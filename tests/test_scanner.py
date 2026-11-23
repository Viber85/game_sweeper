"""Run with python -m unittest discover -s tests -v."""
import tempfile
import unittest
from pathlib import Path

from scanner import discover_libraries, scan


class ScannerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name) / "home"
        self.steam = self.home / ".local/share/Steam"
        self.apps = self.steam / "steamapps"
        self.apps.mkdir(parents=True)
        self.cache = self.home / "gamesweep/known_titles.json"

    def test_installed_and_candidate_and_cache(self):
        (self.apps / "appmanifest_1091500.acf").write_text(
            '"AppState" { "appid" "1091500" "name" "Cyberpunk 2077" }')
        prefix = self.apps / "compatdata/1091500/pfx"
        prefix.mkdir(parents=True)
        (prefix / "dummy").write_bytes(b"x" * 15)
        other = self.apps / "shadercache/123456"
        other.mkdir(parents=True)
        (other / "cache").write_bytes(b"y" * 37)
        result = scan(self.home, self.cache)
        self.assertEqual(len(result["disks"]), 1)
        self.assertEqual(result["disks"][0]["library"], str(self.steam))
        self.assertGreater(result["disks"][0]["total"], 0)
        by_id = {row["id"]: row for row in result["entries"]}
        self.assertEqual(by_id["1091500"]["status"], "installed")
        self.assertEqual(by_id["1091500"]["name"], "Cyberpunk 2077")
        self.assertEqual(by_id["1091500"]["bytes"], 15)
        self.assertEqual(by_id["123456"]["status"], "candidate")
        self.assertEqual(by_id["123456"]["bytes"], 37)
        (self.apps / "appmanifest_1091500.acf").unlink()
        new = scan(self.home, self.cache)
        self.assertEqual(
            next(x for x in new["entries"] if x["id"] == "1091500")["name"],
            "Cyberpunk 2077")

    def test_external_library_unavailable_prevents_candidate(self):
        (self.apps / "libraryfolders.vdf").write_text(
            '"libraryfolders" { "1" { "path" "/missing/extra-library" } }')
        (self.apps / "compatdata/3000").mkdir(parents=True)
        result = scan(self.home, self.cache)
        self.assertEqual(result["entries"][0]["status"], "review")
        self.assertTrue(result["missing_libraries"])

    def test_do_not_follow_symlink(self):
        outside = Path(self.tmp.name) / "outside"
        outside.mkdir()
        (outside / "large").write_bytes(b"a" * 1000)
        folder = self.apps / "compatdata/1234"
        folder.mkdir(parents=True)
        (folder / "link").symlink_to(outside, target_is_directory=True)
        result = scan(self.home, self.cache)
        self.assertEqual(result["entries"][0]["bytes"], 0)

    def test_nonsteam_like_id_is_review(self):
        (self.apps / "compatdata/3456789012").mkdir(parents=True)
        result = scan(self.home, self.cache)
        self.assertEqual(result["entries"][0]["status"], "review")

    def test_missing_steam_returns_empty(self):
        libraries, missing = discover_libraries(self.home / "other")
        self.assertEqual(libraries, [])
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
