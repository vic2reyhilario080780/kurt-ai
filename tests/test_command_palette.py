import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
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
        fake = [{"id": "openai/gpt-4.1", "name": "OpenAI: GPT-4.1", "architecture": {"output_modalities": ["text"]}}]
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

    async def _fake_probe(self, conn):
        from kurt.core.mcp_client import MCPTool
        return [MCPTool(name="t", description="", server_name=conn.name)]

    def test_connect_preset_persists_to_registry(self):
        with patch.object(client, "probe_connection", self._fake_probe):
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
        buf = io.StringIO()
        with redirect_stdout(buf):
            result = orch.handle_slash(
                prompt="/mcp connect-preset not-a-real-preset",
                session_id="s1",
                current_model="auto",
                current_skill=None,
                last_response="",
            )
        self.assertTrue(result.handled)
        self.assertIn("Unknown server", buf.getvalue())
        self.assertEqual(client.load_registry(), {})

    def test_authorize_alias_also_persists_preset(self):
        with patch.object(client, "probe_connection", self._fake_probe):
            result = orch.handle_slash(
                prompt="/mcp authorize sqlite",
                session_id="s1",
                current_model="auto",
                current_skill=None,
                last_response="",
            )
        self.assertTrue(result.handled)
        self.assertIn("sqlite", client.load_registry())

    def test_authorize_reports_missing_field_without_blocking_when_not_a_tty(self):
        # github preset needs GITHUB_PERSONAL_ACCESS_TOKEN — with no real
        # tty (as in a test run) this must describe what's missing instead
        # of calling Prompt.ask and hanging forever waiting for stdin.
        # github is a remote http preset (Authorization header) whose own
        # server has no OAuth metadata (confirmed against the real
        # api.githubcopilot.com endpoint) — mock that discovery call so
        # the test doesn't depend on network access.
        from kurt.core import mcp_oauth
        with patch.dict(client.PRESETS["github"].headers, {"Authorization": ""}), \
             patch.object(mcp_oauth, "authorize", side_effect=mcp_oauth.NotOAuthProtected("github")):
            buf = io.StringIO()
            with redirect_stdout(buf):
                result = orch.handle_slash(
                    prompt="/mcp authorize github",
                    session_id="s1",
                    current_model="auto",
                    current_skill=None,
                    last_response="",
                )
        self.assertTrue(result.handled)
        self.assertIn("Needs: Authorization", buf.getvalue())
        self.assertIn("https://github.com/settings/tokens", buf.getvalue())
        self.assertNotIn("github", client.load_registry())


class ConnectorDirectoryTests(unittest.TestCase):
    """The full bundled Composio/Zapier/n8n directories (not just the
    small hand-curated subsets) that back the command palette's pickers."""

    def test_bundled_directories_are_large_and_deduplicated(self):
        from kurt.hub.composio import load_toolkits
        from kurt.hub.mcp_servers import load_zapier_apps, load_n8n_integrations

        for loader, minimum in ((load_toolkits, 1000), (load_zapier_apps, 9000), (load_n8n_integrations, 2000)):
            slugs = loader()
            with self.subTest(loader=loader.__name__):
                self.assertGreaterEqual(len(slugs), minimum)
                self.assertEqual(len(slugs), len(set(slugs)))

    def test_connector_picker_covers_full_composio_directory(self):
        from kurt.core.command_palette import _connector_items
        items = _connector_items("")
        self.assertGreaterEqual(len(items), 1000)
        self.assertTrue(any(i["target"] == "connector:composio:gmail" for i in items))

    def test_zapier_and_n8n_pickers_open_setup_menus(self):
        from kurt.core.command_palette import _zapier_picker_items, _n8n_picker_items
        zap = _zapier_picker_items("shopify")
        n8n = _n8n_picker_items("slack")
        self.assertTrue(zap and all(i["kind"] == "open" and i["target"].startswith("connector:zapier:") for i in zap))
        self.assertTrue(n8n and all(i["kind"] == "open" and i["target"].startswith("connector:n8n:") for i in n8n))

    def test_zapier_open_and_n8n_open_navigate_to_the_real_integration_page(self):
        from kurt.hub import mcp_servers
        with patch.object(mcp_servers.webbrowser, "open") as fake_open:
            result = orch.handle_slash(prompt="/zapier open shopify", session_id="s1",
                                        current_model="auto", current_skill=None, last_response="")
            self.assertTrue(result.handled)
            fake_open.assert_called_with("https://zapier.com/apps/shopify/integrations")

            result = orch.handle_slash(prompt="/n8n open slack", session_id="s1",
                                        current_model="auto", current_skill=None, last_response="")
            self.assertTrue(result.handled)
            fake_open.assert_called_with("https://n8n.io/integrations/slack/")


