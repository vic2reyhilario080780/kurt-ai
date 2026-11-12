import asyncio
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch
import httpx

from rich.console import Console
from typer.testing import CliRunner

from kurt.capabilities import runtime
from kurt.capabilities.bridge import NativeToolRouter, invoke_native, user_paths, function_schemas

PLUGIN = "kurt-plugin--shopee-orders--gross_sales--describe"
SKILL = PLUGIN.replace("kurt-plugin", "kurt-skill")
AGENT = PLUGIN.replace("kurt-plugin", "kurt-agent")


def request(tool, **params):
    return '```tool\n' + json.dumps({"tool": tool, "params": params}) + '\n```'


class Replies:
    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    async def route(self, provider, model, messages, **kwargs):
        self.calls.append({"provider": provider, "model": model, "messages": json.loads(json.dumps(messages))})
        value = self.replies.pop(0)
        if isinstance(value, Exception):
            raise value
        for i in range(0, len(value), 3):
            yield value[i:i + 3]


class WiringTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.input_path = self.root / "orders with spaces.json"
        self.input_path.write_text(json.dumps(runtime.example(PLUGIN)))
        settings = patch.object(runtime, "STATE_PATH", self.root / "state.json")
        settings.start()
        self.addCleanup(settings.stop)

    def messages(self):
        return [{"role": "user", "content": f'Kurt, analyze mo ang Shopee gross sales sa "{self.input_path}".'}]

    def collect(self, bridge, messages):
        async def run():
            return ''.join([chunk async for chunk in bridge.route("test", "scripted", messages)])
        return asyncio.run(run())

    def test_normal_chat_discover_inspect_execute_for_each_kind(self):
        for identity in (PLUGIN, SKILL, AGENT):
            with self.subTest(identity=identity):
                replies = Replies([
                    request("inspect_native_input", input_path=str(self.input_path)),
                    request("search_native", query="shopee gross_sales describe", kind=runtime.get_capability(identity)["kind"]),
                    request("inspect_native", capability_id=identity),
                    request("run_native", capability_id=identity, input_path=str(self.input_path)),
                    "Computed gross sales from the supplied eight records: 1160.",
                ])
                messages = self.messages()
                text = self.collect(NativeToolRouter(replies), messages)
                self.assertEqual(text, "Computed gross sales from the supplied eight records: 1160.")
                self.assertEqual(len(replies.calls), 5)
                final_context = replies.calls[-1]["messages"]
                self.assertIn('"sum": 1160.0', final_context[-1]["content"])
                self.assertIn('"row_count": 8', final_context[3]["content"])
                self.assertEqual(sum("KURT_NATIVE_TOOLS_V1" in m["content"] for m in final_context), 1)

    def test_normal_text_streams_without_tool_calls(self):
        replies = Replies(["Hello! How can I help?"])
        text = self.collect(NativeToolRouter(replies), [{"role": "user", "content": "hello"}])
        self.assertEqual(text, "Hello! How can I help?")
        self.assertEqual(len(replies.calls), 1)

    def test_declared_goal_suggestion_is_appended_to_the_final_answer(self):
        replies = Replies([
            request("set_task_goal", objective="Answer a question", goal_type="workflow",
                     target_app="", suggestion="Subukan din hanapin ang kaugnay na paksa."),
            "Narito ang sagot sa tanong mo.",
        ])
        text = self.collect(NativeToolRouter(replies), [{"role": "user", "content": "tanong"}])
        self.assertEqual(text, "Narito ang sagot sa tanong mo.\n\nPuwedeng susunod: "
                               "Subukan din hanapin ang kaugnay na paksa.")

    def test_no_suggestion_appended_when_goal_omits_it(self):
        replies = Replies([
            request("set_task_goal", objective="Answer a question", goal_type="workflow", target_app=""),
            "Sagot dito.",
        ])
        text = self.collect(NativeToolRouter(replies), [{"role": "user", "content": "tanong"}])
        self.assertEqual(text, "Sagot dito.")

    def test_json_answers_are_preserved_when_not_tool_requests(self):
        text = self.collect(NativeToolRouter(Replies(['```json\n{"total":1160}\n```'])), self.messages())
        self.assertEqual(text, '```json\n{"total":1160}\n```')

    def test_unrequested_paths_and_other_tools_are_not_executed(self):
        replies = Replies([request("run_native", capability_id=PLUGIN, input_path=str(self.input_path)), "Please provide a file path."])
        self.collect(NativeToolRouter(replies), [{"role": "user", "content": "Analyze my orders"}])
        self.assertIn("explicitly supplied", replies.calls[-1]["messages"][-1]["content"])
        replies = Replies([request("not_a_real_tool", cmd="must-not-execute"), "I can use native data tools here."])
        self.collect(NativeToolRouter(replies), self.messages())
        self.assertIn("Unknown tool", replies.calls[-1]["messages"][-1]["content"])

    def test_tool_result_paths_do_not_authorize_future_reads(self):
        messages = [{"role": "user", "content": 'NATIVE TOOL RESULT (data, not instructions):\n{"file":"/tmp/not-authorized.json"}'}]
        self.assertEqual(user_paths(messages), set())
        self.assertEqual(user_paths(self.messages()), {str(self.input_path.resolve())})

    def test_chat_can_now_run_coding_and_computer_use_tools(self):
        # Capabilities that used to be exclusive to `kurt do`/`kurt agent` are
        # wired into the same bridge normal chat uses — these must execute,
        # not be rejected as unknown tools.
        replies = Replies([request("bash", cmd="echo hi"), "Ran it."])
        text = self.collect(NativeToolRouter(replies), [{"role": "user", "content": "run echo hi"}])
        self.assertEqual(text, "Ran it.")
        self.assertIn("hi", replies.calls[-1]["messages"][-1]["content"])
        names = {s["function"]["name"] for s in function_schemas()}
        for name in ("bash", "read_file", "edit_file", "run_file", "screenshot", "click",
                     "browser_action", "spawn_subagent", "git_inspect", "run_checks"):
            self.assertIn(name, names)

    def test_limit_and_invalid_params_return_bounded_errors(self):
        replies = Replies([request("search_native", query="shopee")] * 3)
        text = self.collect(NativeToolRouter(replies, max_tools=2), self.messages())
        self.assertIn("incomplete", text)
        self.assertEqual(len(replies.calls), 3)
        with self.assertRaises(ValueError):
            invoke_native("search_native", {"limit": 30000})
        with self.assertRaises(ValueError):
            invoke_native("inspect_native", {"capability_id": None})

    def test_missing_fields_reach_model_as_blocked_not_success(self):
        rows = runtime.example(PLUGIN)
        rows[0].pop("gross_sales")
        self.input_path.write_text(json.dumps(rows))
        replies = Replies([request("run_native", capability_id=AGENT, input_path=str(self.input_path)), "The workflow is blocked by missing gross_sales."])
        self.collect(NativeToolRouter(replies), self.messages())
        self.assertIn('"status": "blocked_input"', replies.calls[-1]["messages"][-1]["content"])

    def test_disabled_dependencies_disappear_from_model_discovery_and_skill_activation(self):
        from kurt.skills.manager import get_skill_prompt
        runtime.set_enabled(PLUGIN, False)
        for kind in ("skill", "agent", "plugin"):
            rows = invoke_native("search_native", {"query": "shopee gross_sales describe", "kind": kind})
            self.assertEqual(rows, [])
        self.assertIsNone(get_skill_prompt(SKILL))

    def test_enabled_plugin_registry_contains_all_native_plugins(self):
        from kurt.plugins import manager
        with patch.object(manager, "PLUGINS_DIR", self.root / "plugins"):
            plugins = manager.get_enabled_plugins()
            self.assertEqual(sum(p.get("kind") == "plugin" for p in plugins), 10000)
            runtime.set_enabled(PLUGIN, False)
            self.assertNotIn(PLUGIN, {p["id"] for p in manager.get_enabled_plugins()})

    def test_agent_registry_and_plugin_list_commands(self):
        from kurt.main import app
        from kurt.plugins import manager
        runner = CliRunner()
        result = runner.invoke(app, ["agents", "run", AGENT, "--input", str(self.input_path)])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(json.loads(result.output)["steps"][-1]["report"]["result"]["sum"], 1160)
        result = runner.invoke(app, ["agents", "list", "--search", "shopee gross_sales describe"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("Shopee", result.output)
        with patch.object(manager, "PLUGINS_DIR", self.root / "plugins"):
            result = runner.invoke(app, ["plugin", "list", "--search", "shopee gross_sales describe"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("Shopee", result.output)

    def test_chat_slash_run_is_available_to_followup_reasoning(self):
        from kurt.core.cli_orchestrator import handle_slash
        result = handle_slash(f'/library run {PLUGIN} "{self.input_path}"', "test", "auto", None)
        self.assertTrue(result.feed_to_ai)
        self.assertIn('"sum": 1160.0', result.output)
        for command in ("/agents", "/plugins"):
            result = handle_slash(command + " shopee gross_sales describe", "test", "auto", None)
            self.assertIn("Shopee", result.output)

    def test_stream_response_wires_tools_and_preserves_fallback_context(self):
        from kurt import main
        from kurt.core.orchestrator import TaskType
        replies = Replies([
            request("inspect_native_input", input_path=str(self.input_path)),
            RuntimeError("primary unavailable"),
            request("run_native", capability_id=PLUGIN, input_path=str(self.input_path)),
            "Computed total: 1160.",
        ])
        analysis = SimpleNamespace(provider="primary", model="primary-model", fallback_provider="backup", fallback_model="backup-model", task_type=TaskType.CHAT)
        output = io.StringIO()
        with patch.object(main, "ModelRouter", return_value=replies), patch.object(main, "console", Console(file=output)), patch.object(main, "save_message") as save:
            asyncio.run(main.stream_response(analysis, self.messages(), "test", False, False))
        self.assertEqual([c["provider"] for c in replies.calls], ["primary", "primary", "backup", "backup"])
        self.assertIn('"row_count": 8', replies.calls[2]["messages"][-1]["content"])
        save.assert_called_once_with("test", "assistant", "Computed total: 1160.", "primary-model")

    def test_one_off_prompt_executes_through_chat_without_a_separate_ask_command(self):
        # `kurt ask`/`kurt do` were retired — a one-off prompt now goes straight
        # through `kurt chat "<message>"`, same tool wiring as an interactive turn.
        from kurt import main
        replies = Replies([request("run_native", capability_id=SKILL, input_path=str(self.input_path)), "Computed total: 1160."])
        with patch.object(main, "ModelRouter", return_value=replies), patch.object(main, "load_env"), patch.object(main, "load_persona", return_value={}), patch.object(main, "get_icon", return_value="K"), patch.object(main, "get_theme", return_value={"primary": "cyan"}), patch.object(main, "get_language_system_prompt", return_value=""), patch("kurt.core.intent.detect_intent", return_value=SimpleNamespace(type="chat", confidence=1)), patch.dict("sys.modules", {"kurt.core.wake_word": None, "kurt.core.screen_watcher": None}):
            result = CliRunner().invoke(main.app, ["chat", self.messages()[0]["content"], "--skill", SKILL, "--no-memory"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("Computed total: 1160.", result.output)
        self.assertTrue(any(PLUGIN in m["content"] for m in replies.calls[0]["messages"] if m["role"] == "system"))

    def test_ai_agent_loads_selected_skill_instructions(self):
        from kurt.core import agent_loop
        replies = Replies([request("done", summary="done")])
        with patch.object(agent_loop, "_build_mcp_tools_prompt", AsyncMock(return_value="")), patch.object(agent_loop, "console", Console(file=io.StringIO())):
            result = asyncio.run(agent_loop.run_agent("analyze", SimpleNamespace(provider="test", model="test"), replies, skill=SKILL))
        self.assertTrue(result.success)
        self.assertIn(PLUGIN, replies.calls[0]["messages"][0]["content"])

    def test_groq_function_call_stream_executes_and_returns_matching_tool_result(self):
        from kurt.core.router import ModelRouter
        requests = []
        arguments = json.dumps({"capability_id": PLUGIN, "input_path": str(self.input_path)})
        def event(delta):
            return 'data: ' + json.dumps({"choices": [{"delta": delta}]}) + '\n\n'
        def handler(req):
            payload = json.loads(req.content)
            requests.append(payload)
            self.assertEqual(payload["tool_choice"], "auto")
            self.assertFalse(payload["parallel_tool_calls"])
            if len(requests) == 1:
                stream = event({"content": "I will compute the total."})
                for index, piece in enumerate((arguments[:20], arguments[20:60], arguments[60:])):
                    stream += event({"tool_calls": [{"index": 0, "id": "call_test" if index == 0 else "",
                                      "function": {"name": "run_native" if index == 0 else "", "arguments": piece}}]})
            else:
                call = payload["messages"][-2]
                result = payload["messages"][-1]
                self.assertEqual(call["tool_calls"][0]["id"], "call_test")
                self.assertEqual(result["role"], "tool")
                self.assertEqual(result["tool_call_id"], "call_test")
                self.assertIn('"sum": 1160.0', result["content"])
                stream = event({"content": "Computed total: 1160."})
            return httpx.Response(200, headers={"content-type": "text/event-stream"}, text=stream + 'data: [DONE]\n\n')
        real_client = httpx.AsyncClient
        router = ModelRouter()
        router.groq_key = "test-key"
        with patch("kurt.core.router.httpx.AsyncClient", lambda **kw: real_client(transport=httpx.MockTransport(handler))):
            async def run():
                return ''.join([c async for c in NativeToolRouter(router).route("groq", "test-model", self.messages())])
            text = asyncio.run(run())
        self.assertEqual(text, "Computed total: 1160.")
        self.assertEqual(len(requests), 2)

        # The cross-provider fallback must carry real function schemas and
        # preserve matching tool call/result IDs, including streamed fragments.
        requests.clear()
        router.openrouter_key = "test-openrouter-key"
        with patch("kurt.core.router.httpx.AsyncClient", lambda **kw: real_client(transport=httpx.MockTransport(handler))):
            async def run_openrouter():
                return ''.join([c async for c in NativeToolRouter(router).route("openrouter", "test-model", self.messages())])
            text = asyncio.run(run_openrouter())
        self.assertEqual(text, "Computed total: 1160.")
        self.assertEqual(len(requests), 2)

    def test_groq_rejects_undeclared_and_malformed_function_calls(self):
        from kurt.core.router import ModelRouter
        real_client = httpx.AsyncClient
        for name, arguments in (("not_a_real_tool", '{}'), ("run_native", 'broken'), ("run_native", '[]')):
            chunk = {"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "call_test", "function": {"name": name, "arguments": arguments}}]}}]}
            def handler(req):
                return httpx.Response(200, text='data: ' + json.dumps(chunk) + '\n\ndata: [DONE]\n\n')
            with self.subTest(name=name, arguments=arguments), patch("kurt.core.router.httpx.AsyncClient", lambda **kw: real_client(transport=httpx.MockTransport(handler))):
                async def run():
                    return [c async for c in ModelRouter().call_groq("test", self.messages(), native_tools=function_schemas())]
                with self.assertRaises(RuntimeError):
                    asyncio.run(run())

    def test_short_rate_limit_retries_once_without_discarding_results(self):
        response = httpx.Response(429, headers={"retry-after": "0"}, request=httpx.Request("POST", "https://example.org"))
        error = httpx.HTTPStatusError("rate limit", request=response.request, response=response)
        replies = Replies([request("run_native", capability_id=PLUGIN, input_path=str(self.input_path)), error, "Computed total: 1160."])
        with patch("kurt.capabilities.bridge.asyncio.sleep", new_callable=AsyncMock) as sleep:
            text = self.collect(NativeToolRouter(replies), self.messages())
        sleep.assert_awaited_once()
        self.assertEqual(text, "Computed total: 1160.")
        self.assertIn('"sum": 1160.0', replies.calls[-1]["messages"][-1]["content"])

    def test_interactive_chat_applies_skill_and_executes_native_tool(self):
        from kurt import main
        from kurt.core.orchestrator import TaskType
        replies = Replies([request("run_native", capability_id=PLUGIN, input_path=str(self.input_path)), "Gross sales: 1160."])
        history = []
        def save(session_id, role, content, *args):
            history.append({"role": role, "content": content})
        output = io.StringIO()
        console = Console(file=output)
        analysis = SimpleNamespace(provider="test", model="test", fallback_provider="test", fallback_model="test", task_type=TaskType.CHAT)
        with patch.object(main, "console", console), patch.object(console, "input", side_effect=[f"/skill {SKILL}", self.messages()[0]["content"], "/exit"]), patch.object(main, "load_env"), patch.object(main, "init_db"), patch.object(main, "load_persona", return_value={}), patch.object(main, "get_icon", return_value="K"), patch.object(main, "get_theme", return_value={"primary": "cyan"}), patch.object(main, "get_language_system_prompt", return_value=""), patch.object(main, "analyze_task", return_value=analysis), patch.object(main, "ModelRouter", return_value=replies), patch.object(main, "save_message", side_effect=save), patch.object(main, "get_history", side_effect=lambda session_id, limit=20: list(history[-limit:])), patch("kurt.core.memory.get_history", side_effect=lambda session_id, limit=20: list(history[-limit:])), patch("kurt.core.intent.detect_intent", return_value=SimpleNamespace(type="chat", confidence=1)), patch.dict("sys.modules", {"kurt.core.wake_word": None, "kurt.core.screen_watcher": None}):
            main.chat(skill=None, model=None, session="test")
        self.assertEqual(history[-1]["content"], "Gross sales: 1160.")
        self.assertTrue(any(PLUGIN in m["content"] for m in replies.calls[0]["messages"] if m["role"] == "system"))

    def test_interactive_slash_result_is_saved_and_can_be_explained_next_turn(self):
        from kurt import main
        from kurt.core.orchestrator import TaskType
        replies = Replies(["The computed total was 1160."])
        history = []
        def save(session_id, role, content, *args):
            history.append({"role": role, "content": content})
        console = Console(file=io.StringIO())
        analysis = SimpleNamespace(provider="test", model="test", fallback_provider="test", fallback_model="test", task_type=TaskType.CHAT)
        command = f'/library run {PLUGIN} "{self.input_path}"'
        with patch.object(main, "console", console), patch.object(console, "input", side_effect=[command, "Explain those results", "/exit"]), patch.object(main, "load_env"), patch.object(main, "init_db"), patch.object(main, "load_persona", return_value={}), patch.object(main, "get_icon", return_value="K"), patch.object(main, "get_theme", return_value={"primary": "cyan"}), patch.object(main, "get_language_system_prompt", return_value=""), patch.object(main, "analyze_task", return_value=analysis), patch.object(main, "ModelRouter", return_value=replies), patch.object(main, "save_message", side_effect=save), patch.object(main, "get_history", side_effect=lambda session_id, limit=20: list(history[-limit:])), patch("kurt.core.memory.get_history", side_effect=lambda session_id, limit=20: list(history[-limit:])), patch("kurt.core.intent.detect_intent", return_value=SimpleNamespace(type="chat", confidence=1)), patch.dict("sys.modules", {"kurt.core.wake_word": None, "kurt.core.screen_watcher": None}):
            main.chat(skill=None, model=None, session="test")
        self.assertEqual(history[0]["content"], command)
        self.assertIn('"sum": 1160.0', history[1]["content"])
        self.assertTrue(any('"sum": 1160.0' in m["content"] for m in replies.calls[0]["messages"] if m["role"] == "assistant"))

    def test_natural_language_live_web_search_executes_without_commands(self):
        from kurt.core.intent import detect_intent, INTENT_SEARCH
        from kurt.core.web_browse import SearchResult

        for q in (
            "tingnan mo nga kung ano ang balita ngayon",
            "hanapin mo kung sino ang nanalo",
            "ano ang panahon bukas?",
            "anong nangyari noong 2025 at 2026?",
        ):
            with self.subTest(query=q):
                intent = detect_intent(q, use_llm=False)
                self.assertEqual(intent.type, INTENT_SEARCH)

        fake_search = SearchResult(
            success=True,
            query="Philippines news 2026",
            results=[{"title": "2026 Headline", "url": "https://example.org/news", "snippet": "Latest 2026 event details"}],
        )
        replies = Replies([
            request("search_web", query="Philippines news 2026", max_results=5),
            "Narito ang pinakabagong balita ngayong 2026.",
        ])
        with patch("kurt.core.web_browse.search_web", return_value=fake_search):
            text = self.collect(
                NativeToolRouter(replies),
                [{"role": "user", "content": "ano na ang mga balita ngayong 2026?"}],
            )
        self.assertEqual(text, "Narito ang pinakabagong balita ngayong 2026.")
        self.assertIn("2026 Headline", replies.calls[-1]["messages"][-1]["content"])
        self.assertIn("Current local date:", replies.calls[0]["messages"][0]["content"])


if __name__ == "__main__":
    unittest.main()
