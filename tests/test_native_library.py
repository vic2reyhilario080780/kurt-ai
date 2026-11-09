import copy
import csv
import io
import asyncio
from types import SimpleNamespace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, AsyncMock

from typer.testing import CliRunner

from kurt.capabilities import engine, runtime
from kurt.capabilities.authoring import capability_id, definition
from kurt.capabilities.commands import run_and_write
from kurt.capabilities.profiles import profiles

PROFILE = profiles()[0]
METRIC = PROFILE["metrics"][0]


def identity(kind="plugin", method="describe"):
    return capability_id(kind, PROFILE["id"], METRIC, method)


class NativeEngineTests(unittest.TestCase):
    def rows(self, values):
        rows = engine.sample_rows(PROFILE)[:len(values)]
        for row, value in zip(rows, values):
            row[METRIC] = value
        return rows

    def test_known_statistics_and_source_unchanged(self):
        rows = self.rows([1, 2, 3, 4])
        before = copy.deepcopy(rows)
        result = engine.analyze(rows, PROFILE, METRIC, "describe")["result"]
        self.assertEqual((result["sum"], result["mean"], result["median"]), (10, 2.5, 2.5))
        self.assertAlmostEqual(result["sample_stdev"], 1.2909944487358056)
        self.assertEqual(rows, before)

    def test_constant_single_zero_and_negative_measurements(self):
        for values in ([0], [5, 5, 5, 5], [-5, -2, 0, 7]):
            for method in engine.METHODS:
                with self.subTest(values=values, method=method):
                    result = engine.analyze(self.rows(values), PROFILE, METRIC, method)
                    json.dumps(result, allow_nan=False)
        norm = engine.analyze(self.rows([5, 5]), PROFILE, METRIC, "normalize")["result"]
        self.assertTrue(all(r["min_max"] == 0 and r["z_score"] == 0 for r in norm))
        contrib = engine.analyze(self.rows([-1, 1]), PROFILE, METRIC, "contribution")["result"]
        self.assertTrue(all(r["share_percent"] is None for r in contrib["records"]))

    def test_invalid_measurements_audited_and_rejected(self):
        for bad in (None, "", "NaN", float("inf"), True, "₱100", "1,000", [], {}, 1e101, 1e-101):
            rows = self.rows([bad])
            with self.subTest(bad=bad):
                audit = engine.analyze(rows, PROFILE, METRIC, "quality")["result"]
                self.assertGreater(audit["issue_count"], 0)
                with self.assertRaises(ValueError):
                    engine.analyze(rows, PROFILE, METRIC, "describe")

    def test_timezones_sorting_and_calendar_gaps(self):
        rows = self.rows([10, 20, 30])
        dates = ["2026-01-03T00:30:00+08:00", "2026-01-01", "2026-01-05"]
        for row, date in zip(rows, dates):
            row[PROFILE["date"]] = date
        trend = engine.analyze(rows, PROFILE, METRIC, "trend")["result"]
        self.assertEqual([r["date"] for r in trend], ["2026-01-01", "2026-01-02", "2026-01-05"])
        self.assertEqual(trend[-1]["days_since_previous"], 3)
        self.assertEqual(trend[-1]["change"], 20)

    def test_rank_ties_and_duplicate_entity_notes(self):
        rows = self.rows([2, 2, 1])
        rows[1][PROFILE["entity"]] = rows[0][PROFILE["entity"]]
        result = engine.analyze(rows, PROFILE, METRIC, "rank")["result"]
        self.assertEqual([r["row"] for r in result], [1, 2, 3])
        result = engine.analyze(rows, PROFILE, METRIC, "quality")["result"]
        self.assertEqual(result["issues"][0]["issue"], "repeated_entity")

    def test_group_sizes_and_histogram_boundaries(self):
        result = engine.analyze(self.rows([0, 1, 2, 3, 4, 5]), PROFILE, METRIC, "histogram")["result"]
        self.assertEqual([r["count"] for r in result], [1, 1, 1, 1, 2])
        self.assertEqual(sum(r["count"] for r in result), 6)


class NativeRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        setting = patch.object(runtime, "STATE_PATH", self.root / "settings.json")
        setting.start()
        self.addCleanup(setting.stop)

    def test_every_one_of_30000_entries_executes_and_matches_facts(self):
        report = runtime.verify_library()
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["counts"], {"skill": 10000, "agent": 10000, "plugin": 10000})
        self.assertEqual(report["total_executed"], 30000)

    def test_agent_stops_after_invalid_audit(self):
        rows = runtime.example(identity())
        rows[0][METRIC] = "broken"
        result = runtime.run_capability(identity("agent"), rows=rows)
        self.assertEqual(result["status"], "blocked_input")
        self.assertEqual([s["step"] for s in result["steps"]], ["audit"])

    def test_agent_preserves_audit_if_analysis_contract_fails(self):
        rows = runtime.example(identity())
        rows[0].pop(PROFILE["date"])
        result = runtime.run_capability(identity("agent", "trend"), rows=rows)
        self.assertEqual(result["status"], "blocked_input")
        self.assertEqual(result["failed_step"], "analysis")
        self.assertEqual(len(result["steps"]), 1)

    def test_disabled_plugin_blocks_direct_skill_and_agent_execution(self):
        runtime.set_enabled(identity(), False)
        self.assertFalse(runtime.get_capability(identity())["enabled"])
        for kind in ("plugin", "skill"):
            with self.assertRaises(ValueError):
                runtime.run_capability(identity(kind), rows=runtime.example(identity()))
        result = runtime.run_capability(identity("agent"), rows=runtime.example(identity()))
        self.assertEqual(result["status"], "blocked_input")
        runtime.set_enabled(identity(), True)
        self.assertEqual(runtime.run_capability(identity(), rows=runtime.example(identity()))["status"], "completed")

    def test_unknown_and_traversal_ids_rejected(self):
        for invalid in ("../../../etc/passwd", "kurt-plugin--../../etc--x--describe", identity() + "--extra", identity().replace("gross_sales", "absent")):
            with self.assertRaises(ValueError):
                runtime.get_capability(invalid)

    def test_skill_prompt_resolves_through_existing_manager(self):
        from kurt.skills.manager import get_skill_prompt
        prompt = get_skill_prompt(identity("skill"))
        self.assertIn(identity(), prompt)
        self.assertIn("gross_sales", prompt)
        self.assertGreaterEqual(len(prompt.split()), 200)

    def test_csv_json_and_non_destructive_output(self):
        rows = runtime.example(identity())
        data = self.root / "input.json"
        data.write_text(json.dumps(rows))
        before = data.read_bytes()
        output = self.root / "report.json"
        result = run_and_write(identity(), data, output)
        self.assertEqual(json.loads(output.read_text()), result)
        with self.assertRaises(FileExistsError):
            run_and_write(identity(), data, output)
        with self.assertRaises(ValueError):
            run_and_write(identity(), data, data)
        self.assertEqual(data.read_bytes(), before)
        csv_path = self.root / "input.csv"
        with csv_path.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        self.assertEqual(runtime.run_capability(identity(), input_path=csv_path)["report"]["result"]["sum"], 1160)

    def test_malformed_files_and_limits(self):
        for name, content in (("duplicates.csv", "a,a\n1,2\n"), ("extra.csv", "a\n1,2\n"),
                              ("duplicate.json", '[{"a":1,"a":2}]'), ("empty.json", "[]")):
            path = self.root / name
            path.write_text(content)
            with self.subTest(name=name), self.assertRaises(ValueError):
                engine.load_rows(path)
        path = self.root / "large.json"
        path.write_text(" " * 100)
        with patch.object(engine, "MAX_BYTES", 50), self.assertRaises(ValueError):
            engine.load_rows(path)

    def test_cli_chat_and_agent_tools_execute_same_report(self):
        from kurt.main import app
        from kurt.core.agent_loop import execute_tool
        from kurt.core.cli_orchestrator import handle_slash
        data = self.root / "data.json"
        data.write_text(json.dumps(runtime.example(identity())))
        runner = CliRunner()
        for args in (["library", "run", identity(), "--input", str(data)],
                     ["skill", "run", identity("skill"), "--input", str(data)],
                     ["plugin", "run", identity(), "--input", str(data)],
                     ["agent", "analyze", "--profile", identity("agent"), "--data", str(data)]):
            result = runner.invoke(app, args)
            self.assertEqual(result.exit_code, 0, result.output)
            self.assertEqual(json.loads(result.output)["status"], "completed")
        result = handle_slash(f'/library run {identity()} "{data}"', "test", None, None)
        self.assertEqual(json.loads(result.output)["report"]["result"]["sum"], 1160)
        result = execute_tool("run_native", {"capability_id": identity(), "input_path": str(data)})
        self.assertEqual(json.loads(result)["report"]["result"]["sum"], 1160)

    def test_search_is_bounded_and_model_gets_tools(self):
        from kurt.core.agent_loop import TOOLS_PROMPT
        rows = runtime.search("shopee gross_sales", kind="plugin", limit=10)
        self.assertEqual(len(rows), 10)
        self.assertTrue(all(row["domain"] == "shopee-orders" for row in rows))
        self.assertIn("search_native", TOOLS_PROMPT)
        self.assertIn("run_native", TOOLS_PROMPT)

    def test_agent_loop_discovers_runs_and_receives_native_result(self):
        from kurt.core import agent_loop
        from rich.console import Console
        data = self.root / "agent-input.json"
        data.write_text(json.dumps(runtime.example(identity())))
        case = self

        class ScriptedRouter:
            calls = 0

            async def route(self, provider, model, messages):
                if self.calls == 0:
                    tool = {"tool": "search_native", "params": {"query": "shopee gross_sales describe", "kind": "plugin"}}
                elif self.calls == 1:
                    case.assertIn(identity(), messages[-1]["content"])
                    tool = {"tool": "run_native", "params": {"capability_id": identity(), "input_path": str(data)}}
                else:
                    case.assertIn('"sum": 1160.0', messages[-1]["content"])
                    tool = {"tool": "done", "params": {"summary": "Read fixture records; computed total 1160."}}
                self.calls += 1
                yield "```tool\n" + json.dumps(tool) + "\n```"

        router = ScriptedRouter()
        with patch.object(agent_loop, "_build_mcp_tools_prompt", AsyncMock(return_value="")), patch.object(agent_loop, "console", Console(file=io.StringIO())):
            result = asyncio.run(agent_loop.run_agent("Analyze the supplied order export", SimpleNamespace(model="scripted-test", provider="test"), router, max_steps=3))
        self.assertTrue(result.success)
        self.assertEqual([s.tool_name for s in result.steps], ["search_native", "run_native", "done"])


if __name__ == "__main__":
    unittest.main()
