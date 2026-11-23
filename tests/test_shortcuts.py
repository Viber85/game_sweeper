"""Binary Steam shortcuts.vdf parser and name-recovery tests."""
import struct
import tempfile
import unittest
from pathlib import Path

from scanner import scan
from shortcuts import parse_shortcuts, read_shortcuts


def shortcut_file(appid: int, title: str) -> bytes:
    def word(name: str) -> bytes:
        return name.encode("utf-8") + b"\x00"

    def field_str(key: str, value: str) -> bytes:
        return b"\x01" + word(key) + word(value)

    def field_i32(key: str, unsigned: int) -> bytes:
        signed = unsigned if unsigned < 2**31 else unsigned - 2**32
        return b"\x02" + word(key) + struct.pack("<i", signed)

    return (
        b"\x00" + word("shortcuts")
        + b"\x00" + word("0")
        + field_i32("appid", appid)
        + field_str("AppName", title)
        + field_str("Exe", '"/home/deck/Games/example.exe"')
        + b"\x08" + b"\x08"
    )


class ShortcutsTests(unittest.TestCase):
    def test_signed_i32_becomes_unsigned_appid(self):
        raw = shortcut_file(3821140444, "My Non-Steam Game")
        self.assertEqual(parse_shortcuts(raw)["3821140444"], "My Non-Steam Game")

    def test_corrupt_file_does_not_crash(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "shortcuts.vdf"
            path.write_bytes(b"\x00shortcuts\x00\x01garbled")
            self.assertEqual(read_shortcuts(path), {})

    def test_current_shortcut_marks_installed(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            apps = home / ".local/share/Steam/steamapps"
            config = home / ".local/share/Steam/userdata/123/config"
            apps.mkdir(parents=True)
            config.mkdir(parents=True)
            (apps / "compatdata/3821140444").mkdir(parents=True)
            (config / "shortcuts.vdf").write_bytes(shortcut_file(3821140444, "Game A"))
            data = scan(home, home / "cache.json")
            item = data["entries"][0]
            self.assertEqual(item["name"], "Game A")
            self.assertEqual(item["status"], "installed")
            self.assertEqual(item["name_source"], "shortcut")

    def test_backup_restores_name_but_does_not_allow_auto_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            apps = home / ".local/share/Steam/steamapps"
            config = home / ".local/share/Steam/userdata/123/config"
            apps.mkdir(parents=True)
            config.mkdir(parents=True)
            (apps / "shadercache/3821140444").mkdir(parents=True)
            (config / "shortcuts.vdf.bak").write_bytes(shortcut_file(3821140444, "Old Game"))
            data = scan(home, home / "cache.json")
            item = data["entries"][0]
            self.assertEqual(item["name"], "Old Game")
            self.assertEqual(item["status"], "review")
            self.assertEqual(item["name_source"], "backup")


if __name__ == "__main__":
    unittest.main()
