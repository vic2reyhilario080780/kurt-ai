import asyncio
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

import httpx
from rich.console import Console

from kurt.core import execution_preferences as prefs
from kurt.core import persona
from kurt.core.cli_orchestrator import handle_slash
from kurt.core.router import ModelRouter
from kurt.capabilities.bridge import NativeToolRouter


def failure(status, code=None):
    response = httpx.Response(status, json={"error": {"code": code}},
                              request=httpx.Request("POST", "https://example.org"))
    return httpx.HTTPStatusError("Synthetic provider failure", request=response.request, response=response)


class Replies:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []
        self.options = []
        self.strict_selection = False

    async def route(self, provider, model, messages, **kwargs):
        self.calls.append((provider, model, self.strict_selection, json.loads(json.dumps(messages))))
        self.options.append(kwargs)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        yield response


class SavedDefaultsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        for name, value in (("KURT_DIR", root), ("PERSONA_PATH", root / "persona.json")):
            context = patch.object(persona, name, value)
            context.start()
            self.addCleanup(context.stop)

    def slash(self, text):
        return handle_slash(text, "test", "auto", None)

    def test_vibe_default_persists_and_uses_headless_ask_adapter(self):
        self.assertEqual(self.slash('/cli default vibe').cli_override, 'vibe')
        self.assertEqual(prefs.ExecutionSession.load().cli, 'vibe')
        messages = [{'role': 'user', 'content': 'Hello'}]
        with patch('kurt.core.cli_orchestrator._resolve_cmd', return_value='/test/vibe'), \
             patch('kurt.core.cli_orchestrator.run_ai_cli', return_value={'status': 'completed', 'stdout': 'Hello', 'stderr': '', 'exit_code': 0}) as run:
            self.assertEqual(prefs.run_default_cli('vibe', messages), 'Hello')
        cmd, args = run.call_args.args
        self.assertEqual(cmd, '/test/vibe')
        self.assertEqual(args[0], '-p')
        self.assertEqual(args[args.index('--agent') + 1], 'ask')
        self.assertEqual(args[args.index('--model') + 1], 'mistral-medium-3.5')
        self.assertNotIn('--auto-approve', args)

    def test_vibe_only_receives_its_provider_key(self):
        from kurt.core.cli_orchestrator import _ai_cli_env
        with patch.dict(os.environ, {'MISTRAL_API_KEY': 'stale-shell', 'OPENAI_API_KEY': 'fixture-openai', 'GROQ_API_KEY': 'fixture-groq'}, clear=True), patch('kurt.utils.env_loader.setup_mistral_key', return_value='fixture-mistral'):
            env = _ai_cli_env('/test/vibe')
        self.assertEqual(env['MISTRAL_API_KEY'], 'fixture-mistral')
        self.assertNotIn('OPENAI_API_KEY', env)
        self.assertNotIn('GROQ_API_KEY', env)

    def test_vibe_uses_public_ca_bundle_without_disabling_tls(self):
        from kurt.core.cli_orchestrator import _ai_cli_env
        from kurt.utils.execution import sandbox_profile
        with patch('ssl.get_default_verify_paths') as paths:
            paths.return_value.cafile = '/public/roots.pem'
            env = _ai_cli_env('/test/vibe')
            profile = sandbox_profile(service='vibe')
        self.assertEqual(env['SSL_CERT_FILE'], '/public/roots.pem')
        self.assertIn('(allow file-read* (literal "/public/roots.pem"))', profile)
        self.assertIn('.aws', profile)

    def test_saved_model_survives_restart_and_cli_model_precedence_is_explicit(self):
        persona.save_persona({"user_name": "Test"})
        prefs.save_default_model("mistral-small-latest", "mistral")
        first = prefs.ExecutionSession.load()
        self.assertEqual(first.analysis().provider, "mistral")
        self.assertEqual(first.analysis().model, "mistral-small-latest")
        prefs.save_default_cli("claude")
        self.assertEqual(prefs.ExecutionSession.load().cli, "claude")
        override = prefs.ExecutionSession.load(model="deepseek-flash")
        self.assertEqual(override.cli, "auto")
        self.assertEqual(override.analysis().provider, "deepseek")
        self.assertEqual(prefs.ExecutionSession.load().cli, "claude")
        prefs.save_default_model("auto")
        self.assertEqual(prefs.ExecutionSession.load().cli, "auto")
        self.assertEqual(persona.load_persona()["user_name"], "Test")

    def test_slash_default_and_session_only_changes_have_different_persistence(self):
        saved = self.slash("/model default mistral-small-latest mistral")
        self.assertEqual(saved.model_override, "mistral-small-latest|mistral")
        self.assertEqual(saved.cli_override, "auto")
        session = self.slash("/model deepseek-flash deepseek")
        self.assertEqual(session.model_override, "deepseek-flash|deepseek")
        self.assertEqual(prefs.ExecutionSession.load().analysis().provider, "mistral")
        self.assertEqual(self.slash("/cli default codex").cli_override, "codex")
        self.assertEqual(self.slash("/cli use gemini").cli_override, "gemini")
        self.assertEqual(prefs.ExecutionSession.load().cli, "codex")
        before = persona.PERSONA_PATH.read_text()
        self.slash("/cli default nonexistent")
        self.slash("/model default a/b badprovider")
        self.assertEqual(persona.PERSONA_PATH.read_text(), before)

    def test_provider_resolution_does_not_guess_gpt_or_claude_as_groq(self):
        for name, provider in (("gpt-4.1", "openai"), ("claude-test", "anthropic"),
                               ("mistral-small-latest", "mistral"), ("deepseek-flash", "deepseek")):
            with self.subTest(name=name):
                self.assertEqual(prefs.parse_model(name)[1], provider)
        self.assertEqual(prefs.parse_model("openai/gpt-4.1", "openai"), ("gpt-4.1", "openai"))
        self.assertEqual(prefs.parse_model("openai/gpt-4.1"), ("openai/gpt-4.1", "openrouter"))

    def test_quota_failover_is_session_only_and_restart_retries_saved_default(self):
        prefs.save_default_model("mistral-small-latest")
        current = prefs.ExecutionSession.load()
        current.exhausted = True
        self.assertFalse(current.pinned)
        self.assertEqual(current.analysis().provider, "groq")
        self.assertTrue(prefs.ExecutionSession.load().pinned)

    def test_pickers_offer_saved_model_and_cli_actions(self):
        from kurt.core import command_palette as cp
        with patch.object(cp, "_openrouter_models", return_value=[{"id": "openai/example", "architecture": {"output_modalities": ["text"]}}]):
            self.assertTrue(any(i.get("value") == "/model default openai/example openrouter" for i in cp._default_model_items("")))
        self.assertTrue(any(i.get("value") == "/cli default codex" for i in cp._cli_default_items("codex")))
        self.assertEqual(next(i for i in cp._config_items("model"))["target"], "default_models")

    def test_cli_default_receives_context_without_api_planner(self):
        from kurt import main
        prefs.save_default_cli("claude")
        output = Console(file=io.StringIO())
        with patch.object(main, "console", output), \
             patch.object(output, "input", side_effect=["hello", "continue", "/exit"]), \
             patch.object(main, "load_env"), \
             patch.object(prefs, "run_default_cli", side_effect=["first answer", "second answer"]) as cli, \
             patch.object(main, "stream_response", AsyncMock()) as api, \
             patch.dict("sys.modules", {"kurt.core.wake_word": None, "kurt.core.screen_watcher": None}):
            main.chat(skill=None, model=None, cli=None, session="test", no_memory=True)
        api.assert_not_called()
        self.assertEqual(cli.call_count, 2)
        self.assertIn({"role": "assistant", "content": "first answer"}, cli.call_args.args[1])

    def test_cli_timeout_never_replays_or_changes_saved_default(self):
        from kurt import main
        prefs.save_default_cli("claude")
        output = io.StringIO()
        console = Console(file=output)
        with patch.object(main, "console", console), \
             patch.object(console, "input", side_effect=["do task", "/exit"]), \
             patch.object(main, "load_env"), \
             patch.object(prefs, "run_default_cli", side_effect=RuntimeError("timed_out")) as cli, \
             patch.object(main, "stream_response", AsyncMock()) as api, \
             patch.dict("sys.modules", {"kurt.core.wake_word": None, "kurt.core.screen_watcher": None}):
            main.chat(skill=None, model=None, cli=None, session="test", no_memory=True)
        api.assert_not_called()
        cli.assert_called_once()
        self.assertIn("not replayed", output.getvalue())
        self.assertEqual(prefs.ExecutionSession.load().cli, "claude")

    def test_cli_quota_enables_auto_for_next_request_without_replaying_task(self):
        from kurt import main
        prefs.save_default_cli("claude")
        console = Console(file=io.StringIO())
        with patch.object(main, "console", console), \
             patch.object(console, "input", side_effect=["first task", "next task", "/exit"]), \
             patch.object(main, "load_env"), \
             patch.object(prefs, "run_default_cli", side_effect=prefs.CLIQuotaExhausted("quota")) as cli, \
             patch.object(main, "stream_response", AsyncMock(return_value="auto answer")) as api, \
             patch.dict("sys.modules", {"kurt.core.wake_word": None, "kurt.core.screen_watcher": None}):
            main.chat(skill=None, model=None, cli=None, session="test", no_memory=True)
        cli.assert_called_once()
        api.assert_awaited_once()
        self.assertEqual(api.call_args.kwargs["prompt"], "next task")
        self.assertEqual(prefs.ExecutionSession.load().cli, "claude")


