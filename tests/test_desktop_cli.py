import asyncio
from dataclasses import asdict
import io
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from rich.console import Console
from typer.testing import CliRunner

from kurt.core import cli_tools
from kurt.capabilities.bridge import NativeToolRouter, function_schemas


class DesktopCLITests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.binary = self.root / "test cli"
        self.binary.write_text(f'#!{sys.executable}\nimport json,sys\nprint(json.dumps({{"received":sys.argv[1:]}}))\n')
        self.binary.chmod(0o700)
        resolver = patch.object(cli_tools, "resolve_cli", return_value=str(self.binary))
        resolver.start()
        self.addCleanup(resolver.stop)
        managed = patch.object(cli_tools, "MANAGED_CONFIG", self.root / "unconfigured.json")
        managed.start()
        self.addCleanup(managed.stop)

    def test_openclaw_task_and_session_are_exact_arguments(self):
        task = 'Summarize "orders"; $(touch NEVER) `echo hi`\nnext line'
        result = cli_tools.delegate_desktop_cli("openclaw", task, agent="work", session_id="session-42")
        self.assertEqual(result.status, "completed")
        self.assertEqual(result.data["received"], ["agent", "--agent", "work", "--message", task, "--json", "--session-id", "session-42"])
        self.assertNotIn("--deliver", result.data["received"])

    def test_peekaboo_direct_commands_need_no_model(self):
        result = cli_tools.delegate_desktop_cli("peekaboo", 'type "hello world; $(echo nope)" --app Safari --window-id 123')
        self.assertEqual(result.data["received"], ["type", "hello world; $(echo nope)", "--app", "Safari", "--window-id", "123"])

    def test_managed_openclaw_uses_lean_headless_mode(self):
        with patch.object(cli_tools, "managed_openclaw", return_value=True):
            result = cli_tools.delegate_desktop_cli("openclaw", "reply only")
            args = result.data["received"]
            self.assertEqual(args[:2], ["agent", "exec"])
            self.assertIn("--local-model-lean", args)
            self.assertEqual(args[-2:], ["--", "reply only"])
            result = cli_tools.delegate_desktop_cli("openclaw", "continue", session_id="saved-session")
            self.assertIn("--local", result.data["received"])
            self.assertIn("saved-session", result.data["received"])

    def test_managed_setup_stores_only_environment_reference_and_refuses_overwrite(self):
        folder = self.root / "managed"
        config = folder / "openclaw.json"
        with patch.object(cli_tools, "MANAGED_DIR", folder), patch.object(cli_tools, "MANAGED_CONFIG", config), patch.object(cli_tools, "cli_env", return_value={"GROQ_API_KEY": "test-secret"}):
            result = cli_tools.setup_openclaw()
            self.assertEqual(result["mode"], "embedded")
            self.assertNotIn("test-secret", config.read_text())
            self.assertIn("${GROQ_API_KEY}", config.read_text())
            self.assertEqual(config.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                cli_tools.setup_openclaw()

    def test_explicit_openclaw_state_is_not_replaced_by_managed_profile(self):
        cli_tools.MANAGED_CONFIG.write_text("{}")
        with patch.dict(os.environ, {"OPENCLAW_STATE_DIR": str(self.root / "user-state")}, clear=False):
            env = cli_tools.cli_env()
        self.assertEqual(env["OPENCLAW_STATE_DIR"], str(self.root / "user-state"))
        self.assertNotEqual(env.get("OPENCLAW_CONFIG_PATH"), str(cli_tools.MANAGED_CONFIG))

    def test_exact_args_and_literal_shell_metacharacters(self):
        marker = self.root / "must-not-exist"
        args = ["see", "--app", f"Safari; touch {marker}", "--json"]
        result = cli_tools.delegate_desktop_cli("peekaboo", args=args)
        self.assertEqual(result.data["received"], args)
        self.assertFalse(marker.exists())

    def test_nonzero_exit_without_stderr_is_failed(self):
        self.binary.write_text(f'#!{sys.executable}\nimport sys\nprint("failed")\nsys.exit(7)\n')
        result = cli_tools.run_cli("peekaboo", ["see"])
        self.assertEqual((result.status, result.exit_code), ("failed", 7))
        self.assertEqual(result.stdout, "failed")

    def test_json_failure_is_not_reported_as_success(self):
        self.binary.write_text(f'#!{sys.executable}\nprint(\'{{"success":false,"error":"access denied"}}\')\n')
        result = cli_tools.run_cli("peekaboo", ["see"])
        self.assertEqual(result.status, "failed")
        self.assertIn("permissions", result.hint)

    def test_timeout_returns_unknown_action_outcome(self):
        self.binary.write_text(f'#!{sys.executable}\nimport time\ntime.sleep(20)\n')
        result = cli_tools.run_cli("peekaboo", ["see"], timeout=1)
        self.assertEqual(result.status, "timed_out")
        self.assertIn("Observe current state", result.hint)

    def test_output_is_bounded_and_truncation_is_explicit(self):
        self.binary.write_text(f'#!{sys.executable}\nprint("x"*100000)\n')
        result = cli_tools.run_cli("peekaboo", ["see"])
        self.assertTrue(result.truncated)
        self.assertLessEqual(len(result.stdout), cli_tools.MAX_OUTPUT)
        self.assertIsNone(result.data)

    def test_missing_cli_has_no_download_or_shell_fallback(self):
        with patch.object(cli_tools, "resolve_cli", return_value=None), patch.object(cli_tools.subprocess, "Popen") as start:
            result = cli_tools.delegate_desktop_cli("openclaw", "hello")
        self.assertEqual(result.status, "missing")
        start.assert_not_called()

    def test_invalid_parameters_are_rejected(self):
        for args in ("see --json", [1], ["a\0b"]):
            with self.subTest(args=args), self.assertRaises(ValueError):
                cli_tools.run_cli("peekaboo", args)
        for timeout in (0, 601, True):
            with self.assertRaises(ValueError):
                cli_tools.run_cli("peekaboo", [], timeout)
        with self.assertRaises(ValueError):
            cli_tools.delegate_desktop_cli("openclaw", "hello", args=["health"])

    def test_chat_slash_and_agent_delegation_use_same_runner(self):
        from kurt.core.cli_orchestrator import handle_slash
        from kurt.core.agent_loop import execute_tool
        for tool, task in (("openclaw", "summarize the local task"), ("peekaboo", "permissions status --json")):
            slash = handle_slash(f"/{tool} {task}", "test", "auto", None)
            self.assertTrue(slash.feed_to_ai)
            self.assertEqual(json.loads(slash.output)["status"], "completed")
            result = json.loads(execute_tool("delegate_cli", {"tool": tool, "prompt": task}))
            self.assertEqual(result["status"], "completed")

    def test_cli_command_reports_failure_via_exit_status(self):
        from kurt.main import app
        result = CliRunner().invoke(app, ["cli", "run", "peekaboo", "permissions status --json"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(json.loads(result.output)["status"], "completed")
        with patch.object(cli_tools, "resolve_cli", return_value=None):
            result = CliRunner().invoke(app, ["cli", "run", "openclaw", "hello"])
        self.assertEqual(result.exit_code, 1)
        self.assertEqual(json.loads(result.output)["status"], "missing")

    def test_regular_chat_can_delegate_and_continue_with_result(self):
        class Router:
            calls = 0
            async def route(self, provider, model, messages, **kw):
                if self.calls == 0:
                    value = {"tool": "desktop_cli", "params": {"tool": "peekaboo", "args": ["permissions", "status", "--json"]}}
                    response = '```tool\n' + json.dumps(value) + '\n```'
                else:
                    if '"received": ["permissions", "status", "--json"]' not in messages[-1]["content"]:
                        raise AssertionError("CLI result missing from model context")
                    response = "The desktop CLI returned its permissions result."
                self.calls += 1
                yield response
        async def run():
            return ''.join([s async for s in NativeToolRouter(Router()).route("test", "test", [{"role": "user", "content": "Check Peekaboo permissions"}])])
        self.assertIn("permissions result", asyncio.run(run()))

    def test_tools_are_visible_in_ai_function_schemas_and_help(self):
        from kurt.core.cli_orchestrator import handle_slash
        from kurt.core.agent_loop import TOOLS_PROMPT
        names = {s["function"]["name"] for s in function_schemas()}
        self.assertIn("desktop_cli", names)
        self.assertIn("desktop_cli_status", names)
        self.assertIn("openclaw", TOOLS_PROMPT)
        self.assertIn("peekaboo", TOOLS_PROMPT)
        help_text = handle_slash("/help", "test", "auto", None).output
        self.assertIn("/openclaw", help_text)
        self.assertIn("/peekaboo", help_text)


class CLIResolutionTests(unittest.TestCase):
    def test_local_bin_precedes_global_and_node_is_first_on_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            binary = root / "peekaboo"
            binary.write_text("test")
            binary.chmod(0o700)
            with patch.object(cli_tools, "NODE_BIN", root), patch.object(cli_tools.shutil, "which", return_value="/global/peekaboo"):
                self.assertEqual(cli_tools.resolve_cli("peekaboo"), str(binary))
                self.assertEqual(cli_tools.cli_env()["PATH"].split(":")[0], str(root))
            with patch.object(cli_tools, "NODE_BIN", root / "absent"), patch.object(cli_tools.shutil, "which", return_value="/global/peekaboo"):
                self.assertEqual(cli_tools.resolve_cli("peekaboo"), "/global/peekaboo")


if __name__ == "__main__":
    unittest.main()
