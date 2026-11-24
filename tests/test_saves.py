"""Save-only backup and restore tests: disposable fake Steam libraries only."""
import asyncio
import json
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

sys.modules.setdefault("decky", types.ModuleType("decky"))
sys.modules["decky"].logger = types.SimpleNamespace(
    info=lambda *args, **kwargs: None,
    warning=lambda *args, **kwargs: None,
)

import saves
from main import Plugin


class SavesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.steamapps = self.home / ".local/share/Steam/steamapps"
        self.steamapps.mkdir(parents=True)
        self.library = str(self.steamapps.parent)
        self.cache = self.home / "settings/known_titles.json"
        self.appid = "123456"
        self.prefix = self.steamapps / "compatdata" / self.appid
        self.save = self.prefix / "pfx/drive_c/users/steamuser/AppData/Roaming/TestCo/TestGame/saves/slot1.sav"
        self.config = self.prefix / "pfx/drive_c/users/steamuser/AppData/Roaming/TestCo/TestGame/config.ini"
        self.save.parent.mkdir(parents=True)
        self.save.write_bytes(b"important-save-12345")
        self.config.write_text("do-not-copy")
        (self.steamapps / ("appmanifest_" + self.appid + ".acf")).write_text(
            '"AppState" { "appid" "' + self.appid + '" "name" "Test Game" }'
        )
        self.rules = self.home / "save_rules.json"
        self.rules.write_text(json.dumps({
            "schema": 1,
            "by_steam_id": {
                self.appid: ["<winAppData>/TestCo/TestGame/saves"]
            },
            "by_name": {"test game": ["<winAppData>/TestCo/TestGame/saves"]}
        }))

    def preview(self):
        return saves.preview_saves(self.home, self.cache, self.library, self.appid, self.rules)

    def create(self):
        return saves.create_backup(self.home, self.cache, self.library, self.appid, self.rules)

    def test_preview_only_save_folder(self):
        info = self.preview()
        self.assertTrue(info["supported"])
        self.assertEqual(info["count"], 1)
        self.assertEqual(info["bytes"], len(self.save.read_bytes()))
        self.assertIn("slot1.sav", info["sample"][0])

    def test_backup_does_not_copy_other_appdata_or_prefix(self):
        backup = self.create()
        self.assertEqual(backup["count"], 1)
        self.assertEqual(backup["appid"], self.appid)
        storage = saves.backup_root(self.home) / backup["id"]
        self.assertEqual(len(list((storage / "files").rglob("*sav"))), 1)
        self.assertFalse(any(p.name == "config.ini" for p in storage.rglob("*")))
        self.assertTrue(self.config.exists())
        self.assertEqual(len(saves.list_backups(self.home)), 1)

    def test_restore_after_prefix_deleted(self):
        original = self.save.read_bytes()
        saved = self.create()
        shutil.rmtree(self.prefix)
        detail = saves.preview_restore(self.home, self.cache, saved["id"])
        self.assertEqual(detail["conflicts"], 0)
        done = saves.restore_backup(self.home, self.cache, saved["id"])
        self.assertEqual(done["count"], 1)
        self.assertEqual(self.save.read_bytes(), original)

    def test_restore_reports_existing_conflicts(self):
        saved = self.create()
        self.save.write_bytes(b"newer-progress")
        detail = saves.preview_restore(self.home, self.cache, saved["id"])
        self.assertEqual(detail["conflicts"], 1)
        self.assertEqual(self.save.read_bytes(), b"newer-progress")
        saves.restore_backup(self.home, self.cache, saved["id"])
        self.assertEqual(self.save.read_bytes(), b"important-save-12345")

    def test_modified_archive_blocks_restore_before_writing(self):
        saved = self.create()
        archived = saves.backup_root(self.home) / saved["id"] / "files" / self.save.relative_to(self.prefix)
        archived.write_bytes(b"corrupted-but-not-restored")
        self.save.write_bytes(b"current-progress")
        with self.assertRaisesRegex(saves.SaveError, "checksum|modified"):
            saves.restore_backup(self.home, self.cache, saved["id"])
        self.assertEqual(self.save.read_bytes(), b"current-progress")

    def test_no_rules_never_creates_empty_backup(self):
        self.rules.write_text(json.dumps({"schema": 1, "by_steam_id": {}, "by_name": {}}))
        preview = self.preview()
        self.assertFalse(preview["supported"])
        with self.assertRaisesRegex(saves.SaveError, "No verified"):
            self.create()

    def test_running_game_blocks_backup(self):
        with patch("saves._running_app_or_prefix", return_value=True):
            with self.assertRaisesRegex(saves.SaveError, "Close the game"):
                self.create()

    def test_symlinked_save_outside_prefix_rejected(self):
        original = self.save.read_bytes()
        external = self.home / "not-a-save"
        external.write_bytes(b"secret")
        self.save.unlink()
        self.save.symlink_to(external)
        with self.assertRaises(saves.SaveError):
            self.preview()
        self.assertEqual(external.read_bytes(), b"secret")

    def test_invalid_restore_id_cannot_read_outside_backup_dir(self):
        with self.assertRaisesRegex(saves.SaveError, "identifier"):
            saves.preview_restore(self.home, self.cache, "../somewhere")

    def test_restore_rejects_symlink_in_destination(self):
        backed = self.create()
        folder = self.save.parent
        shutil.rmtree(folder)
        other = self.home / "another-dir"
        other.mkdir()
        (other / "slot1.sav").write_bytes(b"keep")
        folder.symlink_to(other, target_is_directory=True)
        with self.assertRaises(saves.SaveError):
            saves.preview_restore(self.home, self.cache, backed["id"])
        self.assertEqual((other / "slot1.sav").read_bytes(), b"keep")

    def test_backend_preview_and_confirm_token(self):
        plugin = Plugin()
        plugin.home = self.home
        plugin.cache_path = self.cache
        plugin.lock = asyncio.Lock()
        plugin.pending_restores = {}
        async def cycle():
            with patch.object(saves, "RULES_FILE", self.rules):
                # Functions' default rules_file parameters are bound at definition
                # time: explicitly route test fixture through the callable.
                with patch("main.preview_saves",
                           side_effect=lambda h,c,l,a: saves.preview_saves(h,c,l,a,self.rules)):
                    preview = await plugin.preview_save_backup(self.library, self.appid)
                self.assertTrue(preview["ok"])
                self.assertEqual(preview["count"], 1)
            saved = self.create()
            request = await plugin.prepare_save_restore(saved["id"])
            self.assertTrue(request["ok"])
            wrong = await plugin.restore_save_backup(request["token"], "BAD")
            self.assertFalse(wrong["ok"])
            self.save.write_bytes(b"latest")
            finished = await plugin.restore_save_backup(request["token"], "RESTORE_OVERWRITE")
            self.assertTrue(finished["ok"])
            self.assertEqual(self.save.read_bytes(), b"important-save-12345")
            repeat = await plugin.restore_save_backup(request["token"], "RESTORE_OVERWRITE")
            self.assertFalse(repeat["ok"])
        asyncio.run(cycle())


if __name__ == "__main__":
    unittest.main()
