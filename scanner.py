"""Read-only Steam library scanner for GameSweep.

Never deletes, modifies, or follows filesystem links while scanning.
"""
from __future__ import annotations

import json
import os
import re
import stat
from shutil import disk_usage
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from shortcuts import collect_shortcuts

VALUE = re.compile(r'"([^"\\]+)"\s+"((?:\\.|[^"\\])*)"')
MAX_CACHE_ENTRIES = 30000


def vdf_pairs(text: str):
    """Read quoted string pairs; sufficient for paths, AppID and names."""
    for match in VALUE.finditer(text):
        raw = match.group(2)
        yield match.group(1).lower(), raw.replace(r'\"', '"').replace(r'\\', '\\')


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig", errors="replace")
    except (OSError, UnicodeError):
        return ""


def steam_roots(home: Path) -> list[Path]:
    paths = [
        home / ".local/share/Steam",
        home / ".steam/steam",
        home / ".steam/root",
    ]
    result: list[Path] = []
    seen: set[str] = set()
    for item in paths:
        if not item.is_dir():
            continue
        resolved = item.resolve()
        key = str(resolved)
        if key not in seen:
            seen.add(key)
            result.append(resolved)
    return result


def discover_libraries(home: Path) -> tuple[list[Path], list[str]]:
    roots = steam_roots(home)
    candidates: list[Path] = [root for root in roots]
    missing: list[str] = []
    for root in roots:
        library_file = root / "steamapps/libraryfolders.vdf"
        if not library_file.is_file():
            continue
        for key, value in vdf_pairs(read_text(library_file)):
            if key != "path":
                continue
            directory = Path(value).expanduser()
            if directory.is_absolute():
                candidates.append(directory)
    libraries: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        target = candidate / "steamapps"
        if not target.is_dir():
            if str(candidate) not in missing:
                missing.append(str(candidate))
            continue
        resolved = target.resolve()
        path_key = str(resolved)
        if path_key not in seen:
            seen.add(path_key)
            libraries.append(resolved)
    return libraries, missing


def manifests(libraries: list[Path]) -> dict[str, str]:
    installed: dict[str, str] = {}
    for apps in libraries:
        try:
            files = apps.glob("appmanifest_*.acf")
            for path in files:
                if not path.is_file():
                    continue
                appid = path.stem.removeprefix("appmanifest_")
                if not appid.isdigit():
                    continue
                data = dict(vdf_pairs(read_text(path)))
                if data.get("appid") not in (None, appid):
                    continue
                installed[appid] = data.get("name", "").strip() or installed.get(appid, "")
        except OSError:
            continue
    return installed


def read_cache(cache_file: Path) -> dict[str, str]:
    try:
        data = json.loads(cache_file.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {
                str(k): v[:180]
                for k, v in data.items()
                if str(k).isdigit() and isinstance(v, str) and v.strip()
            }
    except (OSError, ValueError, TypeError):
        pass
    return {}


def write_cache(cache_file: Path, cache: dict[str, str]) -> None:
    """Store known labels outside Steam files, using an atomic replace."""
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(dict(list(cache.items())[-MAX_CACHE_ENTRIES:]), ensure_ascii=False)
    temp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=cache_file.parent,
            prefix=".gamesweep-", delete=False
        ) as handle:
            temp_path = handle.name
            handle.write(serialized)
        os.replace(temp_path, cache_file)
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)


def directory_bytes(folder: Path) -> int:
    """Count regular files once, ignoring symlinks and special files."""
    total = 0
    try:
        for root, dirs, files in os.walk(folder, topdown=True, followlinks=False):
            dirs[:] = [
                name for name in dirs
                if not (Path(root) / name).is_symlink()
            ]
            for name in files:
                try:
                    s = (Path(root) / name).lstat()
                    if stat.S_ISREG(s.st_mode):
                        total += s.st_size
                except OSError:
                    continue
    except OSError:
        pass
    return total


