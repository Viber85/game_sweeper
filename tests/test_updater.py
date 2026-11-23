"""Updater contract tests. Run with python -m unittest discover -s tests -v."""
import importlib
import sys
import types
import unittest
from unittest.mock import patch

# Decky's Python module is provided by Loader on-device, not in CI.
sys.modules.setdefault("decky", types.ModuleType("decky"))
updater = importlib.import_module("main")


def release(version, filename=None, draft=False):
    tag = "v" + version
    return {
        "tag_name": tag,
        "draft": draft,
        "prerelease": True,
        "assets": [{
            "name": filename if filename is not None else "GameSweep-" + tag + ".zip",
            "browser_download_url": (
                "https://github.com/Viber85/game_sweeper/releases/download/" + tag +
                "/GameSweep-" + tag + ".zip"
            ),
            "digest": "sha256:" + "a" * 64,
        }],
    }


class UpdaterTests(unittest.TestCase):
    def test_newer_release_is_detected(self):
        with patch.object(updater, "_download_json", return_value=[
            release("0.2.1"), release("0.3.2"), release("0.3.1")
        ]):
            data = updater._github_update()
        self.assertTrue(data["available"])
        self.assertEqual(data["version"], "v0.3.2")
        self.assertEqual(data["sha256"], "a" * 64)

    def test_same_version_is_not_an_update(self):
        with patch.object(updater, "_download_json", return_value=[
            release("0.3.0"), release("0.2.1")
        ]):
            data = updater._github_update()
        self.assertFalse(data["available"])

    def test_wrong_asset_or_draft_is_rejected(self):
        with patch.object(updater, "_download_json", return_value=[
            release("0.3.5", filename="Source-code.zip"),
            release("0.3.6", draft=True)
        ]):
            data = updater._github_update()
        self.assertFalse(data["available"])

    def test_loader_bridge_is_not_plugin_rpc(self):
        """Guard against regressing to @decky/api.call('utilities/install_plugin')."""
        from pathlib import Path
        source = (Path(__file__).resolve().parent.parent / "src/api.ts").read_text()
        self.assertIn('bridge.callable("utilities/install_plugin")', source)
        self.assertNotIn('import { callable, call } from "@decky/api"', source)


if __name__ == "__main__":
    unittest.main()
