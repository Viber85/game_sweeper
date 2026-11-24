"""Save location chooser, manual detection and multi-location restore tests."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import backup_locations
import manual_saves
import saves


class LocationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.apps = self.home / ".local/share/Steam/steamapps"
        self.apps.mkdir(parents=True)
        self.library = str(self.apps.parent)
        self.cache = self.home / "settings/known_titles.json"
        self.appid = "777321"
        self.prefix = self.apps / "compatdata" / self.appid
        self.save = self.prefix / "pfx/drive_c/users/steamuser/AppData/Roaming/MyGame/saves/slot1.sav"
        self.config = self.prefix / "pfx/drive_c/users/steamuser/AppData/Roaming/MyGame/config.ini"
        self.save.parent.mkdir(parents=True)
        self.save.write_bytes(b"important-progress")
        self.config.write_bytes(b"not-in-save-folder")
        (self.apps / ("appmanifest_" + self.appid + ".acf")).write_text(
            '"AppState" { "appid" "' + self.appid + '" "name" "Example Game" }'
        )
        self.rules = self.home / "rules.json"
        self.rules.write_text(json.dumps({
            "schema": 1, "by_steam_id": {}, "by_name": {}
        }))

    def test_select_destination_and_back_up_only_save_files(self):
        docs = self.home / "Documents"
        docs.mkdir()
        info = backup_locations.choose_location(self.home, self.cache, str(docs))
        self.assertTrue(info["ok"])
        self.assertEqual(info["base"], str(docs))
        self.assertEqual(info["folder"], str(docs / "GameSweep/save-backups"))

        relative = "users/steamuser/AppData/Roaming/MyGame/saves"
        manual_saves.select_manual_save_folder(
            self.cache, self.library, self.appid, self.prefix, relative
        )
        info = saves.preview_saves(self.home, self.cache, self.library,
                                   self.appid, self.rules)
        self.assertEqual(info["count"], 1)
        self.assertTrue(info["manual"])
        snap = saves.create_backup(self.home, self.cache, self.library,
                                   self.appid, self.rules)
        backup_path = docs / "GameSweep/save-backups" / snap["id"]
        self.assertTrue((backup_path / "manifest.json").exists())
        self.assertEqual(len(list((backup_path / "files").rglob("*.sav"))), 1)
        self.assertFalse(any(p.name == "config.ini" for p in backup_path.rglob("*")))

    def test_restore_after_location_changed_still_discovers_old_backup(self):
        first = self.home / "Documents"
        second = self.home / "Downloads"
        first.mkdir()
        second.mkdir()
        relative = "users/steamuser/AppData/Roaming/MyGame/saves"
        manual_saves.select_manual_save_folder(
            self.cache, self.library, self.appid, self.prefix, relative
        )
        backup_locations.choose_location(self.home, self.cache, str(first))
        snapshot = saves.create_backup(self.home, self.cache, self.library,
                                       self.appid, self.rules)
        backup_locations.choose_location(self.home, self.cache, str(second))
        found = saves.list_backups(self.home, cache_file=self.cache)
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["id"], snapshot["id"])
        self.assertEqual(found[0]["backup_folder"], str(first / "GameSweep/save-backups"))
        self.save.write_bytes(b"newer-progress")
        preview = saves.preview_restore(self.home, self.cache, snapshot["id"])
        self.assertEqual(preview["conflicts"], 1)
        saves.restore_backup(self.home, self.cache, snapshot["id"])
        self.assertEqual(self.save.read_bytes(), b"important-progress")

    def test_backup_browser_shows_existing_folders(self):
        (self.home / "Documents").mkdir()
        top = backup_locations.browser(self.home, "")
        self.assertTrue(any(row["name"] == "Home" for row in top["folders"]))
        page = backup_locations.browser(self.home, str(self.home))
        self.assertTrue(any(row["name"] == "Documents" for row in page["folders"]))
        self.assertTrue(page["selectable"])

    def test_reject_destination_inside_steam_storage(self):
        with self.assertRaisesRegex(backup_locations.FolderError, "Steam"):
            backup_locations.choose_location(self.home, self.cache, str(self.apps))
        self.assertFalse(backup_locations.locations_file(self.cache).exists())

    def test_reject_outside_home_and_symlink(self):
        with tempfile.TemporaryDirectory() as external:
            with self.assertRaisesRegex(backup_locations.FolderError, "under Home"):
                backup_locations.choose_location(self.home, self.cache, external)
        docs = self.home / "Documents"
        docs.mkdir()
        shortcut = self.home / "link-to-documents"
        shortcut.symlink_to(docs, target_is_directory=True)
        with self.assertRaisesRegex(backup_locations.FolderError, "Linked"):
            backup_locations.choose_location(self.home, self.cache, str(shortcut))

    def test_select_specific_manual_folder_not_appdata(self):
        browser = manual_saves.browse_game_save_folders(
            self.prefix, "users/steamuser/AppData/Roaming/MyGame/saves"
        )
        self.assertTrue(browser["selectable"])
        self.assertEqual(browser["count"], 1)
        self.assertEqual(browser["parent"], "users/steamuser/AppData/Roaming/MyGame")
        with self.assertRaisesRegex(manual_saves.ManualSaveError, "specific"):
            manual_saves.select_manual_save_folder(
                self.cache, self.library, self.appid, self.prefix,
                "users/steamuser/AppData"
            )
        with self.assertRaisesRegex(manual_saves.ManualSaveError, "(?i)system"):
            manual_saves.select_manual_save_folder(
                self.cache, self.library, self.appid, self.prefix,
                "Windows/System32"
            )

    def test_manual_folder_rejects_symlink_file(self):
        external = self.home / "secret"
        external.write_bytes(b"secret")
        self.save.unlink()
        self.save.symlink_to(external)
        with self.assertRaisesRegex(manual_saves.ManualSaveError, "symbolic-link"):
            manual_saves.select_manual_save_folder(
                self.cache, self.library, self.appid, self.prefix,
                "users/steamuser/AppData/Roaming/MyGame/saves"
            )

    def test_bad_rule_explains_why_no_saves_found(self):
        result = saves.preview_saves(self.home, self.cache, self.library,
                                     self.appid, self.rules)
        self.assertFalse(result["supported"])
        self.assertIn("No save-location rule", result["message"])
        self.assertIn("manually", result["message"])

    def test_manual_override_resets_to_auto(self):
        relative = "users/steamuser/AppData/Roaming/MyGame/saves"
        manual_saves.select_manual_save_folder(
            self.cache, self.library, self.appid, self.prefix, relative
        )
        self.assertEqual(manual_saves.chosen_folder(self.cache, self.library, self.appid), relative)
        manual_saves.clear_manual_save_folder(self.cache, self.library, self.appid)
        self.assertEqual(manual_saves.chosen_folder(self.cache, self.library, self.appid), "")


if __name__ == "__main__":
    unittest.main()
