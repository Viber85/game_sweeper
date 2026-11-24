"""Verify we compile ONLY explicitly tagged saved-game files."""
import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "game_saves_build", Path(__file__).resolve().parent.parent / "tools/build_save_rules.py")
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class SaveRulesTests(unittest.TestCase):
    def test_explicit_save_tags_only(self):
        data = {
            "Test Game": {
                "files": {
                    "<winAppData>/TestCo/Saves": {"tags": ["save"]},
                    "<winAppData>/TestCo/Config": {"tags": ["config"]},
                    "<root>/Steam/Install": {"tags": ["save"]},
                    "<winLocalAppData>/TestCo/Caches": {},
                    "<home>/save.dat": {"tags": ["save"]},
                    "<home>/../secrets": {"tags": ["save"]},
                    "<winDocuments>/TestCo/Settings": {"tags": ["other"]},
                },
                "steam": {"id": 123456},
            },
            "Other": {
                "files": {
                    "<winLocalAppData>/Game/Save": {"tags": ["save"]},
                }
            }
        }
        compiled = builder.compile_manifest(data, enforce_minimum=False)
        self.assertEqual(
            compiled["by_steam_id"]["123456"],
            ["<winAppData>/TestCo/Saves", "<home>/save.dat"]
        )
        self.assertNotIn("<root>/Steam/Install", compiled["by_steam_id"]["123456"])
        self.assertEqual(len(compiled["by_name"]), 2)

    def test_linux_only_rule_excluded_for_proton(self):
        self.assertFalse(builder.allowed_path(
            "<home>/.local/games/save",
            {"tags": ["save"], "when": [{"os": "linux"}]}
        ))
        self.assertTrue(builder.allowed_path(
            "<winDocuments>/Saved Games/game",
            {"tags": ["save"], "when": [{"os": "windows"}]}
        ))


if __name__ == "__main__":
    unittest.main()
