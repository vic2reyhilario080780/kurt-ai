import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from kurt.capabilities.bridge import function_schemas
from kurt.core.assistant_tools import ACTION_NAMES, DESKTOP_NAMES, invoke_assistant


class ToolRegistrationTests(unittest.TestCase):
    def test_new_tools_are_exposed_to_providers(self):
        names = {s["function"]["name"] for s in function_schemas()}
        self.assertIn("analyze_screen", names)
        self.assertIn("click_at_coordinates", names)

    def test_click_at_coordinates_is_gated_as_an_action(self):
        self.assertIn("click_at_coordinates", ACTION_NAMES)

    def test_analyze_screen_is_read_only(self):
        self.assertNotIn("analyze_screen", ACTION_NAMES)
        self.assertIn("analyze_screen", DESKTOP_NAMES)


class ClickAtCoordinatesTests(unittest.TestCase):
    def test_dispatches_a_real_click_within_screen_bounds(self):
        with patch("kurt.core.computer_use.get_screen_size", return_value=(1920, 1080)), \
             patch("kurt.core.computer_use.focus_window", return_value=MagicMock(success=True)), \
             patch("kurt.core.computer_use.click", return_value=MagicMock(success=True, message="ok")) as click:
            result = invoke_assistant("click_at_coordinates", {"app": "Music", "x": 100, "y": 200})
        click.assert_called_once_with(100, 200)
        self.assertEqual(result["status"], "dispatched")
        self.assertTrue(result["focus_verified"])

    def test_rejects_out_of_bounds_coordinates_without_clicking(self):
        with patch("kurt.core.computer_use.get_screen_size", return_value=(1920, 1080)), \
             patch("kurt.core.computer_use.click", side_effect=AssertionError("must not click")):
            with self.assertRaises(ValueError):
                invoke_assistant("click_at_coordinates", {"app": "Music", "x": 99999, "y": 200})

    def test_reports_focus_failure_without_raising(self):
        with patch("kurt.core.computer_use.get_screen_size", return_value=(1920, 1080)), \
             patch("kurt.core.computer_use.focus_window", return_value=MagicMock(success=False)), \
             patch("kurt.core.computer_use.click", return_value=MagicMock(success=True, message="ok")):
            result = invoke_assistant("click_at_coordinates", {"app": "Ghost App", "x": 1, "y": 1})
        self.assertFalse(result["focus_verified"])


class AnalyzeScreenTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.img = Path(self.tmp.name) / "fake.png"
        self.img.write_bytes(b"not a real png, fine for this mocked test")

    def test_missing_file_returns_error_without_calling_vision(self):
        with patch("kurt.core.vision.describe_screen", side_effect=AssertionError("must not run")):
            result = invoke_assistant("analyze_screen", {"mode": "describe", "path": "/no/such/file.png"})
        self.assertEqual(result["status"], "error")
        self.assertIn("not found", result["reason"])

    def test_describe_mode_returns_model_description(self):
        with patch("kurt.core.vision.load_image_b64", return_value="ZmFrZQ=="), \
             patch("kurt.core.vision.describe_screen",
                   return_value=MagicMock(success=True, description="A music app is open.",
                                           model_used="llava", elements=[])):
            result = invoke_assistant("analyze_screen", {"mode": "describe", "path": str(self.img)})
        self.assertEqual(result, {"status": "completed", "description": "A music app is open.",
                                   "model_used": "llava", "elements": []})

    def test_find_mode_passes_query_as_element_description(self):
        with patch("kurt.core.vision.load_image_b64", return_value="ZmFrZQ=="), \
             patch("kurt.core.vision.find_element", return_value=MagicMock(
                 success=True, description="FOUND: yes", model_used="llava", elements=[{"x": 400, "y": 120}])) as fe:
            result = invoke_assistant("analyze_screen", {"mode": "find", "path": str(self.img), "query": "search bar"})
        fe.assert_called_once_with("ZmFrZQ==", element_description="search bar")
        self.assertEqual(result["elements"], [{"x": 400, "y": 120}])

    def test_vision_failure_is_reported_not_raised(self):
        with patch("kurt.core.vision.load_image_b64", return_value="ZmFrZQ=="), \
             patch("kurt.core.vision.describe_screen",
                   return_value=MagicMock(success=False, error="Local vision unavailable")):
            result = invoke_assistant("analyze_screen", {"mode": "describe", "path": str(self.img)})
        self.assertEqual(result, {"status": "error", "reason": "Local vision unavailable"})


if __name__ == "__main__":
    unittest.main()
