"""Game Mode folder picker and persistent safe backup destinations.

The selected folder contains a GameSweep/save-backups subfolder. Existing
backups remain discoverable after changing destination or ejecting microSD.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from scanner import directory_bytes

HISTORY_LIMIT = 15
APP_DIR = Path("GameSweep/save-backups")
DEFAULT_BASE_REL = Path(".local/share")
RESTRICTED = {"steamapps", "compatdata", "shadercache", "decky", "decky-loader"}


class FolderError(ValueError):
    pass


def locations_file(cache_file: Path) -> Path:
    return cache_file.with_name("backup_locations.json")


def default_base(home: Path) -> Path:
    return home / DEFAULT_BASE_REL


def allowed_roots(home: Path) -> list[Path]:
    roots = [home]
    for external in (Path("/run/media"), Path("/media"), Path("/mnt")):
        if external.is_dir():
            roots.append(external)
    return roots


def _within(root: Path, other: Path) -> bool:
    try:
        other.relative_to(root)
        return True
    except ValueError:
        return False


def validated_folder(home: Path, text: str, *, for_backup: bool = False) -> Path:
    if not isinstance(text, str) or not text or len(text) > 2048 or "\x00" in text:
        raise FolderError("Invalid directory")
    raw = Path(text).expanduser()
    if not raw.is_absolute() or ".." in raw.parts:
        raise FolderError("Choose an absolute directory from the folder browser")
    if not raw.is_dir():
        raise FolderError("Folder does not exist or drive is disconnected")
    if raw.is_symlink():
        raise FolderError("Linked folders are not allowed as backup destinations")
    # Directory symlinks anywhere in the user-controlled segment are rejected.
    for root in allowed_roots(home):
        try:
            relative = raw.relative_to(root)
        except ValueError:
            continue
        if not relative.parts and root != home and for_backup:
            raise FolderError("Select the external drive itself, not the media mount root")
        current = root
        for segment in relative.parts:
            current = current / segment
            if current.is_symlink():
                raise FolderError("Select a real folder, not a symbolic link")
        if root != home and not relative.parts:
            if for_backup:
                raise FolderError("Select a drive or folder under this mount")
        if for_backup:
            if any(part.lower() in RESTRICTED for part in relative.parts):
                raise FolderError("Do not store backups in Steam data or Decky folders")
            # SteamOS root home may live on /var/home/... and resolve via a
            # system link. Compare relative segments, not absolute resolved roots.
            if relative.parts[:3] == (".local", "share", "Steam") or (
                relative.parts and relative.parts[0] == ".steam"
            ):
                raise FolderError("Do not store backups within the Steam library")
        if not _within(root.resolve(), raw.resolve()):
            raise FolderError("Folder resolves outside the selected storage root")
        return raw
    raise FolderError("Select a folder under Home, /run/media, /media or /mnt")


def browser(home: Path, path: str = "") -> dict[str, Any]:
    if not path:
        choices = [
            {"name": "Home", "path": str(home)},
        ]
        for mount, title in ((Path("/run/media"), "Removable drives (/run/media)"),
                             (Path("/media"), "Other drives (/media)"),
                             (Path("/mnt"), "Mounted disks (/mnt)")):
            if mount.is_dir():
                choices.append({"name": title, "path": str(mount)})
        return {"ok": True, "path": "", "parent": "", "folders": choices,
                "selectable": False, "free": 0}

    folder = validated_folder(home, path)
    directories = []
    try:
        for child in folder.iterdir():
            if child.name in (".", "..") or child.is_symlink() or not child.is_dir():
                continue
            if child.name.startswith(".") and child.name not in (".local",):
                continue
            directories.append({"name": child.name, "path": str(child)})
            if len(directories) > 300:
                raise FolderError("Folder contains too many subdirectories")
    except OSError as exc:
        raise FolderError("Cannot list folder: " + str(exc)) from exc
    parent = "" if folder in allowed_roots(home) else str(folder.parent)
    selectable = True
    try:
        validated_folder(home, path, for_backup=True)
    except FolderError:
        selectable = False
    stat = os.statvfs(folder)
    return {
        "ok": True, "path": str(folder), "parent": parent,
        "folders": sorted(directories, key=lambda x: x["name"].casefold()),
        "selectable": selectable,
        "free": stat.f_bavail * stat.f_frsize,
    }


def _read_settings(cache_file: Path) -> dict:
    try:
        obj = json.loads(locations_file(cache_file).read_text(encoding="utf-8"))
        if isinstance(obj, dict) and obj.get("schema") == 1:
            return obj
    except (OSError, ValueError):
        pass
    return {"schema": 1, "selected": "", "history": []}


def _write_settings(cache_file: Path, value: dict) -> None:
    path = locations_file(cache_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                                         dir=path.parent, prefix=".gs-locations-",
                                         delete=False) as f:
            temp = Path(f.name)
            json.dump(value, f, ensure_ascii=False)
        os.replace(temp, path)
    finally:
        if temp:
            temp.unlink(missing_ok=True)


def selected_base(home: Path, cache_file: Path) -> Path:
    settings = _read_settings(cache_file)
    raw = settings.get("selected")
    if isinstance(raw, str) and raw:
        return validated_folder(home, raw, for_backup=True)
    return default_base(home)


def backup_root_for(home: Path, cache_file: Path) -> Path:
    return selected_base(home, cache_file) / APP_DIR


def known_backup_roots(home: Path, cache_file: Path | None) -> list[Path]:
    bases = [default_base(home)]
    if cache_file is not None:
        setting = _read_settings(cache_file)
        bases.extend([setting.get("selected"), *setting.get("history", [])])
    result, seen = [], set()
    for base in bases:
        if not isinstance(base, (str, Path)) or not str(base):
            continue
        try:
            valid = validated_folder(home, str(base), for_backup=True)
        except FolderError:
            continue
        path = valid / APP_DIR
        if str(path) not in seen and not path.is_symlink():
            result.append(path)
            seen.add(str(path))
    return result


def location_status(home: Path, cache_file: Path) -> dict:
    settings = _read_settings(cache_file)
    raw = settings.get("selected")
    base = selected_base(home, cache_file)
    st = os.statvfs(base)
    return {"ok": True, "base": str(base), "folder": str(base / APP_DIR),
            "default": not bool(raw), "free": st.f_bavail * st.f_frsize,
            "known": len(known_backup_roots(home, cache_file))}


def choose_location(home: Path, cache_file: Path, path: str) -> dict:
    base = validated_folder(home, path, for_backup=True)
    # Check writing on actual selected volume *before* storing the selection.
    with tempfile.NamedTemporaryFile(dir=base, prefix=".gamesweep-write-test-"):
        pass
    output = base / APP_DIR
    if output.is_symlink() or (base / "GameSweep").is_symlink():
        raise FolderError("Destination contains a symbolic-link GameSweep folder")
    previous = _read_settings(cache_file)
    history = [str(base), previous.get("selected", ""),
               *previous.get("history", [])]
    history = list(dict.fromkeys(v for v in history if v))[:HISTORY_LIMIT]
    _write_settings(cache_file, {"schema": 1, "selected": str(base),
                                 "history": history})
    return location_status(home, cache_file)


def reset_location(home: Path, cache_file: Path) -> dict:
    settings = _read_settings(cache_file)
    old = settings.get("selected", "")
    history = [old, *settings.get("history", [])]
    history = list(dict.fromkeys(v for v in history if isinstance(v, str) and v))[:HISTORY_LIMIT]
    _write_settings(cache_file, {"schema": 1, "selected": "", "history": history})
    return location_status(home, cache_file)
