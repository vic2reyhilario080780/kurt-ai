import io
import asyncio
import tempfile
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

from rich.console import Console
from typer.testing import CliRunner

from kurt.core import command_palette as palette, persona
from kurt.core.execution_preferences import save_default_model


class SettingsPickerTests(unittest.TestCase):
    def test_vibe_is_discoverable_in_cli_picker(self):
        with patch('kurt.core.cli_orchestrator._cmd_exists', return_value=True):
            rows = palette._cli_default_items('vibe')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['value'], '/cli default vibe')
        self.assertIn('Mistral Vibe', rows[0]['label'])

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        for name, value in (("KURT_DIR", Path(temp.name)), ("PERSONA_PATH", Path(temp.name) / "persona.json")):
            context = patch.object(persona, name, value)
            context.start()
            self.addCleanup(context.stop)

    def test_chat_pickers_exclude_media_and_transcription_but_keep_vision_input(self):
        models = [
            {"id": "test/chat", "architecture": {"input_modalities": ["text", "image"], "output_modalities": ["text"]},
             "pricing": {"prompt": "0.001", "completion": "0.002"}},
            {"id": "test/image", "architecture": {"output_modalities": ["image"]}},
            {"id": "test/mixed", "architecture": {"output_modalities": ["text", "image"]}},
            {"id": "test/video", "architecture": {"output_modalities": ["video"]}},
            {"id": "test/unknown"},
        ]
        with patch.object(palette.items, "_openrouter_models", return_value=models), patch.object(palette.items, "_fal_models") as fal:
            session = palette._model_items("")
            defaults = palette._default_model_items("")
        for items in (session, defaults):
            values = " ".join(i.get("value", "") for i in items)
            self.assertIn("test/chat", values)
            for blocked in ("test/image", "test/mixed", "test/video", "test/unknown", "whisper", "flux", "wan-2.1", "musicgen"):
                self.assertNotIn(blocked, values)
        fal.assert_not_called()
        paid = [i for i in defaults if "test/chat" in i.get("value", "")]
        self.assertIn("Paid", paid[0]["label"])

    def test_pricing_is_not_guessed_when_metadata_is_missing(self):
        self.assertEqual(palette._pricing_hint({}), "pricing unavailable")
        self.assertEqual(palette._pricing_hint({"pricing": {"prompt": "0", "completion": "0"}}), "Free")
        self.assertEqual(palette._pricing_hint({"pricing": {"prompt": "nan", "completion": "0"}}), "pricing unavailable")

    def test_four_distinct_roles_are_reachable_from_setting(self):
        self.assertEqual(palette.OPEN_TARGETS["/setting"], "execution_defaults")
        items = palette._execution_default_items("")
        self.assertEqual({i["target"] for i in items}, {"default_models", "cli_settings", "media_image", "media_video"})

    def test_saving_media_as_chat_default_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "image-model"):
            save_default_model("fal-ai/flux/schnell", "fal")
        self.assertFalse(persona.PERSONA_PATH.exists())

    def test_native_picker_runs_the_same_saved_settings_action(self):
        state = palette._PaletteState()
        session = Mock()
        session.prompt.return_value = "/cli default claude"
        with patch.object(palette.engine, "_build_session", return_value=(session, state)), \
             patch("sys.stdin.isatty", return_value=True), \
             patch("kurt.utils.env_loader.load_env"), patch("rich.console.Console", return_value=Console(file=io.StringIO())):
            self.assertTrue(palette.pick_execution_default("cli"))
        self.assertEqual(state.view, "cli_settings")
        self.assertEqual(persona.load_persona()["default_cli"], "claude")

    def test_native_picker_cannot_run_unrelated_commands(self):
        session = Mock()
        session.prompt.return_value = "/run echo unexpected"
        with patch.object(palette.engine, "_build_session", return_value=(session, palette._PaletteState())), \
             patch("sys.stdin.isatty", return_value=True), patch("kurt.utils.env_loader.load_env"), \
             patch("kurt.core.cli_orchestrator.handle_slash") as dispatch:
            self.assertFalse(palette.pick_execution_default())
        dispatch.assert_not_called()
        self.assertFalse(persona.PERSONA_PATH.exists())

    def test_kurt_setting_and_subcommands_open_the_right_picker(self):
        from kurt import main
        for kind in (None, "model", "cli", "image", "video"):
            with self.subTest(kind=kind), patch.object(palette, "pick_execution_default") as picker, patch("sys.stdin.isatty", return_value=True):
                if kind is None:
                    main.config_callback(Mock(invoked_subcommand=None))
                    picker.assert_called_once_with()
                elif kind == "model":
                    main.config_default_model_cmd(model=None, provider=None)
                    picker.assert_called_once_with(kind)
                elif kind == "cli":
                    main.config_default_cli_cmd(cli=None)
                    picker.assert_called_once_with(kind)
                else:
                    main._setting_media(kind, None, None)
                    picker.assert_called_once_with(kind)

    def test_noninteractive_settings_still_report_without_prompting(self):
        from kurt import main
        with patch.object(palette, "pick_execution_default") as picker:
            result = CliRunner().invoke(main.app, ["setting", "model"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("Default model:", result.output)
        picker.assert_not_called()


class NativePickerKeyboardTests(unittest.IsolatedAsyncioTestCase):
    async def test_four_way_picker_saves_cli_using_real_keyboard_navigation(self):
        from prompt_toolkit.input.defaults import create_pipe_input
        from prompt_toolkit.output import DummyOutput
        real_session = palette.PromptSession
        with tempfile.TemporaryDirectory() as temp, create_pipe_input() as pipe, \
             patch.object(persona, "KURT_DIR", Path(temp)), \
             patch.object(persona, "PERSONA_PATH", Path(temp) / "persona.json"), \
             patch("sys.stdin.isatty", return_value=True), \
             patch("kurt.utils.env_loader.load_env"), \
             patch.object(palette.engine, "PromptSession", lambda **kw: real_session(input=pipe, output=DummyOutput(), **kw)):
            task = asyncio.create_task(asyncio.to_thread(palette.pick_execution_default))
            try:
                await asyncio.sleep(.05)
                pipe.send_text("cli\r")
                await asyncio.sleep(.05)
                pipe.send_text("claude\r")
                self.assertTrue(await asyncio.wait_for(task, 2))
                self.assertEqual(persona.load_persona()["default_cli"], "claude")
            finally:
                pipe.send_text("\x03")


if __name__ == "__main__":
    unittest.main()
