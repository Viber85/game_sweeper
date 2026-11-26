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
            release("0.7.0"), release("0.8.2"), release("0.8.1")
        ]):
            data = updater._github_update()
        self.assertTrue(data["available"])
        self.assertEqual(data["version"], "v0.8.2")
        self.assertEqual(data["sha256"], "a" * 64)

    def test_same_version_is_not_an_update(self):
        with patch.object(updater, "_download_json", return_value=[
            release("0.8.0"), release("0.3.1")
        ]):
            data = updater._github_update()
        self.assertFalse(data["available"])

    def test_wrong_asset_or_draft_is_rejected(self):
        with patch.object(updater, "_download_json", return_value=[
            release("0.8.5", filename="Source-code.zip"),
            release("0.8.6", draft=True)
        ]):
            data = updater._github_update()
        self.assertFalse(data["available"])

    def test_loader_bridge_is_not_plugin_rpc(self):
        """Guard against regressing to @decky/api.call('utilities/install_plugin')."""
        from pathlib import Path
        source = (Path(__file__).resolve().parent.parent / "src/api.ts").read_text()
        self.assertIn('bridge.callable("utilities/install_plugin")', source)
        self.assertNotIn('import { callable, call } from "@decky/api"', source)



class TLSTests(unittest.TestCase):
    def test_uses_packaged_mozilla_roots_when_present(self):
        """Decky may not find host CA certificates; bundle must be consulted."""
        import tempfile
        from pathlib import Path
        from unittest.mock import sentinel
        with tempfile.TemporaryDirectory() as directory:
            ca_file = Path(directory) / "cacert.pem"
            ca_file.write_bytes(b"fake test bundle")
            with patch.object(updater, "TRUST_BUNDLE", ca_file):
                with patch.object(updater.ssl, "create_default_context", return_value=sentinel.ssl_context) as maker:
                    self.assertIs(updater._https_context(), sentinel.ssl_context)
                    maker.assert_called_once_with(cafile=str(ca_file))

    def test_absent_bundle_uses_verified_system_context(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import sentinel
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "not-here.pem"
            with patch.object(updater, "TRUST_BUNDLE", missing):
                with patch.object(updater.ssl, "create_default_context", return_value=sentinel.ssl_context) as maker:
                    self.assertIs(updater._https_context(), sentinel.ssl_context)
                    maker.assert_called_once_with()

    def test_download_uses_tls_context(self):
        from unittest.mock import sentinel
        class FakeResponse:
            status = 200
            def __enter__(self):
                return self
            def __exit__(self, *_):
                return None
            def read(self, size):
                return b'{"success":true}'
        with patch.object(updater, "_https_context", return_value=sentinel.ssl_context):
            with patch.object(updater, "urlopen", return_value=FakeResponse()) as opener:
                self.assertEqual(updater._download_json("https://api.github.com/example"), {"success": True})
                self.assertEqual(opener.call_args.kwargs["context"], sentinel.ssl_context)
                self.assertEqual(opener.call_args.kwargs["timeout"], 8)

if __name__ == "__main__":
    unittest.main()
