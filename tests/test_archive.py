import tempfile
import unittest
import zipfile
from pathlib import Path

from kurt.core import cli_orchestrator as orch
from kurt.core.archive import export_folder, import_zip


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.src = self.root / "myapp"
        self.src.mkdir()
        (self.src / "main.py").write_text("print(1)")
        (self.src / "sub").mkdir()
        (self.src / "sub" / "util.py").write_text("x = 1")

    def test_export_then_import_round_trips_all_files(self):
        zip_path = export_folder(str(self.src))
        self.assertTrue(Path(zip_path).exists())
        dest = self.root / "restored"
        out = import_zip(zip_path, str(dest))
        self.assertEqual(Path(out).resolve(), dest.resolve())
        restored = {p.relative_to(dest) for p in dest.rglob("*") if p.is_file()}
        self.assertEqual(restored, {Path("main.py"), Path("sub/util.py")})

    def test_export_rejects_non_directory(self):
        with self.assertRaises(ValueError):
            export_folder(str(self.src / "main.py"))

    def test_import_rejects_zip_slip_path_traversal(self):
        evil_zip = self.root / "evil.zip"
        with zipfile.ZipFile(evil_zip, "w") as zf:
            zf.writestr("../../etc/evil.txt", "pwned")
        dest = self.root / "safe_extract"
        with self.assertRaises(ValueError):
            import_zip(str(evil_zip), str(dest))
        self.assertFalse((self.root.parent / "etc" / "evil.txt").exists())

    def test_import_rejects_non_zip_file(self):
        with self.assertRaises(ValueError):
            import_zip(str(self.src / "main.py"))

    def test_slash_command_round_trip(self):
        result = orch.handle_slash(
            prompt=f"/zip export {self.src}",
            session_id="s1", current_model="auto", current_skill=None, last_response="",
        )
        self.assertTrue(result.handled)
        self.assertIn("✅ Exported", result.output)

        result2 = orch.handle_slash(
            prompt=f"/zip import {self.src}.zip {self.root}/out",
            session_id="s1", current_model="auto", current_skill=None, last_response="",
        )
        self.assertTrue(result2.handled)
        self.assertIn("✅ Imported", result2.output)
        self.assertTrue((self.root / "out" / "main.py").exists())

    def test_slash_command_usage_without_args(self):
        result = orch.handle_slash(
            prompt="/zip", session_id="s1", current_model="auto", current_skill=None, last_response="",
        )
        self.assertTrue(result.handled)
        self.assertIn("Usage", result.output)


if __name__ == "__main__":
    unittest.main()
