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


def _current_selection(home: Path, cache_file: Path, library: str, appid: str, kind: str, allow_installed: bool = False) -> dict[str, Any]:
    _validate_input(library, appid, kind)
    current = scan(home, cache_file)
    if current["missing_libraries"]:
        raise CleanupError("One or more Steam libraries are offline; cleanup is disabled")
    if library not in current["libraries"]:
        raise CleanupError("Steam library is no longer registered")
    match = next((i for i in current["entries"] if i["id"] == appid and i["library"] == library), None)
    if match is None:
        raise CleanupError("AppID not found on the selected library")
    if match["status"] == "installed" and allow_installed is not True:
        raise CleanupError("Installed-game data needs separate explicit authorization")
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
        "game_type": match["game_type"],
        "type_source": match["type_source"],
        "allow_installed": allow_installed is True,
        "bytes": match[kind + "_bytes"],
        "device": info.st_dev,
        "inode": info.st_ino,
    }


def preview_cleanup(home: Path, cache_file: Path, library: str, appid: str, kind: str, allow_installed: bool = False) -> dict[str, Any]:
    entry = _current_selection(home, cache_file, library, appid, kind, allow_installed=allow_installed)
    # Keep the filesystem fingerprint in backend-only state; do not expose it
    # to user-provided values on execution.
    return entry


def execute_cleanup(home: Path, cache_file: Path, preview: dict[str, Any]) -> dict[str, Any]:
    """Re-scan under caller's lock, then delete exactly one previewed folder."""
    if not getattr(shutil.rmtree, "avoids_symlink_attacks", False):
        raise CleanupError("This Python platform cannot guarantee symlink-safe deletion")
    fresh = _current_selection(
        home, cache_file,
        preview["library"], preview["appid"], preview["kind"],
        allow_installed=preview["allow_installed"]
    )
    # A preview is valid only for the state and classification it showed.
    # If a shortcut or installation changes, ask for a new confirmation.
    if fresh["status"] != preview["status"] or fresh["game_type"] != preview["game_type"]:
        raise CleanupError("Game installation or classification changed since confirmation")
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


def preview_all_cleanup(home: Path, cache_file: Path, library: str,
                        appid: str, allow_installed: bool = False) -> dict[str, Any]:
    """Preview every existing game-data directory; not the game installation."""
    if not isinstance(allow_installed, bool):
        raise CleanupError("Invalid installed-game authorization")
    _validate_input(library, appid, "prefix")
    snapshot = scan(home, cache_file)
    if snapshot["missing_libraries"]:
        raise CleanupError("One or more Steam libraries are offline; cleanup is disabled")
    if library not in snapshot["libraries"]:
        raise CleanupError("Steam library is no longer registered")
    item = next((i for i in snapshot["entries"]
                 if i["id"] == appid and i["library"] == library), None)
    if item is None:
        raise CleanupError("Game data not found in selected Steam library")
    # A manually placed symlink with this AppID is never silently ignored.
    # If it exists in either category, refuse combined deletion entirely.
    for category in CATEGORIES.values():
        candidate = Path(library) / "steamapps" / category / appid
        if candidate.is_symlink():
            raise CleanupError("Symbolic link game data found; cleanup refused")
    kinds = [kind for kind in ("prefix", "shader") if item.get(kind + "_path")]
    if not kinds:
        raise CleanupError("No compatdata or shader cache folders found")

    # Each target is independently checked; no deletion occurs during preview.
    targets = [
        _current_selection(home, cache_file, library, appid, kind,
                           allow_installed=allow_installed)
        for kind in kinds
    ]
    if any(target["status"] != targets[0]["status"] or
           target["game_type"] != targets[0]["game_type"] for target in targets):
        raise CleanupError("Inconsistent game metadata; rescan required")
    return {
        "library": library, "appid": appid, "kind": "all",
        "name": targets[0]["name"], "status": targets[0]["status"],
        "game_type": targets[0]["game_type"],
        "type_source": targets[0]["type_source"],
        "allow_installed": allow_installed,
        "targets": targets,
        "bytes": sum(target["bytes"] for target in targets),
    }


def _delete_pinned_target(target: dict[str, Any]) -> None:
    """Delete the pinned directory with an fd-anchored symlink-safe rmtree."""
    path = Path(target["target"])
    flags = os.O_RDONLY | os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path.parent, flags)
    try:
        before = os.stat(target["appid"], dir_fd=fd, follow_symlinks=False)
        if (before.st_dev, before.st_ino) != (target["device"], target["inode"]):
            raise CleanupError("Folder changed while preparing deletion")
        if not stat.S_ISDIR(before.st_mode):
            raise CleanupError("Target is no longer a directory")
        shutil.rmtree(target["appid"], dir_fd=fd)
    except OSError as exc:
        raise CleanupError("Filesystem removal failed: " + str(exc)) from exc
    finally:
        os.close(fd)


def execute_all_cleanup(home: Path, cache_file: Path,
                        preview: dict[str, Any]) -> dict[str, Any]:
    """Validate all targets before deleting; report partial failures clearly."""
    if preview.get("kind") != "all" or not preview.get("targets"):
        raise CleanupError("Invalid combined cleanup request")
    if not getattr(shutil.rmtree, "avoids_symlink_attacks", False):
        raise CleanupError("This Python platform cannot guarantee symlink-safe deletion")

    # Re-check both folders, metadata, and each inode BEFORE removing either.
    fresh = preview_all_cleanup(
        home, cache_file, preview["library"], preview["appid"],
        allow_installed=preview["allow_installed"],
    )
    previous = {item["kind"]: item for item in preview["targets"]}
    current = {item["kind"]: item for item in fresh["targets"]}
    if previous.keys() != current.keys():
        raise CleanupError("Available game data changed since confirmation")
    if fresh["status"] != preview["status"] or fresh["game_type"] != preview["game_type"]:
        raise CleanupError("Game installation or classification changed since confirmation")
    for kind, target in current.items():
        earlier = previous[kind]
        for field in ("target", "device", "inode"):
            if target[field] != earlier[field]:
                raise CleanupError("Game data folders changed since confirmation")

    removed: list[str] = []
    for kind in ("prefix", "shader"):
        if kind not in current:
            continue
        try:
            _delete_pinned_target(current[kind])
            removed.append(kind)
        except CleanupError as exc:
            raise CleanupError(
                "Combined cleanup incomplete: removed " +
                (", ".join(removed) if removed else "nothing") +
                "; could not delete " + kind + ": " + str(exc) +
                ". Rescan to inspect remaining data."
            ) from exc
    return {
        "success": True,
        "name": preview["name"],
        "kind": "all",
        "removed_kinds": removed,
        "bytes": sum(item["bytes"] for item in fresh["targets"]),
    }
