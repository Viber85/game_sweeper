"""Guarded, permanent cleanup of individual Steam compatdata/shadercache dirs.

No arbitrary paths accepted. Every cleanup is revalidated against a fresh
Steam manifest + shortcut scan, and the target's device/inode are pinned
between preview and deletion. This remains deliberately opt-in.
"""
from __future__ import annotations

import os
import re
import shutil
import stat
from pathlib import Path
from typing import Any

from scanner import scan

CATEGORIES = {"prefix": "compatdata", "shader": "shadercache"}
VALID_ID = re.compile(r"^[0-9]{1,20}$")


class CleanupError(ValueError):
    pass


def _validate_input(library: str, appid: str, kind: str) -> None:
    if not isinstance(library, str) or not library:
        raise CleanupError("Missing Steam library")
    if not isinstance(appid, str) or not VALID_ID.fullmatch(appid):
        raise CleanupError("Invalid AppID")
    if kind not in CATEGORIES:
        raise CleanupError("Invalid cleanup category")


def _running_app_or_prefix(appid: str, target: Path) -> bool:
    """Best-effort safety check: stop if a process advertises this game/prefix.

    This cannot detect *every* process, so the confirmation UI also warns the
    user to close games before cleaning.
    """
    try:
        proc = Path("/proc")
        with os.scandir(proc) as pids:
            for process in pids:
                if not process.name.isdigit():
                    continue
                try:
                    with open(f"/proc/{process.name}/environ", "rb") as handle:
                        data = handle.read(131072)
                except (PermissionError, FileNotFoundError, ProcessLookupError, OSError):
                    continue
                for field in data.split(b"\x00"):
                    if b"=" not in field:
                        continue
                    key, value = field.split(b"=", 1)
                    if key in (b"SteamAppId", b"SteamGameId", b"STEAM_APP_ID"):
                        if value.decode("ascii", "ignore") == appid:
                            return True
                    if key == b"STEAM_COMPAT_DATA_PATH":
                        try:
                            if Path(os.fsdecode(value)).resolve() == target.resolve():
                                return True
                        except (OSError, ValueError):
                            pass
    except OSError:
        pass
    return False


def _target_stat(library: str, appid: str, kind: str) -> tuple[Path, os.stat_result]:
    parent = Path(library) / "steamapps" / CATEGORIES[kind]
    try:
        # Library and steamapps may themselves be Steam-managed symlinks,
        # but the immediate category dir must not be a symlink.
        if parent.is_symlink():
            raise CleanupError("Cleanup directory is a symlink")
        if not parent.is_dir():
            raise CleanupError("Target parent directory unavailable")
        target = parent / appid
        info = target.lstat()
    except (OSError, ValueError) as e:
        raise CleanupError("Target folder unavailable or changed") from e
    if not stat.S_ISDIR(info.st_mode) or target.is_symlink():
        raise CleanupError("Target is not a regular directory")
    return target, info


def _current_selection(home: Path, cache_file: Path, library: str, appid: str, kind: str) -> dict[str, Any]:
    _validate_input(library, appid, kind)
    current = scan(home, cache_file)
    if current["missing_libraries"]:
        raise CleanupError("One or more Steam libraries are offline; cleanup is disabled")
    if library not in current["libraries"]:
        raise CleanupError("Steam library is no longer registered")
    match = next((i for i in current["entries"] if i["id"] == appid and i["library"] == library), None)
    if match is None:
        raise CleanupError("AppID not found on the selected library")
    if match["status"] == "installed":
        raise CleanupError("An installed Steam game or active Non-Steam shortcut is protected")
    key = kind + "_path"
    target, info = _target_stat(library, appid, kind)
    if not match.get(key) or Path(match[key]) != target:
        raise CleanupError("Requested folder is not part of the current scan")
    if _running_app_or_prefix(appid, target):
        raise CleanupError("A process for this game or Proton prefix appears to be running")
    return {
        "library": library,
        "appid": appid,
        "kind": kind,
        "target": str(target),
        "name": match["name"],
        "status": match["status"],
        "bytes": match[kind + "_bytes"],
        "device": info.st_dev,
        "inode": info.st_ino,
    }


def preview_cleanup(home: Path, cache_file: Path, library: str, appid: str, kind: str) -> dict[str, Any]:
    entry = _current_selection(home, cache_file, library, appid, kind)
    # Keep the filesystem fingerprint in backend-only state; do not expose it
    # to user-provided values on execution.
    return entry


def execute_cleanup(home: Path, cache_file: Path, preview: dict[str, Any]) -> dict[str, Any]:
    """Re-scan under caller's lock, then delete exactly one previewed folder."""
    if not getattr(shutil.rmtree, "avoids_symlink_attacks", False):
        raise CleanupError("This Python platform cannot guarantee symlink-safe deletion")
    fresh = _current_selection(
        home, cache_file,
        preview["library"], preview["appid"], preview["kind"]
    )
    if fresh["target"] != preview["target"]:
        raise CleanupError("Target path changed since confirmation")
    if (fresh["device"], fresh["inode"]) != (preview["device"], preview["inode"]):
        raise CleanupError("Target folder changed since confirmation")

    parent = Path(fresh["target"]).parent
    # Anchor removal to a directory FD, preventing a moved parent from
    # redirecting the deletion outside the scanned Steam library.
    flags = os.O_RDONLY | os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(parent, flags)
    try:
        before = os.stat(fresh["appid"], dir_fd=fd, follow_symlinks=False)
        if (before.st_dev, before.st_ino) != (preview["device"], preview["inode"]):
            raise CleanupError("Target changed while preparing the delete")
        if not stat.S_ISDIR(before.st_mode):
            raise CleanupError("Target no longer a directory")
        shutil.rmtree(fresh["appid"], dir_fd=fd)
    except OSError as exc:
        raise CleanupError("Filesystem removal failed: " + str(exc)) from exc
    finally:
        os.close(fd)
    return {
        "success": True,
        "name": preview["name"],
        "kind": preview["kind"],
        "bytes": preview["bytes"],
    }
