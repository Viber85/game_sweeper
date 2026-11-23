"""Destructive path safety tests use disposable temporary directories only."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cleanup import CleanupError, execute_cleanup, preview_cleanup


class CleanupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name) / "home"
        self.apps = self.home / ".local/share/Steam/steamapps"
        self.apps.mkdir(parents=True)
        self.library = str(self.apps.parent)
        self.cache = self.home / "gamesweep-cache.json"

    def test_delete_shader_does_not_touch_prefix(self):
        prefix = self.apps / "compatdata/3456"
        shader = self.apps / "shadercache/3456"
        prefix.mkdir(parents=True)
        shader.mkdir(parents=True)
        (prefix / "savegame").write_bytes(b"saved")
        (shader / "shader").write_bytes(b"x" * 32)
        preview = preview_cleanup(self.home, self.cache, self.library, "3456", "shader")
        self.assertEqual(preview["bytes"], 32)
        result = execute_cleanup(self.home, self.cache, preview)
        self.assertTrue(result["success"])
        self.assertFalse(shader.exists())
        self.assertEqual((prefix / "savegame").read_bytes(), b"saved")

    def test_installed_game_is_protected(self):
        (self.apps / "compatdata/1091500").mkdir(parents=True)
        (self.apps / "appmanifest_1091500.acf").write_text(
            '"AppState" { "appid" "1091500" "name" "Cyberpunk 2077" }'
        )
        with self.assertRaisesRegex(CleanupError, "authorization"):
            preview_cleanup(self.home, self.cache, self.library, "1091500", "prefix")

    def test_protect_if_manifest_appears_after_confirmation(self):
        (self.apps / "compatdata/3456").mkdir(parents=True)
        preview = preview_cleanup(self.home, self.cache, self.library, "3456", "prefix")
        (self.apps / "appmanifest_3456.acf").write_text(
            '"AppState" { "appid" "3456" "name" "New Installation" }'
        )
        with self.assertRaisesRegex(CleanupError, "protected"):
            execute_cleanup(self.home, self.cache, preview)
        self.assertTrue((self.apps / "compatdata/3456").exists())

    def test_path_injection_rejected(self):
        (self.apps / "compatdata/3456").mkdir(parents=True)
        for appid in ("../3456", "-1", "3456/../9", "notanid"):
            with self.subTest(appid=appid), self.assertRaises(CleanupError):
                preview_cleanup(self.home, self.cache, self.library, appid, "prefix")
        with self.assertRaises(CleanupError):
            preview_cleanup(self.home, self.cache, self.library, "3456", "../shadercache")

    def test_unavailable_external_library_blocks_deletion(self):
        (self.apps / "libraryfolders.vdf").write_text(
            '"libraryfolders" { "1" { "path" "/unplugged/example" } }'
        )
        (self.apps / "compatdata/3456").mkdir(parents=True)
        with self.assertRaisesRegex(CleanupError, "offline"):
            preview_cleanup(self.home, self.cache, self.library, "3456", "prefix")

    def test_inode_swap_after_preview_blocks_deletion(self):
        target = self.apps / "compatdata/3456"
        target.mkdir(parents=True)
        preview = preview_cleanup(self.home, self.cache, self.library, "3456", "prefix")
        old = self.apps / "compatdata/old"
        target.rename(old)
        target.mkdir()
        (target / "important").write_text("keep")
        with self.assertRaisesRegex(CleanupError, "changed"):
            execute_cleanup(self.home, self.cache, preview)
        self.assertTrue((target / "important").exists())
        self.assertTrue(old.exists())

    def test_symlink_target_never_deleted(self):
        outside = self.home / "important-other-data"
        outside.mkdir(parents=True)
        (outside / "keep").write_text("safe")
        link = self.apps / "compatdata/3456"
        link.parent.mkdir(parents=True)
        link.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(CleanupError):
            preview_cleanup(self.home, self.cache, self.library, "3456", "prefix")
        self.assertTrue((outside / "keep").exists())

    def test_running_game_is_blocked(self):
        (self.apps / "compatdata/3456").mkdir(parents=True)
        with patch("cleanup._running_app_or_prefix", return_value=True):
            with self.assertRaisesRegex(CleanupError, "running"):
                preview_cleanup(self.home, self.cache, self.library, "3456", "prefix")


if __name__ == "__main__":
    unittest.main()
