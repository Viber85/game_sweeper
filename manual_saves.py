"""Per-game manual save folder selection, restricted to a Steam Proton prefix.

The user chooses a specific folder in the fullscreen browser. Broad folders
such as the entire C: drive or AppData are never eligible for backup.
"""
from __future__ import annotations
import json
import os
import re
import stat
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

MAX_MANUAL_FILES = 4000
MAX_MANUAL_BYTES = 4 * 1024**3


class ManualSaveError(ValueError):
    pass


def overrides_path(cache_file: Path) -> Path:
    return cache_file.with_name("manual_save_folders.json")


def _key(library: str, appid: str) -> str:
    return library + "|" + appid


def _read(cache_file: Path) -> dict[str, str]:
    try:
        data = json.loads(overrides_path(cache_file).read_text(encoding="utf-8"))
        return {
            k: v for k, v in data.items()
            if isinstance(k, str) and isinstance(v, str) and len(v) <= 600
        } if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _write(cache_file: Path, data: dict[str, str]) -> None:
    path = overrides_path(cache_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent,
                                         prefix=".gs-manual-", delete=False) as f:
            temp = Path(f.name)
            json.dump(dict(list(data.items())[-300:]), f)
        os.replace(temp, path)
    finally:
        if temp:
            temp.unlink(missing_ok=True)


def chosen_folder(cache_file: Path, library: str, appid: str) -> str:
    return _read(cache_file).get(_key(library, appid), "")


def validate_relative(relative: str) -> Path:
    if not isinstance(relative, str) or len(relative) > 600 or not relative:
        raise ManualSaveError("Choose a specific game-save folder")
    norm = PurePosixPath(relative.replace("\\", "/"))
    if norm.is_absolute() or any(p in ("", ".", "..") for p in norm.parts):
        raise ManualSaveError("Invalid relative save folder path")
    parts = norm.parts
    # Avoid backing up an entire OS profile or broad AppData tree.
    if len(parts) < 2:
        raise ManualSaveError("Choose a folder belonging to one game")
    if parts[0].lower() == "users" and len(parts) < 4:
        raise ManualSaveError("Select a specific game directory under the Windows user")
    if parts[-1].casefold() in {
        "users", "public", "steamuser", "appdata", "roaming", "local",
        "locallow", "documents", "my documents", "saved games", "programdata",
        "program files", "program files (x86)", "windows"
    }:
        raise ManualSaveError("Choose the game's save folder, not a system folder")
    if parts[0].casefold() in {"windows", "program files", "program files (x86)"}:
        raise ManualSaveError("System and installation folders cannot be selected")
    return Path(*parts)


def _in_prefix(prefix: Path, relative: str, *, require_specific: bool = True) -> Path:
    rel = validate_relative(relative) if require_specific else Path(relative)
    drive = prefix / "pfx/drive_c"
    path = drive / rel
    current = prefix
    for part in path.relative_to(prefix).parts:
        current = current / part
        if current.is_symlink():
            raise ManualSaveError("Linked save folders cannot be backed up")
    if not path.is_dir():
        raise ManualSaveError("Selected save folder was not found")
    return path


def inspect_manual_folder(prefix: Path, relative: str) -> list[dict]:
    selected = _in_prefix(prefix, relative)
    files: list[dict] = []
    total = 0
    for base, dirs, filenames in os.walk(selected, followlinks=False):
        current = Path(base)
        for dirname in dirs:
            if (current / dirname).is_symlink():
                raise ManualSaveError("Save folder contains a symbolic-link directory")
        for filename in filenames:
            file = current / filename
            if file.is_symlink():
                raise ManualSaveError("Save folder contains a symbolic-link file")
            info = file.lstat()
            if not stat.S_ISREG(info.st_mode):
                continue
            total += info.st_size
            if len(files) >= MAX_MANUAL_FILES or total > MAX_MANUAL_BYTES:
                raise ManualSaveError("Manual save folder exceeds the backup limit")
            files.append({
                "relative": file.relative_to(prefix).as_posix(),
                "size": info.st_size, "mtime_ns": info.st_mtime_ns,
            })
    return sorted(files, key=lambda item: item["relative"])


def browse_game_save_folders(prefix: Path, relative: str = "") -> dict[str, Any]:
    drive = prefix / "pfx/drive_c"
    if not drive.is_dir() or drive.is_symlink():
        raise ManualSaveError("Windows C: drive not found in this Proton prefix")
    if relative:
        # Browsing is permitted through the Windows user hierarchy but selection
        # has stricter rules.
        normalized = PurePosixPath(relative.replace("\\", "/"))
        if normalized.is_absolute() or ".." in normalized.parts:
            raise ManualSaveError("Invalid folder navigation")
        path = drive / Path(*normalized.parts)
    else:
        path = drive
    current = prefix
    for part in path.relative_to(prefix).parts:
        current = current / part
        if current.is_symlink():
            raise ManualSaveError("Linked directories cannot be browsed")
    if not path.is_dir():
        raise ManualSaveError("Folder is unavailable")

    children = []
    try:
        for child in path.iterdir():
            if child.is_dir() and not child.is_symlink():
                children.append({
                    "name": child.name,
                    "relative": child.relative_to(drive).as_posix(),
                })
            if len(children) > 250:
                raise ManualSaveError("Too many folders to show")
    except OSError as exc:
        raise ManualSaveError("Cannot open save directory") from exc

    selectable = False
    count = 0
    size = 0
    if relative:
        try:
            inspected = inspect_manual_folder(prefix, relative)
            count, size = len(inspected), sum(x["size"] for x in inspected)
            selectable = count > 0
        except (ManualSaveError, OSError):
            pass
    parent = ""
    if relative:
        parent = PurePosixPath(relative).parent.as_posix()
        if parent == ".":
            parent = ""
    return {
        "ok": True, "relative": relative, "parent": parent,
        "folders": sorted(children, key=lambda x: x["name"].casefold()),
        "selectable": selectable, "count": count, "bytes": size,
    }


def select_manual_save_folder(cache_file: Path, library: str, appid: str,
                              prefix: Path, relative: str) -> dict:
    inspected = inspect_manual_folder(prefix, relative)
    if not inspected:
        raise ManualSaveError("This folder does not contain regular save files")
    saved = _read(cache_file)
    saved[_key(library, appid)] = relative
    _write(cache_file, saved)
    return {"ok": True, "relative": relative, "count": len(inspected),
            "bytes": sum(item["size"] for item in inspected)}


def clear_manual_save_folder(cache_file: Path, library: str, appid: str) -> dict:
    saved = _read(cache_file)
    saved.pop(_key(library, appid), None)
    _write(cache_file, saved)
    return {"ok": True}
