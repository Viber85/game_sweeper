"""Installed Steam/Non-Steam data cleanup is opt-in and always revalidated.

Only temporary test directories are touched; no actual Steam libraries.
"""
import asyncio
import sys
import tempfile
import types
import unittest
from pathlib import Path

sys.modules.setdefault("decky", types.ModuleType("decky"))

from cleanup import CleanupError, execute_cleanup, preview_cleanup
from main import Plugin
from scanner import scan
from test_shortcuts import shortcut_file


class InstalledDataTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.apps = self.home / ".local/share/Steam/steamapps"
        self.apps.mkdir(parents=True)
        self.library = str(self.apps.parent)
        self.cache = self.home / "metadata/known_titles.json"

    def steam_game(self, appid="1091500"):
        (self.apps / ("appmanifest_" + appid + ".acf")).write_text(
            '"AppState" { "appid" "' + appid + '" "name" "Cyberpunk 2077" }'
        )
        prefix = self.apps / "compatdata" / appid
        prefix.mkdir(parents=True)
        (prefix / "savegame").write_text("valuable")
        return prefix

    def test_installed_steam_requires_override(self):
        prefix = self.steam_game()
        row = scan(self.home, self.cache)["entries"][0]
        self.assertEqual(row["game_type"], "steam")
        self.assertEqual(row["type_source"], "manifest")
        self.assertEqual(row["status"], "installed")
        with self.assertRaisesRegex(CleanupError, "authorization"):
            preview_cleanup(self.home, self.cache, self.library, "1091500", "prefix")
        self.assertTrue(prefix.exists())

    def test_installed_game_can_delete_one_directory_after_override(self):
        prefix = self.steam_game()
        shader = self.apps / "shadercache/1091500"
        shader.mkdir(parents=True)
        (shader / "cache").write_bytes(b"shader")
        preview = preview_cleanup(self.home, self.cache, self.library, "1091500", "shader", True)
        self.assertTrue(preview["allow_installed"])
        self.assertEqual(preview["status"], "installed")
        result = execute_cleanup(self.home, self.cache, preview)
        self.assertTrue(result["success"])
        self.assertFalse(shader.exists())
        self.assertEqual((prefix / "savegame").read_text(), "valuable")

    def test_nonsteam_source_from_shortcut(self):
        config = self.home / ".local/share/Steam/userdata/123/config"
        config.mkdir(parents=True)
        (config / "shortcuts.vdf").write_bytes(shortcut_file(3821140444, "Epic Game"))
        prefix = self.apps / "compatdata/3821140444"
        prefix.mkdir(parents=True)
        row = scan(self.home, self.cache)["entries"][0]
        self.assertEqual(row["game_type"], "non_steam")
        self.assertEqual(row["type_source"], "shortcut")
        self.assertEqual(row["status"], "installed")
        with self.assertRaisesRegex(CleanupError, "authorization"):
            preview_cleanup(self.home, self.cache, self.library, "3821140444", "prefix")
        self.assertTrue(prefix.exists())

    def test_source_type_retained_after_manifest_removed(self):
        prefix = self.steam_game()
        scan(self.home, self.cache)
        (self.apps / "appmanifest_1091500.acf").unlink()
        row = scan(self.home, self.cache)["entries"][0]
        self.assertEqual(row["game_type"], "steam")
        self.assertEqual(row["type_source"], "history")
        self.assertEqual(row["name"], "Cyberpunk 2077")
        self.assertTrue(prefix.exists())

    def test_numeric_size_does_not_guess_nonsteam(self):
        (self.apps / "shadercache/3821140444").mkdir(parents=True)
        row = scan(self.home, self.cache)["entries"][0]
        self.assertEqual(row["game_type"], "unknown")
        self.assertEqual(row["type_source"], "unknown")

    def test_status_change_between_preview_and_delete_blocks(self):
        prefix = self.steam_game()
        preview = preview_cleanup(self.home, self.cache, self.library, "1091500", "prefix", True)
        (self.apps / "appmanifest_1091500.acf").unlink()
        with self.assertRaisesRegex(CleanupError, "changed since confirmation"):
            execute_cleanup(self.home, self.cache, preview)
        self.assertTrue(prefix.exists())

    def test_backend_confirmation_token_rejects_regular_code_for_installed(self):
        prefix = self.steam_game()
        plugin = Plugin()
        plugin.home = self.home
        plugin.cache_path = self.cache
        plugin.lock = asyncio.Lock()
        plugin.pending_deletions = {}

        async def run_case():
            request = await plugin.prepare_cleanup(self.library, "1091500", "prefix", True)
            self.assertTrue(request["ok"])
            self.assertEqual(request["game_type"], "steam")
            wrong = await plugin.delete_storage(request["token"], "PERMANENT_DELETE")
            self.assertFalse(wrong["ok"])
            self.assertIn("installed-game", wrong["error"])
            self.assertTrue(prefix.exists())

        asyncio.run(run_case())

    def test_backend_installed_shaders_can_delete_with_strong_code(self):
        self.steam_game()
        shader = self.apps / "shadercache/1091500"
        shader.mkdir(parents=True)
        (shader / "x").write_text("cache")
        plugin = Plugin()
        plugin.home = self.home
        plugin.cache_path = self.cache
        plugin.lock = asyncio.Lock()
        plugin.pending_deletions = {}

        async def run_case():
            request = await plugin.prepare_cleanup(self.library, "1091500", "shader", True)
            self.assertTrue(request["ok"])
            outcome = await plugin.delete_storage(
                request["token"], "PERMANENT_DELETE_INSTALLED"
            )
            self.assertTrue(outcome["ok"])
            self.assertFalse(shader.exists())

        asyncio.run(run_case())


if __name__ == "__main__":
    unittest.main()