class PaletteRenderingTests(unittest.TestCase):
    def test_violet_items_aligned_descriptions_and_non_clickable_info_skipping(self):
        from kurt.core import command_palette as cp
        rows = [
            {"label": "Header count info", "kind": "info"},
            {"label": "Hugging Face — Full Hub — 277 additional models", "kind": "open", "target": "catalog_provider:huggingface_hub"},
            {"label": "Qwen3 [Qwen/Qwen3-14B] — Text Generation — default: chat", "kind": "open", "target": "catalog_model:huggingface_inference:Qwen"},
            {"label": "Footer scope description", "kind": "info"},
            {"label": "Load next catalog pages", "kind": "provider_more", "provider": "huggingface_hub"},
        ]
        # Navigation helpers skip info rows cleanly
        self.assertEqual(cp._first_selectable(rows), 1)
        self.assertEqual(cp._step_selectable(rows, 1, 1), 2)
        self.assertEqual(cp._step_selectable(rows, 2, 1), 4)
        self.assertEqual(cp._step_selectable(rows, 4, 1), 1)
        self.assertEqual(cp._step_selectable(rows, 1, -1), 4)
        # Splitting preserves HF provider names and 3-column model rows
        self.assertEqual(cp._split_item_columns(rows[1]), ("Hugging Face — Full Hub", "277 additional models", ""))
        self.assertEqual(cp._split_item_columns(rows[2]), ("Qwen3 [Qwen/Qwen3-14B]", "Text Generation", "default: chat"))
        # Rendering uses violet item styles, sky-cyan descriptions, emerald runnable badge, and ℹ for info rows
        state = cp._PaletteState(is_open=True, view="model_catalog", index=1)
        with patch.object(cp, "_current_items", return_value=rows):
            fragments = cp._render(state, "/")
        rendered = "".join(t for _, t in fragments)
        self.assertIn("ℹ Header count info", rendered)
        self.assertNotIn("▶ Header count info", rendered)
        self.assertTrue(any(s == cp._STYLE_ITEM_SELECTED and "Hugging Face — Full Hub" in t for s, t in fragments))
        self.assertTrue(any(s == cp._STYLE_ITEM and "Qwen3 [Qwen/Qwen3-14B]" in t for s, t in fragments))
        self.assertTrue(any(s == cp._STYLE_DESC_SELECTED and "277 additional models" in t for s, t in fragments))
        self.assertTrue(any(s == cp._STYLE_BADGE_OK and "default: chat" in t for s, t in fragments))
        self.assertTrue(any(s == cp._STYLE_INFO and "ℹ Footer scope description" in t for s, t in fragments))
        # Aligned description columns start at matching visual offsets
        lines = [ln for ln in rendered.splitlines() if "277 additional models" in ln or "Text Generation" in ln]
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0].index("277 additional models"), lines[1].index("Text Generation"))

    def test_config_pickers_theme_backgrounds_and_converted_slash_pickers(self):
        from kurt.core import command_palette as cp, persona
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.object(persona, "KURT_DIR", root), \
                 patch.object(persona, "PERSONA_PATH", root / "persona.json"), \
                 patch.object(manager, "SKILLS_DIR", root / "skills"):
                # All config choices open pickers (no manual typing)
                cfg_items = cp._config_items("")
                targets = {r.get("target") for r in cfg_items if r.get("kind") == "open"}
                for expected in ("config_theme", "config_background", "config_icon", "config_language",
                                 "config_voice", "config_greeting", "config_aimode", "config_display",
                                 "config_reset", "default_models", "cli_settings", "media_image", "media_video"):
                    self.assertIn(expected, targets)
                # Theme & background pickers carry live per-row bg_hex swatches
                theme_rows = cp._config_theme_items("")
                violet_row = next(r for r in theme_rows if r.get("value") == "/config theme violet")
                self.assertEqual(violet_row["bg_hex"], "#160a2b")
                state = cp._PaletteState(is_open=True, view="config_theme", index=1)
                fragments = cp._render(state, "/")
                self.assertTrue(any("bg:#160a2b" in s for s, _ in fragments))
                # Direct one-shot /config commands save without prompting and update dynamic toolbar bg
                for cmd_str in (
                    "/config theme violet",
                    "/config icon crown",
                    "/config language tl",
                    "/config voice default",
                    "/config greeting hype",
                    "/config aimode kurt_only",
                    "/config compact on",
                    "/config routing on",
                ):
                    res = orch.handle_slash(cmd_str, "s1", "auto", None)
                    self.assertTrue(res.handled)
                    self.assertIn("✅", res.output)
                saved = persona.load_persona()
                self.assertEqual(saved["theme"], "violet")
                self.assertEqual(saved["icon"], "crown")
                self.assertEqual(saved["language"], "tl")
                self.assertEqual(saved["voice"], "default")
                self.assertEqual(saved["greeting_style"], "hype")
                self.assertEqual(saved["ai_mode"], "kurt_only")
                self.assertTrue(saved["compact_mode"])
                self.assertTrue(saved["show_routing_info"])
                self.assertEqual(cp._active_bg_hex(), "#160a2b")
                # Custom background override & transparent mode
                res = orch.handle_slash("/config background royal_navy", "s1", "auto", None)
                self.assertIn("#071426", res.output)
                self.assertEqual(cp._active_bg_hex(), "#071426")
                self.assertEqual(persona.get_theme()["background"], "on #071426")
                res = orch.handle_slash("/config background none", "s1", "auto", None)
                self.assertEqual(cp._active_bg_hex(), "")
                self.assertEqual(persona.get_theme()["background"], "")
                # Cancel reset preserves settings
                res = orch.handle_slash("/config reset cancel", "s1", "auto", None)
                self.assertEqual(persona.load_persona()["theme"], "violet")
                # All previously non-picker slash menus now open real pickers
                for slash_cmd, view_name in (
                    ("/skill", "skills"),
                    ("/speech", "speech"),
                    ("/wallet", "wallet"),
                    ("/doctor", "doctor"),
                    ("/computer", "computer"),
                    ("/browser", "browser"),
                    ("/tasks", "tasks"),
                    ("/library", "library"),
                ):
                    self.assertEqual(cp.OPEN_TARGETS[slash_cmd], view_name)
                    items = cp._current_items(cp._PaletteState(is_open=True, view=view_name), "")
                    self.assertTrue(any(r.get("kind") == "leaf" for r in items), f"No leaf rows in {view_name}")


if __name__ == "__main__":
    unittest.main()
