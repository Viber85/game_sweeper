"""Combined compatdata + shader cache cleanup. All filesystem changes temporary."""
import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import sys
import types

sys.modules.setdefault("decky", types.ModuleType("decky"))
sys.modules["decky"].logger = types.SimpleNamespace(
    info=lambda *args, **kwargs: None,
    warning=lambda *args, **kwargs: None,
)

from cleanup import (
    CleanupError, execute_all_cleanup, preview_all_cleanup,
)
from main import Plugin


class AllGameDataCleanupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.apps = self.home / ".local/share/Steam/steamapps"
        self.apps.mkdir(parents=True)
        self.library = str(self.apps.parent)
        self.cache = self.home / "settings/known_titles.json"

    def fixture(self, installed=False, appid="4567"):
        prefix = self.apps / "compatdata" / appid
        shader = self.apps / "shadercache" / appid
        prefix.mkdir(parents=True)
        shader.mkdir(parents=True)
        (prefix / "save").write_bytes(b"s" * 33)
        (shader / "cache").write_bytes(b"c" * 22)
        if installed:
            (self.apps / ("appmanifest_" + appid + ".acf")).write_text(
                '"AppState" { "appid" "' + appid + '" "name" "Test Game" }'
            )
        return prefix, shader

    def test_full_cleanup_removes_exactly_two_folders(self):
        prefix, shader = self.fixture()
        other = self.apps / "compatdata/9999"
        other.mkdir()
        (other / "keep").write_text("safe")
        plan = preview_all_cleanup(self.home, self.cache, self.library, "4567")
        self.assertEqual(plan["bytes"], 55)
        self.assertEqual({t["kind"] for t in plan["targets"]}, {"prefix", "shader"})
        result = execute_all_cleanup(self.home, self.cache, plan)
        self.assertEqual(result["removed_kinds"], ["prefix", "shader"])
        self.assertFalse(prefix.exists())
        self.assertFalse(shader.exists())
        self.assertEqual((other / "keep").read_text(), "safe")

    def test_installed_game_requires_override(self):
        prefix, shader = self.fixture(installed=True)
        with self.assertRaisesRegex(CleanupError, "authorization"):
            preview_all_cleanup(self.home, self.cache, self.library, "4567")
        self.assertTrue(prefix.exists())
        self.assertTrue(shader.exists())

    def test_installed_game_override_does_not_uninstall_game(self):
        prefix, shader = self.fixture(installed=True)
        appmanifest = self.apps / "appmanifest_4567.acf"
        plan = preview_all_cleanup(
            self.home, self.cache, self.library, "4567", allow_installed=True
        )
        self.assertEqual(plan["status"], "installed")
        execute_all_cleanup(self.home, self.cache, plan)
        self.assertTrue(appmanifest.exists())
        self.assertFalse(prefix.exists())
        self.assertFalse(shader.exists())

    def test_inode_swap_blocks_both_deletions(self):
        prefix, shader = self.fixture()
        plan = preview_all_cleanup(self.home, self.cache, self.library, "4567")
        shader.rename(shader.with_name("old-shader"))
        shader.mkdir()
        (shader / "keep").write_text("important")
        with self.assertRaisesRegex(CleanupError, "changed"):
            execute_all_cleanup(self.home, self.cache, plan)
        self.assertTrue((prefix / "save").exists())
        self.assertTrue((shader / "keep").exists())

    def test_game_installed_after_preview_blocks_both(self):
        prefix, shader = self.fixture()
        plan = preview_all_cleanup(self.home, self.cache, self.library, "4567")
        (self.apps / "appmanifest_4567.acf").write_text(
            '"AppState" { "appid" "4567" "name" "Game" }'
        )
        with self.assertRaisesRegex(CleanupError, "authorization"):
            execute_all_cleanup(self.home, self.cache, plan)
        self.assertTrue(prefix.exists())
        self.assertTrue(shader.exists())

    def test_running_game_blocks_preview(self):
        self.fixture()
        with patch("cleanup._running_app_or_prefix", return_value=True):
            with self.assertRaisesRegex(CleanupError, "running"):
                preview_all_cleanup(self.home, self.cache, self.library, "4567")

    def test_symlink_blocks_combined_cleanup(self):
        _, shader = self.fixture()
        external = self.home / "very-important"
        external.mkdir()
        (external / "keep").write_text("safe")
        shader.rename(shader.with_name("moved-cache"))
        shader.symlink_to(external, target_is_directory=True)
        with self.assertRaises(CleanupError):
            preview_all_cleanup(self.home, self.cache, self.library, "4567")
        self.assertEqual((external / "keep").read_text(), "safe")

    def test_offline_library_blocks_preview(self):
        self.fixture()
        (self.apps / "libraryfolders.vdf").write_text(
            '"libraryfolders" { "1" { "path" "/unavailable/microSD" } }'
        )
        with self.assertRaisesRegex(CleanupError, "offline"):
            preview_all_cleanup(self.home, self.cache, self.library, "4567")

    def test_partial_failure_discloses_what_was_removed(self):
        prefix, shader = self.fixture()
        plan = preview_all_cleanup(self.home, self.cache, self.library, "4567")
        from cleanup import _delete_pinned_target
        def failing_second(target):
            if target["kind"] == "shader":
                raise CleanupError("simulated failure")
            _delete_pinned_target(target)
        with patch("cleanup._delete_pinned_target", side_effect=failing_second):
            with self.assertRaisesRegex(CleanupError, "incomplete: removed prefix"):
                execute_all_cleanup(self.home, self.cache, plan)
        self.assertFalse(prefix.exists())
        self.assertTrue(shader.exists())

    def test_backend_requires_one_use_token_and_installed_confirmation(self):
        prefix, shader = self.fixture(installed=True)
        plugin = Plugin()
        plugin.home = self.home
        plugin.cache_path = self.cache
        plugin.lock = asyncio.Lock()
        plugin.pending_deletions = {}

        async def check():
            plan = await plugin.prepare_cleanup(self.library, "4567", "all", True)
            self.assertTrue(plan["ok"], plan.get("error"))
            self.assertEqual(plan["kind"], "all")
            self.assertEqual(len(plan["targets"]), 2)
            rejected = await plugin.delete_storage(plan["token"], "PERMANENT_DELETE")
            self.assertFalse(rejected["ok"])
            self.assertTrue(prefix.exists())
            fresh = await plugin.prepare_cleanup(self.library, "4567", "all", True)
            outcome = await plugin.delete_storage(
                fresh["token"], "PERMANENT_DELETE_INSTALLED"
            )
            self.assertTrue(outcome["ok"], outcome.get("error"))
            self.assertEqual(outcome["kind"], "all")
            self.assertFalse(prefix.exists())
            self.assertFalse(shader.exists())
            repeated = await plugin.delete_storage(
                fresh["token"], "PERMANENT_DELETE_INSTALLED"
            )
            self.assertFalse(repeated["ok"])

        asyncio.run(check())


if __name__ == "__main__":
    unittest.main()
