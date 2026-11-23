"""Read-only discovery of Non-Steam shortcuts in Valve's binary VDF format.

No third-party parser required; never modifies Steam's shortcut files.
"""
from __future__ import annotations

import struct
import zlib
from pathlib import Path
from typing import Any

MAX_FILE_BYTES = 32 * 1024 * 1024
MAX_FIELDS = 100_000
MAX_DEPTH = 16


class ShortcutDecodeError(ValueError):
    pass


def decode_binary_vdf(raw: bytes) -> dict[str, Any]:
    """Decode common binary KeyValues types used by Steam shortcuts.vdf."""
    pos = 0
    fields_seen = 0

    def take(length: int) -> bytes:
        nonlocal pos
        if length < 0 or pos + length > len(raw):
            raise ShortcutDecodeError("Truncated binary VDF")
        chunk = raw[pos:pos + length]
        pos += length
        return chunk

    def cstring() -> str:
        nonlocal pos
        end = raw.find(b"\x00", pos, min(len(raw), pos + 65537))
        if end < 0:
            raise ShortcutDecodeError("Invalid or oversized VDF string")
        value = raw[pos:end].decode("utf-8", errors="replace")
        pos = end + 1
        return value

    def read_object(depth: int) -> dict[str, Any]:
        nonlocal fields_seen
        if depth > MAX_DEPTH:
            raise ShortcutDecodeError("Nested VDF exceeds depth limit")
        result: dict[str, Any] = {}
        while pos < len(raw):
            field_type = take(1)[0]
            if field_type == 8:  # end of object
                return result
            fields_seen += 1
            if fields_seen > MAX_FIELDS:
                raise ShortcutDecodeError("VDF contains too many fields")
            key = cstring()
            if field_type == 0:  # nested object
                value = read_object(depth + 1)
            elif field_type == 1:  # UTF-8 text
                value = cstring()
            elif field_type == 2:  # signed int32
                value = struct.unpack("<i", take(4))[0]
            elif field_type == 3:  # float32
                value = struct.unpack("<f", take(4))[0]
            elif field_type in (4, 6):  # pointer/color: 4 bytes
                value = take(4)
            elif field_type in (7, 9, 10):  # uint64/int64/compiled int64
                value = take(8)
            else:
                raise ShortcutDecodeError("Unknown VDF field type " + str(field_type))
            result[key] = value
        raise ShortcutDecodeError("Missing VDF object terminator")

    return read_object(0)


def _app_id(entry: dict[str, Any]) -> str | None:
    fields = {str(k).lower(): v for k, v in entry.items()}
    value = fields.get("appid")
    if isinstance(value, int):
        identifier = value & 0xFFFFFFFF
        if identifier != 0:
            return str(identifier)
    if isinstance(value, str) and value.strip().lstrip("-").isdigit():
        identifier = int(value) & 0xFFFFFFFF
        if identifier != 0:
            return str(identifier)

    # Legacy shortcut entries may not store an explicit AppID. Attempt the
    # historical CRC32 algorithm only when the AppID is absent.
    exe = fields.get("exe")
    name = fields.get("appname")
    if isinstance(exe, str) and isinstance(name, str) and exe and name:
        return str((zlib.crc32((exe + name).encode("utf-8")) | 0x80000000) & 0xFFFFFFFF)
    return None


def parse_shortcuts(raw: bytes) -> dict[str, str]:
    tree = decode_binary_vdf(raw)
    root = next((v for k, v in tree.items() if k.lower() == "shortcuts"), {})
    if not isinstance(root, dict):
        return {}
    mapping: dict[str, str] = {}
    for index, value in root.items():
        if not str(index).isdigit() or not isinstance(value, dict):
            continue
        fields = {str(k).lower(): v for k, v in value.items()}
        name = fields.get("appname")
        identifier = _app_id(value)
        if identifier and isinstance(name, str):
            clean = name.strip()
            if clean:
                mapping[identifier] = clean[:180]
    return mapping


def read_shortcuts(path: Path) -> dict[str, str]:
    try:
        if not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
            return {}
        return parse_shortcuts(path.read_bytes())
    except (OSError, ValueError, struct.error, RecursionError):
        return {}


def collect_shortcuts(steam_roots: list[Path]) -> tuple[dict[str, str], dict[str, str]]:
    """Collect active shortcut names and optional backup names across accounts.

    Backups may describe removed shortcuts: they identify a name but never
    prove that a game is installed or that its prefix is safe to delete.
    """
    current: dict[str, str] = {}
    historical: dict[str, str] = {}
    seen: set[str] = set()
    for steam_root in steam_roots:
        userdata = steam_root / "userdata"
        if not userdata.is_dir():
            continue
        try:
            profiles = list(userdata.iterdir())[:1000]
        except OSError:
            continue
        for profile in profiles:
            if not profile.is_dir() or not profile.name.isdigit():
                continue
            config = profile / "config"
            active = config / "shortcuts.vdf"
            key = str(active.resolve())
            if key in seen:
                continue
            seen.add(key)
            current.update(read_shortcuts(active))
            for backup_name in (
                "shortcuts.vdf.bak", "shortcuts.vdf.backup", "shortcuts.vdf.old"
            ):
                historical.update(read_shortcuts(config / backup_name))
    return current, historical
