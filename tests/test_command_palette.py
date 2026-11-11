import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from kurt.core import cli_orchestrator as orch
from kurt.core import mcp_client as client
from kurt.skills import manager


class ModelProviderTagTests(unittest.TestCase):
    def test_explicit_provider_tag_is_encoded_in_model_override(self):
        result = orch.handle_slash(
            prompt="/model black-forest-labs/flux-schnell fal",
            session_id="s1", current_model="auto", current_skill=None, last_response="",
        )
        self.assertTrue(result.handled)
        self.assertEqual(result.model_override, "black-forest-labs/flux-schnell|fal")

    def test_plain_model_id_has_no_provider_tag(self):
        result = orch.handle_slash(
            prompt="/model openai/gpt-4.1",
            session_id="s1", current_model="auto", current_skill=None, last_response="",
        )
        self.assertTrue(result.handled)
        self.assertEqual(result.model_override, "openai/gpt-4.1")

    def test_main_py_resolves_explicit_tag_over_the_shape_heuristic(self):
        # black-forest-labs/flux-schnell looks exactly like an OpenRouter id
        # (vendor/name, no anthropic/claude prefix) — only the explicit "|fal"
        # tag, not the shape of the string, should decide the provider.
        current_model = "black-forest-labs/flux-schnell|fal"

        class Analysis:
            pass

        analysis = Analysis()
        if "|" in current_model:
            analysis.model, analysis.provider = current_model.rsplit("|", 1)
        self.assertEqual((analysis.model, analysis.provider), ("black-forest-labs/flux-schnell", "fal"))


class ModelPaletteDataTests(unittest.TestCase):
    def test_fal_models_skipped_without_api_key(self):
        from kurt.core import command_palette as cp
        with patch.object(cp, "_fal_cache", None), patch.dict(os.environ, {}, clear=False):
            os.environ.pop("FAL_API_KEY", None)
            self.assertEqual(cp._fal_models(), [])

    def test_model_items_include_openrouter_entries(self):
        from kurt.core import command_palette as cp
        fake = [{"id": "openai/gpt-4.1", "name": "OpenAI: GPT-4.1"}]
        with patch.object(cp, "_openrouter_cache", fake):
            items = cp._model_items("")
        self.assertTrue(any(i["value"] == "/model openai/gpt-4.1" and "[openrouter]" in i["label"]
                             for i in items))


class SkillsDataTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        p = patch.object(manager, "SKILLS_DIR", Path(self.tmp.name) / "skills")
        p.start()
        self.addCleanup(p.stop)

    def test_builtin_skills_are_exactly_seven(self):
        skills = [s for s in manager.get_all_skills(include_native=False) if s.get("builtin")]
        self.assertEqual(len(skills), 7)
        self.assertEqual(
            {s["id"] for s in skills},
            {"tiktok", "copywriting", "seo", "trading", "filipino", "game-dev", "ecommerce"},
        )


class PresetTests(unittest.TestCase):
    def test_known_presets(self):
        self.assertEqual(
            set(client.PRESETS.keys()),
            {"filesystem", "github", "postgres", "brave-search", "sqlite", "puppeteer"},
        )

    def test_get_preset_resolves_and_rejects_unknown(self):
        self.assertIsNotNone(client.get_preset("sqlite"))
        self.assertIsNone(client.get_preset("nonexistent"))


class ConnectPresetSlashCommandTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        for key, value in (("KURT_DIR", root), ("MCP_REGISTRY_PATH", root / "connections.json")):
            p = patch.object(client, key, value)
            p.start()
            self.addCleanup(p.stop)

    def test_connect_preset_persists_to_registry(self):
        result = orch.handle_slash(
            prompt="/mcp connect-preset sqlite",
            session_id="s1",
            current_model="auto",
            current_skill=None,
            last_response="",
        )
        self.assertTrue(result.handled)
        registry = client.load_registry()
        self.assertIn("sqlite", registry)
        self.assertEqual(registry["sqlite"].transport, "stdio")

    def test_connect_preset_unknown_name(self):
        result = orch.handle_slash(
            prompt="/mcp connect-preset not-a-real-preset",
            session_id="s1",
            current_model="auto",
            current_skill=None,
            last_response="",
        )
        self.assertTrue(result.handled)
        self.assertIn("Unknown preset", result.output)
        self.assertEqual(client.load_registry(), {})


if __name__ == "__main__":
    unittest.main()
