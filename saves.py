"""GameSweep save-only Backup & Restore for Proton Windows profiles.

Uses *save-tagged* paths from a curated, offline Ludusavi manifest index.
No entire prefix, arbitrary AppData folders, shader caches, or game installs.
Backups live outside Decky plugin directory to survive plugin updates.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any
from uuid import uuid4

from cleanup import _running_app_or_prefix
from scanner import scan
from backup_locations import backup_root_for, known_backup_roots
from manual_saves import chosen_folder, inspect_manual_folder, ManualSaveError

RULES_FILE = Path(__file__).resolve().parent / "save_rules.json"
BACKUP_RELATIVE = Path(".local/share/GameSweep/save-backups")
MAX_FILES = 4000
MAX_BYTES = 4 * 1024**3
MAX_RULES = 150
MAX_SNAPSHOTS = 500
ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")
APPID = re.compile(r"^\d{1,20}$")
SUPPORTED_ROOTS = {
    "<winAppData>", "<winLocalAppData>", "<winLocalAppDataLow>",
    "<winDocuments>", "<home>", "<winPublic>", "<winProgramData>",
}
ROOT_RE = re.compile(r"^(<[^>]+>)(?:/(.*))?$")


class SaveError(ValueError):
    pass


def _normal_title(title: str) -> str:
    return " ".join(title.casefold().split())


def _load_rules(path: Path = RULES_FILE) -> dict[str, Any]:
    try:
        if path.stat().st_size > 12_000_000:
            raise SaveError("Save location database is unexpectedly large")
        rules = json.loads(path.read_text(encoding="utf-8"))
        if rules.get("schema") != 1:
            raise SaveError("Unsupported save rule database")
        return rules
    except (OSError, json.JSONDecodeError, AttributeError) as exc:
        raise SaveError("Offline save rules unavailable; reinstall a complete release ZIP") from exc


def _select_game(home: Path, cache_file: Path, library: str, appid: str) -> dict:
    if not isinstance(library, str) or not library or not isinstance(appid, str) or not APPID.fullmatch(appid):
        raise SaveError("Invalid game selection")
    data = scan(home, cache_file)
    if data["missing_libraries"]:
        raise SaveError("A Steam library is offline; save operations are blocked")
    if library not in data["libraries"]:
        raise SaveError("Library is not registered with Steam")
    match = next((e for e in data["entries"] if e["library"] == library and e["id"] == appid), None)
    if match is None:
        raise SaveError("Game not found in registered Steam library")
    if not match["prefix_path"]:
        raise SaveError("This entry has no Proton prefix; native Linux saves are not yet supported")
    prefix = Path(match["prefix_path"])
    expected = Path(library) / "steamapps/compatdata" / appid
    if prefix != expected or prefix.is_symlink() or not prefix.is_dir():
        raise SaveError("Prefix is unavailable or linked outside the Steam library")
    return match


def _safe_relative(relative: str) -> Path:
    if not isinstance(relative, str) or len(relative) > 700:
        raise SaveError("Invalid backup path")
    rel = PurePosixPath(relative)
    if (rel.is_absolute() or ".." in rel.parts or len(rel.parts) < 4
            or tuple(rel.parts[:2]) != ("pfx", "drive_c")):
        raise SaveError("Backup path is outside the Proton prefix")
    return Path(*rel.parts)


def _no_link_parents(base: Path, target: Path) -> None:
    if base.is_symlink() or not target.is_relative_to(base):
        raise SaveError("Refusing a symlink or path outside Proton prefix")
    current = base
    for component in target.relative_to(base).parts:
        current = current / component
        if current.is_symlink():
            raise SaveError("Symbolic-link path found in save data")


def _profiles(prefix: Path) -> list[Path]:
    users = prefix / "pfx/drive_c/users"
    if not users.is_dir() or users.is_symlink():
        return []
    try:
        return [p for p in users.iterdir()
                if p.is_dir() and not p.is_symlink()
                and p.name.casefold() not in {"public", "default", "all users"}
                ][:20]
    except OSError:
        return []


def _match_rules(game: dict, index: dict) -> tuple[list[str], str]:
    steam_id = str(game["id"])
    by_id = index.get("by_steam_id", {})
    by_name = index.get("by_name", {})
    if game["game_type"] == "steam" and steam_id in by_id:
        return by_id[steam_id][:MAX_RULES], "Steam AppID"
    name = game["name"]
    if name.startswith("Unknown game ("):
        return [], ""
    exact = by_name.get(_normal_title(name), [])
    return exact[:MAX_RULES], "Exact game title" if exact else ""


def _rule_roots(prefix: Path, rule: str) -> list[tuple[Path, str]]:
    text = rule.replace("\\", "/")
    parsed = ROOT_RE.fullmatch(text)
    if not parsed:
        return []
    token, remainder = parsed.group(1), parsed.group(2) or ""
    if token not in SUPPORTED_ROOTS:
        return []
    if any(part in (".", "..") for part in PurePosixPath(remainder).parts):
        return []
    if "<" in remainder and "<osUserName>" not in remainder:
        return []
    drive = prefix / "pfx/drive_c"
    out = []
    for profile in _profiles(prefix):
        base = {
            "<winAppData>": profile / "AppData/Roaming",
            "<winLocalAppData>": profile / "AppData/Local",
            "<winLocalAppDataLow>": profile / "AppData/LocalLow",
            "<winDocuments>": profile / "Documents",
            "<home>": profile,
            "<winPublic>": drive / "users/Public",
            "<winProgramData>": drive / "ProgramData",
        }.get(token)
        if base is not None and remainder:
            # No globbing of profile names or expansion outside the prefix.
            tail = remainder.replace("<osUserName>", profile.name)
            if "<" not in tail and ".." not in PurePosixPath(tail).parts:
                out.append((base, tail))
    return list(dict.fromkeys(out))


def _find_files(prefix: Path, rules: list[str]) -> list[dict]:
    found: dict[str, dict] = {}
    size = 0
    for rule in rules:
        if not isinstance(rule, str) or len(rule) > 380:
            continue
        for base, pattern in _rule_roots(prefix, rule):
            if not base.is_dir() or base.is_symlink():
                continue
            # A manifest rule refers to a folder or a file/glob. Do not
            # include unrelated neighbors; files without save-tagged rules
            # are never collected.
            try:
                candidates = base.glob(pattern)
                for ix, path in enumerate(candidates):
                    if ix >= MAX_FILES:
                        raise SaveError("Save rule expands to too many paths")
                    _no_link_parents(prefix, path)
                    if not path.exists():
                        continue
                    if path.is_dir():
                        iterator = ((Path(root) / filename)
                                    for root, dirs, files in os.walk(path, followlinks=False)
                                    for filename in files)
                    else:
                        iterator = iter((path,))
                    for candidate in iterator:
                        _no_link_parents(prefix, candidate)
                        try:
                            st = candidate.lstat()
                        except OSError:
                            continue
                        if not stat.S_ISREG(st.st_mode):
                            continue
                        relative = candidate.relative_to(prefix).as_posix()
                        _safe_relative(relative)
                        if relative in found:
                            continue
                        size += st.st_size
                        if len(found) >= MAX_FILES or size > MAX_BYTES:
                            raise SaveError("Too many save files or save data exceeds 4 GiB")
                        found[relative] = {
                            "relative": relative, "size": st.st_size,
                            "mtime_ns": st.st_mtime_ns,
                        }
            except (OSError, ValueError) as exc:
                if isinstance(exc, SaveError):
                    raise
                continue
    return [found[key] for key in sorted(found)]


def preview_saves(home: Path, cache_file: Path, library: str, appid: str,
                  rules_file: Path = RULES_FILE) -> dict:
    game = _select_game(home, cache_file, library, appid)
    index = _load_rules(rules_file)
    rules, match_type = _match_rules(game, index)
    prefix = Path(game["prefix_path"])
    manual = chosen_folder(cache_file, library, appid)
    if manual:
        files = inspect_manual_folder(prefix, manual)
        match_type = "Manually selected folder: " + manual
    elif not rules:
        return {
            "ok": True, "supported": False, "name": game["name"],
            "appid": appid, "library": library, "count": 0, "bytes": 0,
            "sample": [], "method": "", "manual": False,
            "message": (
                "No save-location rule matched this game's Steam AppID or exact title. "
                "A Non-Steam game might use a different title or store-specific location. "
                "Use Find save folder manually to pick a specific folder inside its Proton prefix."
            ),
        }
    else:
        files = _find_files(prefix, rules)
    return {
        "ok": True, "supported": True, "name": game["name"],
        "appid": appid, "library": library, "count": len(files),
        "bytes": sum(item["size"] for item in files),
        "sample": [item["relative"] for item in files[:6]],
        "method": match_type, "manual": bool(manual),
        "message": "" if files else (
            "The matched save folder is empty." if manual else
            "A save-location rule matched, but no files were found in this Proton prefix. "
            "The game might use a different location or keep saves outside Proton; "
            "use Find save folder manually if you know where they are."
        ),
    }


def _source_files(home: Path, cache_file: Path, library: str, appid: str,
                  rules_file: Path) -> tuple[dict, list[dict]]:
    game = _select_game(home, cache_file, library, appid)
    rules, _ = _match_rules(game, _load_rules(rules_file))
    manual = chosen_folder(cache_file, library, appid)
    if not rules and not manual:
        raise SaveError("No verified save paths for this game; choose a save folder manually")
    prefix = Path(game["prefix_path"])
    if _running_app_or_prefix(appid, prefix):
        raise SaveError("Close the game before backing up its saves")
    files = inspect_manual_folder(prefix, manual) if manual else _find_files(prefix, rules)
    if not files:
        raise SaveError("No save files found; no empty backup was created")
    return game, files


def _copy_hash(source: Path, destination: Path, expected: dict) -> dict:
    destination.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    digest = hashlib.sha256()
    total = 0
    with os.fdopen(os.open(source, flags), "rb") as reader:
        st = os.fstat(reader.fileno())
        if not stat.S_ISREG(st.st_mode) or st.st_size != expected["size"] or st.st_mtime_ns != expected["mtime_ns"]:
            raise SaveError("Save changed during backup; close the game and retry")
        with destination.open("xb") as writer:
            while True:
                block = reader.read(1024 * 1024)
                if not block:
                    break
                total += len(block)
                if total > MAX_BYTES:
                    raise SaveError("Save data exceeds backup size limit")
                writer.write(block)
                digest.update(block)
        after = os.fstat(reader.fileno())
        if after.st_size != st.st_size or after.st_mtime_ns != st.st_mtime_ns:
            raise SaveError("Save changed during copy; backup discarded")
    if total != expected["size"]:
        raise SaveError("Incomplete save copy; backup discarded")
    return {"relative": expected["relative"], "size": total, "sha256": digest.hexdigest()}


def backup_root(home: Path) -> Path:
    return home / BACKUP_RELATIVE


def create_backup(home: Path, cache_file: Path, library: str, appid: str,
                  rules_file: Path = RULES_FILE) -> dict:
    game, files = _source_files(home, cache_file, library, appid, rules_file)
    prefix = Path(game["prefix_path"])
    root = backup_root_for(home, cache_file)
    if root.parent.is_symlink() or root.is_symlink():
        raise SaveError("Backup location is a symbolic link")
    root.mkdir(parents=True, exist_ok=True)
    required = sum(item["size"] for item in files)
    if shutil.disk_usage(root).free < required + 16 * 1024**2:
        raise SaveError("Not enough free disk space for a save backup")
    backup_id = uuid4().hex
    stage = root / (".partial-" + backup_id)
    destination = root / backup_id
    stage.mkdir(mode=0o700)
    try:
        copied = []
        for entry in files:
            relative = _safe_relative(entry["relative"])
            source = prefix / relative
            _no_link_parents(prefix, source)
            copied.append(_copy_hash(source, stage / "files" / relative, entry))
        metadata = {
            "schema": 1, "id": backup_id, "appid": appid, "library": library,
            "name": game["name"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "files": copied, "bytes": sum(item["size"] for item in copied),
            "count": len(copied),
        }
        (stage / "manifest.json").write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        stage.rename(destination)
        return {
            **{key: value for key, value in metadata.items() if key != "files"},
            "backup_folder": str(root),
        }
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def _load_backup(home: Path, backup_id: str,
                 cache_file: Path | None = None) -> tuple[Path, dict]:
    if not isinstance(backup_id, str) or not ID_PATTERN.fullmatch(backup_id):
        raise SaveError("Invalid backup identifier")
    directory = next(
        (root / backup_id for root in known_backup_roots(home, cache_file)
         if (root / backup_id).is_dir() and not (root / backup_id).is_symlink()),
        None,
    )
    if directory is None:
        raise SaveError("Backup unavailable. Connect the drive used for this snapshot.")
    try:
        metadata = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SaveError("Backup metadata missing or corrupt") from exc
    if metadata.get("schema") != 1 or metadata.get("id") != backup_id:
        raise SaveError("Backup metadata does not match selected backup")
    files = metadata.get("files")
    if not isinstance(files, list) or not 0 < len(files) <= MAX_FILES:
        raise SaveError("Backup file list is invalid")
    for entry in files:
        _safe_relative(entry.get("relative"))
        if not isinstance(entry.get("size"), int) or entry["size"] < 0:
            raise SaveError("Invalid backup size")
        if not isinstance(entry.get("sha256"), str) or not re.fullmatch("[a-f0-9]{64}", entry["sha256"]):
            raise SaveError("Backup hash is invalid")
    return directory, metadata


def list_backups(home: Path, appid: str = "",
                 cache_file: Path | None = None) -> list[dict]:
    if appid and (not isinstance(appid, str) or not APPID.fullmatch(appid)):
        raise SaveError("Invalid AppID filter")
    items, ids = [], set()
    for root in known_backup_roots(home, cache_file):
        if not root.is_dir() or root.is_symlink():
            continue
        for path in root.iterdir():
            if not ID_PATTERN.fullmatch(path.name) or path.name in ids:
                continue
            try:
                _, metadata = _load_backup(home, path.name, cache_file)
                if not appid or appid == metadata.get("appid"):
                    items.append({
                        **{key: val for key, val in metadata.items() if key != "files"},
                        "backup_folder": str(path.parent),
                    })
                    ids.add(path.name)
            except (SaveError, OSError):
                continue
            if len(items) >= MAX_SNAPSHOTS:
                break
        if len(items) >= MAX_SNAPSHOTS:
            break
    return sorted(items, key=lambda item: item.get("created_at", ""), reverse=True)


def _restore_target(home: Path, cache_file: Path, metadata: dict) -> Path:
    library, appid = metadata.get("library"), metadata.get("appid")
    if not isinstance(library, str) or not isinstance(appid, str) or not APPID.fullmatch(appid):
        raise SaveError("Invalid original backup destination")
    data = scan(home, cache_file)
    if data["missing_libraries"] or library not in data["libraries"]:
        raise SaveError("Original Steam library is offline or not registered")
    base = Path(library) / "steamapps/compatdata"
    if not base.is_dir() or base.is_symlink():
        raise SaveError("Proton compatdata parent folder missing or linked")
    target = base / appid
    if target.is_symlink() or (target.exists() and not target.is_dir()):
        raise SaveError("Unsafe prefix path")
    if _running_app_or_prefix(appid, target):
        raise SaveError("Close the game before restoring saves")
    return target


def preview_restore(home: Path, cache_file: Path, backup_id: str) -> dict:
    folder, metadata = _load_backup(home, backup_id, cache_file)
    prefix = _restore_target(home, cache_file, metadata)
    collisions = 0
    for entry in metadata["files"]:
        rel = _safe_relative(entry["relative"])
        dest = prefix / rel
        _no_link_parents(prefix, dest)
        if dest.exists():
            collisions += 1
    return {
        "ok": True, "id": backup_id, "name": metadata["name"],
        "appid": metadata["appid"], "count": metadata["count"],
        "bytes": metadata["bytes"], "conflicts": collisions,
        "created_at": metadata["created_at"],
        "message": "Restoring overwrites existing files." if collisions else "",
    }


def restore_backup(home: Path, cache_file: Path, backup_id: str) -> dict:
    """Restore after explicit confirmation; verify *all* hashes before writing."""
    folder, metadata = _load_backup(home, backup_id, cache_file)
    prefix = _restore_target(home, cache_file, metadata)
    # Validate all archived content before writing anything to the prefix.
    for entry in metadata["files"]:
        source = folder / "files" / _safe_relative(entry["relative"])
        _no_link_parents(folder, source)
        if source.is_symlink() or not source.is_file() or source.stat().st_size != entry["size"]:
            raise SaveError("Backup file is missing or modified")
        digest = hashlib.sha256()
        with source.open("rb") as reader:
            for block in iter(lambda: reader.read(1024 * 1024), b""):
                digest.update(block)
        if digest.hexdigest() != entry["sha256"]:
            raise SaveError("Backup checksum mismatch; nothing was restored")

    written = 0
    try:
        for entry in metadata["files"]:
            rel = _safe_relative(entry["relative"])
            source = folder / "files" / rel
            destination = prefix / rel
            _no_link_parents(prefix, destination)
            destination.parent.mkdir(parents=True, exist_ok=True)
            _no_link_parents(prefix, destination)
            with tempfile.NamedTemporaryFile(dir=destination.parent,
                                             prefix=".gamesweep-restore-",
                                             delete=False) as handle:
                temp_path = Path(handle.name)
                with source.open("rb") as reader:
                    shutil.copyfileobj(reader, handle, length=1024 * 1024)
            try:
                os.replace(temp_path, destination)
            finally:
                temp_path.unlink(missing_ok=True)
            written += 1
    except (OSError, SaveError) as exc:
        raise SaveError(
            "Restore incomplete: " + str(written) + " of " +
            str(len(metadata["files"])) + " files restored; " + str(exc)
        ) from exc
    return {"ok": True, "name": metadata["name"], "count": written, "id": backup_id}
