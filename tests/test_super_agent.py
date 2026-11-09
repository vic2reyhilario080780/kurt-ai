import asyncio
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from kurt.core.agent_loop import TOOLS, execute_tool
from kurt.core.cli_orchestrator import handle_slash
from kurt.core.file_ops import find_files, grep_search, multi_edit
from kurt.core.mac_doctor import format_doctor_report, open_folder, run_doctor_action
from kurt.core.subagents import create_plan_artifact, manage_background_task, run_subagent_async, run_swarm_async
from kurt.utils.workspace import workspace


class SuperAgentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.ws = workspace(self.root)
        self.ws.__enter__()
        self.addCleanup(self.ws.__exit__, None, None, None)

    def test_grep_search_and_find_files_skip_sensitive_files(self):
        src = self.root / "app.py"
        src.write_text("def calculate_total(items):\n    return sum(items)\n", encoding="utf-8")
        secret_env = self.root / ".env"
        secret_env.write_text("calculate_total=secret_token_value\n", encoding="utf-8")

        grep_out = grep_search("calculate_total", path=str(self.root))
        self.assertIn("app.py:1:", grep_out)
        self.assertNotIn(".env", grep_out)

        find_out = find_files("*.py", path=str(self.root))
        self.assertIn("app.py", find_out)
        self.assertNotIn(".env", find_out)

    def test_multi_edit_atomic_apply_and_rollback(self):
        target = self.root / "sample.py"
        original = "a = 1\nb = 2\nc = 3\n"
        target.write_text(original, encoding="utf-8")

        # Failed second edit should not partially mutate file
        fail_res = multi_edit(
            str(target),
            [
                {"old_str": "a = 1", "new_str": "a = 10"},
                {"old_str": "nonexistent_line", "new_str": "x = 99"},
            ],
        )
        self.assertIn("❌", fail_res)
        self.assertEqual(target.read_text(encoding="utf-8"), original)

        # Valid multi-edit applies all changes
        ok_res = multi_edit(
            str(target),
            [
                {"old_str": "a = 1", "new_str": "a = 10"},
                {"old_str": "c = 3", "new_str": "c = 30"},
            ],
        )
        self.assertIn("✅", ok_res)
        self.assertEqual(target.read_text(encoding="utf-8"), "a = 10\nb = 2\nc = 30\n")

    def test_mac_doctor_diagnostics_and_sensitive_guard(self):
        summary = run_doctor_action("summary")
        self.assertIn("os", summary)
        self.assertIn("cpu_count", summary)
        formatted = format_doctor_report(summary)
        self.assertIn("System Diagnostics", formatted)

        cpu_top = run_doctor_action("cpu", limit=3)
        self.assertEqual(cpu_top.get("status"), "ok")
        self.assertLessEqual(len(cpu_top.get("processes", [])), 3)

        disk_report = run_doctor_action("disk", target=str(self.root), limit=5)
        self.assertEqual(disk_report.get("status"), "ok")

        # Sensitive path must be blocked
        env_file = self.root / ".env"
        env_file.write_text("SECRET=1", encoding="utf-8")
        blocked = open_folder(str(env_file))
        self.assertEqual(blocked.get("status"), "error")

    def test_background_task_lifecycle_and_safety(self):
        blocked = manage_background_task("start", cmd="rm -rf /")
        self.assertEqual(blocked["status"], "error")

        started = manage_background_task("start", cmd="python3 -c 'import time; print(\"hello_bg\", flush=True); time.sleep(0.2)'", cwd=str(self.root))
        self.assertEqual(started["status"], "started")
        tid = started["task_id"]

        time.sleep(0.4)
        status = manage_background_task("status", task_id=tid)
        self.assertEqual(status["status"], "ok")
        self.assertIn("hello_bg", status["output"])

        listed = manage_background_task("list")
        self.assertGreaterEqual(listed["count"], 1)

        killed = manage_background_task("kill", task_id=tid)
        self.assertEqual(killed["status"], "killed")

    def test_create_plan_artifact(self):
        plan_path = self.root / "my_plan.md"
        res = create_plan_artifact(
            title="Upgrade Kurt Super Agent",
            summary="Make Kurt as strong as Gemini CLI",
            steps=["Add mac_doctor", "Add grep_search and multi_edit", "Add subagents"],
            mermaid_diagram="flowchart LR\n  A[\"User\"] --> B[\"KURT Super Agent\"]",
            verification=["Run unit tests", "Verify CLI slash commands"],
            output_path=str(plan_path),
        )
        self.assertEqual(res["status"], "ok")
        self.assertTrue(plan_path.exists())
        text = plan_path.read_text(encoding="utf-8")
        self.assertIn("> [!IMPORTANT]", text)
        self.assertIn("```mermaid", text)
        self.assertIn("**Step 1:** Add mac_doctor", text)

    def test_subagent_and_swarm_execution(self):
        class FakeRouter:
            async def route(self, provider, model, messages, **kwargs):
                yield '```tool\n{"tool": "done", "params": {"summary": "Subagent finished research"}}\n```'

        with patch("kurt.core.router.ModelRouter", return_value=FakeRouter()):
            sub_res = asyncio.run(run_subagent_async("research", "Check architecture", cwd=str(self.root)))
            self.assertEqual(sub_res["status"], "completed")
            self.assertIn("Subagent finished research", sub_res["summary"])

            swarm_res = asyncio.run(
                run_swarm_async(
                    [
                        {"role": "research", "task": "Task 1"},
                        {"role": "qa-verifier", "task": "Task 2"},
                    ],
                    cwd=str(self.root),
                )
            )
            self.assertEqual(swarm_res["status"], "ok")
            self.assertEqual(swarm_res["subagents_run"], 2)

    def test_agent_loop_tools_and_slash_commands_wired(self):
        tool_names = {t["name"] for t in TOOLS}
        for expected in (
            "grep_search", "find_files", "multi_edit", "background_task",
            "mac_doctor", "open_folder", "spawn_subagent", "swarm_execute",
            "create_plan", "analyze_screen", "find_and_click", "browser_action",
        ):
            self.assertIn(expected, tool_names)

        # Test execute_tool for mac_doctor
        doc_out = execute_tool("mac_doctor", {"action": "summary"})
        self.assertIn("System Diagnostics", doc_out)

        # Test slash commands
        slash_doc = handle_slash("/doctor summary", "sess1", "auto", None)
        self.assertTrue(slash_doc.handled)
        self.assertTrue(slash_doc.feed_to_ai)
        self.assertIn("System Diagnostics", slash_doc.output)

        slash_plan = handle_slash("/plan Test Plan | Step A; Step B", "sess1", "auto", None)
        self.assertTrue(slash_plan.handled)
        self.assertIn("Plan Artifact Created", slash_plan.output)

    def test_cross_platform_os_auto_adaptation(self):
        from kurt.core import mac_doctor

        # 1. Verify get_os_profile adapts across Darwin, Windows, and Linux
        with patch.object(mac_doctor.platform, "system", return_value="Windows"):
            win_prof = mac_doctor.get_os_profile()
            self.assertEqual(win_prof["os_label"], "Windows")
            self.assertEqual(win_prof["file_manager"], "File Explorer")
            self.assertEqual(win_prof["primary_modifier"], "ctrl")

        with patch.object(mac_doctor.platform, "system", return_value="Linux"):
            lin_prof = mac_doctor.get_os_profile()
            self.assertEqual(lin_prof["os_label"], "Linux")
            self.assertEqual(lin_prof["file_manager"], "xdg-open")
            self.assertEqual(lin_prof["primary_modifier"], "ctrl")

        # 2. Verify Windows & Linux diagnostics with os_override
        with patch.object(mac_doctor, "_run_powershell", return_value=(0, '[{"Id": 42, "ProcessName": "chrome", "CPU_s": 12.5, "Mem_MB": 256.0}]', "")):
            win_procs = run_doctor_action("cpu", limit=5, os_override="Windows")
            self.assertEqual(win_procs["status"], "ok")
            self.assertEqual(win_procs["processes"][0]["command"], "chrome")

        (self.root / "sub").mkdir()
        (self.root / "sub" / "file.txt").write_text("hello world", encoding="utf-8")
        with patch.object(mac_doctor, "_run_powershell", return_value=(0, "Healthy", "")):
            win_disk = run_doctor_action("disk", target=str(self.root), os_override="Windows")
            self.assertEqual(win_disk["status"], "ok")
            self.assertEqual(win_disk["smart_status"], "Healthy")

        # 3. Verify system_doctor and /system aliases
        sys_out = execute_tool("system_doctor", {"action": "profile"})
        self.assertIn("os_label", sys_out)

        slash_sys = handle_slash("/system summary", "sess1", "auto", None)
        self.assertTrue(slash_sys.handled)
        self.assertIn("Host System Diagnostics", slash_sys.output)


if __name__ == "__main__":
    unittest.main()