class RoutingPolicyTests(unittest.TestCase):
    def test_quota_classification_excludes_rate_limits_auth_and_server_errors(self):
        for code in (400, 401, 404, 429, 500, 503):
            self.assertFalse(prefs.quota_exhausted(failure(code)))
        self.assertTrue(prefs.quota_exhausted(failure(402)))
        self.assertTrue(prefs.quota_exhausted(failure(429, "insufficient_quota")))
        self.assertFalse(prefs.quota_exhausted(RuntimeError("insufficient_quota")))
        self.assertFalse(prefs.quota_exhausted(failure(429, {"unexpected": "object"})))

    def test_api_model_does_not_silently_fallback_for_nonquota_errors(self):
        from kurt import main
        for error in (failure(401), failure(429), failure(503), RuntimeError("bad tool schema")):
            replies = Replies(error)
            policy = prefs.ExecutionSession("mistral-small-latest|mistral")
            with self.subTest(error=error), patch.object(main, "ModelRouter", return_value=replies), \
                 patch.object(main, "console", Console(file=io.StringIO())):
                text = asyncio.run(main.stream_response(policy.analysis(), [{"role": "user", "content": "hello"}],
                                   "test", True, False, execution=policy))
            self.assertIsNone(text)
            self.assertEqual(len(replies.calls), 1)
            self.assertFalse(policy.exhausted)

    def test_confirmed_quota_falls_back_once_and_future_turn_stays_auto(self):
        from kurt import main
        replies = Replies(failure(402), "fallback answer", "next answer")
        policy = prefs.ExecutionSession("mistral-small-latest|mistral")
        messages = [{"role": "user", "content": "hello"}]
        with patch.object(main, "ModelRouter", return_value=replies), patch.object(main, "console", Console(file=io.StringIO())):
            text = asyncio.run(main.stream_response(policy.analysis(), messages, "test", True, False, execution=policy))
            self.assertEqual(text, "fallback answer")
            self.assertTrue(policy.exhausted)
            asyncio.run(main.stream_response(policy.analysis(), messages, "test", True, False, execution=policy))
        self.assertEqual([c[0] for c in replies.calls], ["mistral", "groq", "groq"])
        self.assertEqual([c[2] for c in replies.calls], [True, False, False])

    def test_selected_model_cannot_delegate_to_other_models_or_clis(self):
        request = "```tool\n" + json.dumps({"tool": "call_model", "params": {"provider": "groq", "model": "other", "prompt": "hello"}}) + "\n```"
        replies = Replies(request, "answer with selected model")
        replies.strict_selection = True
        with patch("kurt.capabilities.bridge.invoke_native") as invoke:
            async def collect():
                return "".join([c async for c in NativeToolRouter(replies).route("mistral", "chosen", [{"role": "user", "content": "hello"}])])
            self.assertEqual(asyncio.run(collect()), "answer with selected model")
        invoke.assert_not_called()
        self.assertIn("orchestration is disabled", replies.calls[-1][3][-1]["content"])

    def test_pinned_native_schemas_keep_direct_tools_but_hide_model_delegation(self):
        replies = Replies("answer")
        replies.strict_selection = True
        replies.supports_native_tools = True
        async def collect():
            return [c async for c in NativeToolRouter(replies).route("groq", "chosen", [{"role": "user", "content": "hello"}])]
        asyncio.run(collect())
        names = {t["function"]["name"] for t in replies.options[0]["native_tools"]}
        self.assertIn("search_web", names)
        self.assertFalse(names & {"call_model", "delegate_cli", "spawn_subagent", "codex_task", "desktop_cli"})

    def test_quota_fallback_retains_tool_receipts_without_reexecuting_tools(self):
        from kurt import main
        request = "```tool\n" + json.dumps({"tool": "search_web", "params": {"query": "test"}}) + "\n```"
        replies = Replies(request, failure(402), "answer from observed result")
        policy = prefs.ExecutionSession("mistral-small-latest|mistral")
        with patch.object(main, "ModelRouter", return_value=replies), \
             patch.object(main, "console", Console(file=io.StringIO())), \
             patch("kurt.capabilities.bridge.invoke_native", return_value={"status": "completed", "text": "observed result"}) as invoke:
            result = asyncio.run(main.stream_response(policy.analysis(), [{"role": "user", "content": "search"}],
                                 "test", True, False, execution=policy))
        self.assertEqual(result, "answer from observed result")
        invoke.assert_called_once()
        self.assertIn("observed result", replies.calls[-1][3][-1]["content"])

    def test_strict_missing_provider_key_does_not_use_another_key(self):
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "synthetic-router-key"}, clear=True):
            router = ModelRouter()
        router.strict_selection = True
        with patch.object(router, "call_openrouter") as other:
            async def collect():
                return [c async for c in router.route("mistral", "test", [])]
            with self.assertRaisesRegex(RuntimeError, "Missing API key"):
                asyncio.run(collect())
        other.assert_not_called()

    def test_native_provider_routes_use_correct_endpoints(self):
        env = {key: "synthetic-key" for key in ("OPENAI_API_KEY", "MISTRAL_API_KEY", "DEEPSEEK_API_KEY", "GOOGLE_AI_KEY")}
        expected = {"openai": "api.openai.com", "mistral": "api.mistral.ai", "deepseek": "api.deepseek.com", "google": "generativelanguage.googleapis.com"}
        real_client = httpx.AsyncClient
        calls = []
        def handler(request):
            calls.append(request)
            self.assertEqual(json.loads(request.content)["model"], "test-model")
            return httpx.Response(200, text='data: {"choices":[{"delta":{"content":"answer"}}]}\n\ndata: [DONE]\n\n')
        with patch.dict(os.environ, env, clear=True):
            router = ModelRouter()
        router.strict_selection = True
        for provider, host in expected.items():
            with self.subTest(provider=provider), patch("kurt.core.router.httpx.AsyncClient", lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw)):
                async def collect():
                    return "".join([c async for c in router.route(provider, "test-model", [{"role": "user", "content": "hello"}])])
                self.assertEqual(asyncio.run(collect()), "answer")
                self.assertEqual(calls[-1].url.host, host)

    def test_cli_quota_requires_structured_error_and_failed_process(self):
        payload = json.dumps({"error": {"code": "insufficient_quota"}})
        self.assertTrue(prefs.cli_quota_exhausted({"status": "failed", "stderr": payload}))
        for result in ({"status": "failed", "stderr": "credits exhausted"},
                       {"status": "timed_out", "stderr": payload},
                       {"status": "completed", "stdout": payload}):
            self.assertFalse(prefs.cli_quota_exhausted(result))


if __name__ == "__main__":
    unittest.main()
