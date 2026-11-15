import asyncio
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import httpx
from rich.console import Console

from kurt.core import execution_preferences as prefs, persona, command_palette as palette
from kurt.core.cli_orchestrator import handle_slash
from kurt.core.assistant_tools import invoke_assistant
from kurt.core.router import ModelRouter


class MediaDefaultsTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        for name, value in (("KURT_DIR", Path(tmp.name)), ("PERSONA_PATH", Path(tmp.name) / "persona.json")):
            context = patch.object(persona, name, value)
            context.start()
            self.addCleanup(context.stop)

    def test_image_and_video_defaults_persist_without_changing_chat_or_cli(self):
        prefs.save_default_model("mistral-small-latest", "mistral")
        prefs.save_default_cli("claude")
        for command in ("/image-model fal-ai/flux/schnell fal", "/video-model owner/video replicate"):
            result = handle_slash(command, "test", "auto", None)
            self.assertIn("saved", result.output)
        saved = persona.load_persona()
        self.assertEqual(saved["default_cli"], "claude")
        self.assertEqual(saved["default_model"], "mistral-small-latest|mistral")
        self.assertEqual(prefs.media_target("image"), {"model": "fal-ai/flux/schnell", "provider": "fal"})
        self.assertEqual(prefs.media_target("video"), {"model": "owner/video", "provider": "replicate"})
        handle_slash("/video-model auto", "test", "auto", None)
        self.assertEqual(persona.load_persona()["default_video_model"], "auto")
        self.assertEqual(persona.load_persona()["default_image_model"], "fal-ai/flux/schnell|fal")

    def test_bad_provider_or_model_url_never_overwrites_saved_selection(self):
        prefs.save_default_media("image", "fal-ai/flux/schnell", "fal")
        before = persona.PERSONA_PATH.read_text()
        for model, provider in (("gpt-test", "openai"), ("https://example.org", "fal"), ("../model", "fal"), ("owner/model?secret=x", "replicate")):
            with self.subTest(model=model), self.assertRaises(ValueError):
                prefs.save_default_media("image", model, provider)
            self.assertEqual(persona.PERSONA_PATH.read_text(), before)

    def test_generation_uses_saved_provider_model_and_media_kind(self):
        prefs.save_default_media("video", "owner/custom-video", "replicate")
        calls = []
        async def generate(provider, model, messages, **kwargs):
            calls.append((provider, model, messages, kwargs))
            yield "https://example.org/video.mp4"
        with patch("kurt.core.router.ModelRouter") as router:
            router.return_value._has_key.return_value = True
            router.return_value.route = generate
            result = invoke_assistant("generate_media", {"kind": "video", "prompt": "A blue bird"})
        self.assertEqual(calls[0][:2], ("replicate", "owner/custom-video"))
        self.assertEqual(calls[0][3], {"media_kind": "video"})
        self.assertTrue(router.return_value.strict_selection)
        self.assertEqual(result["output"], "https://example.org/video.mp4")
        self.assertEqual(result["provider"], "replicate")

    def test_missing_selected_key_blocks_instead_of_using_chat_provider(self):
        prefs.save_default_media("image", "owner/image", "replicate")
        with patch("kurt.core.router.ModelRouter") as router:
            router.return_value._has_key.return_value = False
            result = invoke_assistant("generate_media", {"kind": "image", "prompt": "A circle"})
        self.assertEqual(result["status"], "blocked")
        self.assertIn("replicate", result["reason"])
        router.return_value.route.assert_not_called()

    def test_model_pickers_filter_by_generation_category(self):
        models = [{"id": "fal-ai/picture", "category": "text-to-image"},
                  {"id": "fal-ai/movie", "category": "text-to-video"},
                  {"id": "fal-ai/edit", "category": "image-to-image"},
                  {"id": "fal-ai/animate", "category": "image-to-video"}]
        with patch.object(palette, "_fal_models", return_value=models):
            image = palette._media_model_items("image", "")
            video = palette._media_model_items("video", "")
        self.assertTrue(any(i.get("value") == "/image-model fal-ai/picture fal" for i in image))
        self.assertTrue(any(i.get("value") == "/video-model fal-ai/movie fal" for i in video))
        self.assertFalse(any("fal-ai/animate" in i.get("value", "") or "fal-ai/movie" in i.get("value", "") for i in image))
        self.assertFalse(any("fal-ai/edit" in i.get("value", "") or "fal-ai/picture" in i.get("value", "") for i in video))
        self.assertEqual(palette._config_items("image")[0]["target"], "media_image")

    def test_banner_displays_all_four_defaults_at_common_terminal_widths(self):
        from kurt.main import _kurt_welcome_banner
        defaults = {"default_model": "mistral-small-latest|mistral", "default_cli": "claude",
                    "default_image_model": "fal-ai/flux/schnell|fal", "default_video_model": "owner/video|replicate"}
        for width in (60, 80, 120):
            with self.subTest(width=width):
                out = io.StringIO()
                console = Console(file=out, width=width, color_system=None)
                console.print(_kurt_welcome_banner("Kurt", "test", {"primary": "cyan"}, "Boss", "CLI: claude", None, "test", defaults=defaults))
                text = "".join(out.getvalue().split())
                for expected in ("Chatdefault:", "CLIdefault:", "Imagedefault:", "Videodefault:", "mistral-small-latest[mistral]", "claude", "fal-ai/flux/schnell[fal]", "owner/video[replicate]"):
                    self.assertIn(expected, text)

    def test_fal_image_and_video_outputs_are_parsed_without_duplicate_posts(self):
        real_client = httpx.AsyncClient
        for kind, payload in (("image", {"images": [{"url": "https://example.org/image.png"}]}),
                              ("video", {"video": {"url": "https://example.org/video.mp4"}})):
            calls = []
            def handler(request):
                calls.append(request)
                self.assertEqual(json.loads(request.content)["prompt"], "A blue bird")
                return httpx.Response(200, json=payload)
            with self.subTest(kind=kind), patch.dict(os.environ, {"FAL_API_KEY": "synthetic-key"}), \
                 patch("kurt.core.router.httpx.AsyncClient", lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw)):
                async def collect():
                    return [c async for c in ModelRouter().call_fal("A blue bird", "fal-ai/test", media_kind=kind)]
                result = asyncio.run(collect())
            self.assertEqual(len(calls), 1)
            self.assertEqual(len(result), 1)
            self.assertIn(f"/{kind}.", result[0])


if __name__ == "__main__":
    unittest.main()