def scan(home: Path, cache_file: Path) -> dict[str, Any]:
    libraries, missing = discover_libraries(home)
    installed = manifests(libraries)
    active_shortcuts, older_shortcuts = collect_shortcuts(steam_roots(home))
    titles = read_cache(cache_file)
    # Persist *provenance*, not a guess based on numerical AppID ranges.
    # This preserves Steam/Non-Steam identification after uninstalling a game
    # or removing a shortcut, whenever the game was previously observed.
    type_file = cache_file.with_name("known_types.json")
    known_types = read_cache(type_file)
    changed_names = False
    changed_types = False
    known = {**older_shortcuts, **active_shortcuts, **installed}
    for appid, name in known.items():
        if name and titles.get(appid) != name:
            titles[appid] = name
            changed_names = True
    # Most reliable evidence wins. The main Steam manifest overrides a
    # conflicting shortcut; an active shortcut overrides an old backup.
    observed_types = {appid: "non_steam" for appid in older_shortcuts}
    observed_types.update({appid: "non_steam" for appid in active_shortcuts})
    observed_types.update({appid: "steam" for appid in installed})
    for appid, kind in observed_types.items():
        if known_types.get(appid) != kind:
            known_types[appid] = kind
            changed_types = True
    try:
        if changed_names:
            write_cache(cache_file, titles)
        if changed_types:
            write_cache(type_file, known_types)
    except OSError:
        pass  # Scanning still succeeds if settings storage is read-only.

    items: list[dict[str, Any]] = []
    for steamapps in libraries:
        by_id: dict[str, dict[str, Any]] = {}
        for category, kind in (("compatdata", "prefix"), ("shadercache", "shader")):
            parent = steamapps / category
            if not parent.is_dir():
                continue
            try:
                with os.scandir(parent) as entries:
                    for entry in entries:
                        if not entry.name.isdigit() or not entry.is_dir(follow_symlinks=False):
                            continue
                        appid = entry.name
                        row = by_id.setdefault(appid, {
                            "id": appid,
                            "library": str(steamapps.parent),
                            "prefix_path": "",
                            "shader_path": "",
                            "prefix_bytes": 0,
                            "shader_bytes": 0,
                        })
                        row[kind + "_path"] = entry.path
                        row[kind + "_bytes"] = directory_bytes(Path(entry.path))
            except OSError:
                continue

        for appid, row in by_id.items():
            has_manifest = appid in installed
            uncertain_id = int(appid) >= 2147483648
            if has_manifest:
                status = "installed"
                reason = "Steam installation manifest found"
            elif appid in active_shortcuts:
                status = "installed"
                reason = "Active Non-Steam shortcut found in Steam userdata; protect this prefix"
            elif missing:
                status = "review"
                reason = "A Steam library is unavailable; cannot verify install status"
            elif uncertain_id:
                status = "review"
                reason = (
                    "Title recovered from an older shortcut backup; verify before cleanup"
                    if appid in older_shortcuts else
                    "Possibly a removed Non-Steam shortcut or custom AppID; cannot identify from the number alone"
                )
            else:
                status = "candidate"
                reason = "No installed Steam manifest found; verify before any cleanup"
            if appid in installed:
                game_type, type_source = "steam", "manifest"
            elif appid in active_shortcuts:
                game_type, type_source = "non_steam", "shortcut"
            elif appid in older_shortcuts:
                game_type, type_source = "non_steam", "backup"
            elif known_types.get(appid) in ("steam", "non_steam"):
                game_type, type_source = known_types[appid], "history"
            else:
                game_type, type_source = "unknown", "unknown"
            row["game_type"] = game_type
            row["type_source"] = type_source
            row["status"] = status
            row["reason"] = reason
            row["name"] = (
                installed.get(appid) or active_shortcuts.get(appid) or
                older_shortcuts.get(appid) or titles.get(appid) or
                ("Unknown game (" + appid + ")")
            )
            row["name_source"] = (
                "manifest" if installed.get(appid) else
                "shortcut" if active_shortcuts.get(appid) else
                "backup" if older_shortcuts.get(appid) else
                "cache" if titles.get(appid) else "unknown"
            )
            row["bytes"] = row["prefix_bytes"] + row["shader_bytes"]
            items.append(row)

    items.sort(key=lambda x: (-x["bytes"], x["name"].lower()))
    disks = []
    for apps in libraries:
        try:
            usage = disk_usage(apps)
            disks.append({
                "library": str(apps.parent),
                "total": usage.total,
                "used": usage.used,
                "free": usage.free,
            })
        except OSError:
            continue
    return {
        "version": "0.6.0",
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "libraries": [str(path.parent) for path in libraries],
        "disks": disks,
        "missing_libraries": missing,
        "entries": items,
        "summary": {
            "items": len(items),
            "installed": sum(x["status"] == "installed" for x in items),
            "candidate": sum(x["status"] == "candidate" for x in items),
            "review": sum(x["status"] == "review" for x in items),
            "bytes": sum(x["bytes"] for x in items),
            "candidate_bytes": sum(x["bytes"] for x in items if x["status"] == "candidate"),
        },
    }
