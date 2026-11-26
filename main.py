"""GameSweep v0.6.0 Decky backend with guarded opt-in cleanup."""
from __future__ import annotations

import asyncio
import json
import re
import ssl
from pathlib import Path
from time import monotonic
from uuid import uuid4
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import decky
import sys
sys.path.insert(0, str(Path(__file__).parent))
from scanner import read_cache, scan, write_cache
from cleanup import (CleanupError, preview_cleanup, execute_cleanup,
                     preview_all_cleanup, execute_all_cleanup)
from saves import (SaveError, preview_saves, create_backup, list_backups,
                   preview_restore, restore_backup, _select_game)
from backup_locations import (FolderError, browser as browse_backup_dirs,
                              choose_location, reset_location, location_status)
from manual_saves import (ManualSaveError, browse_game_save_folders,
                          select_manual_save_folder, clear_manual_save_folder)

VERSION = "0.8.0"
REPO = "Viber85/game_sweeper"



# Decky Python environments may not know the host CA trust store.
# Ship Mozilla's trusted CA roots (certifi) and continue checking both the
# server certificate chain AND the HTTPS hostname (no verify=False fallback).
TRUST_BUNDLE = Path(__file__).resolve().parent / "cacert.pem"


def _https_context() -> ssl.SSLContext:
    if TRUST_BUNDLE.is_file():
        return ssl.create_default_context(cafile=str(TRUST_BUNDLE))
    return ssl.create_default_context()


def _download_json(url: str):
    request = Request(url, headers={
        "User-Agent": "GameSweep/" + VERSION,
        "Accept": "application/vnd.github+json" if "api.github.com" in url else "application/json",
    })
    with urlopen(request, timeout=8, context=_https_context()) as response:
        if response.status != 200:
            raise RuntimeError("Server returned HTTP " + str(response.status))
        raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise RuntimeError("Metadata response too large")
        return json.loads(raw)



def _network_error(exc: Exception) -> str:
    reason = getattr(exc, "reason", exc)
    if isinstance(reason, ssl.SSLCertVerificationError) or "CERTIFICATE_VERIFY_FAILED" in str(exc):
        return (
            "Secure connection failed while verifying GitHub/Steam. "
            "Check SteamOS system date and time, network and HTTPS-intercepting proxies. "
            "TLS certificate verification is never disabled."
        )
    return str(exc)


def _version_key(value: str):
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", value.strip())
    return tuple(map(int, match.groups())) if match else None


def _github_update():
    releases = _download_json("https://api.github.com/repos/" + REPO + "/releases?per_page=15")
    if not isinstance(releases, list):
        raise RuntimeError("Invalid GitHub releases response")
    eligible = []
    for release in releases:
        if not isinstance(release, dict) or release.get("draft"):
            continue
        tag = release.get("tag_name", "")
        key = _version_key(tag)
        if not key or key <= _version_key(VERSION):
            continue
        for asset in release.get("assets", []):
            name = str(asset.get("name", ""))
            url = str(asset.get("browser_download_url", ""))
            if name == "GameSweep-" + tag + ".zip" and url.startswith(
                "https://github.com/" + REPO + "/releases/download/"
            ):
                digest = str(asset.get("digest", ""))
                sha256 = digest[7:] if re.fullmatch(r"sha256:[0-9a-fA-F]{64}", digest) else ""
                eligible.append({"version": tag, "url": url, "sha256": sha256, "notes": str(release.get("body", ""))[:800]})
    if eligible:
        return {"available": True, **max(eligible, key=lambda item: _version_key(item["version"]))}
    return {"available": False, "version": VERSION, "url": "", "notes": ""}


def _lookup_title(appid: str):
    # Steam Store AppID queries only; unknown Non-Steam AppIDs stay unknown.
    if not re.fullmatch(r"[0-9]{1,10}", appid) or int(appid) >= 2147483648:
        return None
    result = _download_json("https://store.steampowered.com/api/appdetails?appids=" + appid + "&filters=basic")
    obj = result.get(appid) if isinstance(result, dict) else None
    if not isinstance(obj, dict) or not obj.get("success"):
        return None
    data = obj.get("data")
    name = data.get("name") if isinstance(data, dict) else None
    return name[:180].strip() if isinstance(name, str) and name.strip() else None


class Plugin:
    async def _main(self):
        self.home = Path(decky.DECKY_USER_HOME)
        self.cache_path = Path(decky.DECKY_PLUGIN_SETTINGS_DIR) / "known_titles.json"
        self.lock = asyncio.Lock()
        self.pending_deletions = {}
        self.pending_restores = {}
        decky.logger.info("GameSweep %s ready (guarded cleanup)", VERSION)

    async def scan_storage(self):
        async with self.lock:
            return await asyncio.to_thread(scan, self.home, self.cache_path)

    async def resolve_name(self, appid: str):
        try:
            name = await asyncio.to_thread(_lookup_title, str(appid))
            if name:
                async with self.lock:
                    cache = read_cache(self.cache_path)
                    cache[str(appid)] = name
                    await asyncio.to_thread(write_cache, self.cache_path, cache)
                    type_file = self.cache_path.with_name("known_types.json")
                    types = read_cache(type_file)
                    types[str(appid)] = "steam"
                    await asyncio.to_thread(write_cache, type_file, types)
                return {"found": True, "name": name}
            return {"found": False, "name": ""}
        except (OSError, HTTPError, URLError, ValueError, RuntimeError) as exc:
            return {"found": False, "name": "", "error": _network_error(exc)}

    async def check_update(self):
        try:
            return await asyncio.to_thread(_github_update)
        except (OSError, HTTPError, URLError, ValueError, RuntimeError) as exc:
            return {"available": False, "version": VERSION, "url": "", "error": _network_error(exc)}

    async def prepare_cleanup(self, library: str, appid: str, kind: str,
                              allow_installed: bool = False):
        """Authorize installed-game data only when explicitly requested."""
        async with self.lock:
            try:
                if kind == "all":
                    selected = await asyncio.to_thread(
                        preview_all_cleanup, self.home, self.cache_path,
                        library, appid, allow_installed is True
                    )
                else:
                    selected = await asyncio.to_thread(
                        preview_cleanup, self.home, self.cache_path,
                        library, appid, kind, allow_installed is True
                    )
                now = monotonic()
                self.pending_deletions = {
                    key: value for key, value in self.pending_deletions.items()
                    if now - value[0] < 120
                }
                token = uuid4().hex
                self.pending_deletions[token] = (now, selected)
                return {
                    "ok": True, "token": token, "name": selected["name"],
                    "appid": selected["appid"], "library": selected["library"],
                    "kind": selected["kind"],
                    "status": selected["status"], "game_type": selected["game_type"],
                    "type_source": selected["type_source"],
                    "bytes": selected["bytes"],
                    "path": selected.get("target", ""),
                    "targets": [
                        {"kind": target["kind"], "path": target["target"],
                         "bytes": target["bytes"]}
                        for target in selected.get("targets", [])
                    ]
                }
            except (CleanupError, OSError, ValueError) as exc:
                return {"ok": False, "error": str(exc)}

    async def delete_storage(self, token: str, confirmation: str):
        """Permanently remove exactly the previewed folder after explicit consent."""
        async with self.lock:
            pending = self.pending_deletions.pop(token, None)
            if not pending or monotonic() - pending[0] > 120:
                return {"ok": False, "error": "Confirmation expired; preview again"}
            installed = pending[1]["status"] == "installed"
            expected = "PERMANENT_DELETE_INSTALLED" if installed else "PERMANENT_DELETE"
            if confirmation != expected:
                return {"ok": False, "error": "Explicit installed-game confirmation required"
                        if installed else "Explicit confirmation is required"}
            try:
                operation = (execute_all_cleanup
                             if pending[1]["kind"] == "all" else execute_cleanup)
                outcome = await asyncio.to_thread(
                    operation, self.home, self.cache_path, pending[1]
                )
                decky.logger.info("GameSweep removed %s from %s",
                                  outcome["kind"], pending[1]["appid"])
                return {"ok": True, **outcome}
            except (CleanupError, OSError, ValueError) as exc:
                decky.logger.warning("Cleanup refused or failed: %s", exc)
                return {"ok": False, "error": str(exc)}

    async def preview_save_backup(self, library: str, appid: str):
        async with self.lock:
            try:
                details = await asyncio.to_thread(
                    preview_saves, self.home, self.cache_path, library, appid
                )
                return details
            except (SaveError, OSError, RuntimeError, ValueError) as exc:
                return {"ok": False, "error": str(exc)}

    async def create_save_backup(self, library: str, appid: str):
        async with self.lock:
            try:
                result = await asyncio.to_thread(
                    create_backup, self.home, self.cache_path, library, appid
                )
                decky.logger.info("Saved %s files for game %s", result["count"], appid)
                return {"ok": True, **result}
            except (SaveError, OSError, RuntimeError, ValueError) as exc:
                decky.logger.warning("Save backup failed: %s", exc)
                return {"ok": False, "error": str(exc)}

    async def list_save_backups(self, appid: str = ""):
        async with self.lock:
            try:
                items = await asyncio.to_thread(list_backups, self.home, appid, self.cache_path)
                return {"ok": True, "backups": items}
            except (SaveError, OSError, RuntimeError, ValueError) as exc:
                return {"ok": False, "error": str(exc), "backups": []}

    async def prepare_save_restore(self, backup_id: str):
        async with self.lock:
            try:
                details = await asyncio.to_thread(
                    preview_restore, self.home, self.cache_path, backup_id
                )
                now = monotonic()
                self.pending_restores = {
                    key: value for key, value in self.pending_restores.items()
                    if now - value[0] < 120
                }
                token = uuid4().hex
                self.pending_restores[token] = (now, backup_id)
                return {**details, "token": token}
            except (SaveError, OSError, RuntimeError, ValueError) as exc:
                return {"ok": False, "error": str(exc)}

    async def restore_save_backup(self, token: str, confirmation: str):
        if confirmation != "RESTORE_OVERWRITE":
            return {"ok": False, "error": "Restore requires explicit confirmation"}
        async with self.lock:
            pending = self.pending_restores.pop(token, None)
            if not pending or monotonic() - pending[0] > 120:
                return {"ok": False, "error": "Restore confirmation expired"}
            try:
                result = await asyncio.to_thread(
                    restore_backup, self.home, self.cache_path, pending[1]
                )
                decky.logger.info("Restored %s save files for %s",
                                  result["count"], pending[1])
                return result
            except (SaveError, OSError, RuntimeError, ValueError) as exc:
                decky.logger.warning("Save restore refused: %s", exc)
                return {"ok": False, "error": str(exc)}

    async def get_backup_location(self):
        async with self.lock:
            try:
                return await asyncio.to_thread(
                    location_status, self.home, self.cache_path
                )
            except (FolderError, OSError, ValueError) as exc:
                return {"ok": False, "error": str(exc)}

    async def browse_backup_folders(self, path: str = ""):
        async with self.lock:
            try:
                return await asyncio.to_thread(browse_backup_dirs, self.home, path)
            except (FolderError, OSError, ValueError) as exc:
                return {"ok": False, "error": str(exc)}

    async def choose_backup_location(self, path: str):
        async with self.lock:
            try:
                return await asyncio.to_thread(
                    choose_location, self.home, self.cache_path, path
                )
            except (FolderError, OSError, ValueError) as exc:
                return {"ok": False, "error": str(exc)}

    async def reset_backup_location(self):
        async with self.lock:
            try:
                return await asyncio.to_thread(
                    reset_location, self.home, self.cache_path
                )
            except (FolderError, OSError, ValueError) as exc:
                return {"ok": False, "error": str(exc)}

    async def browse_save_folders(self, library: str, appid: str,
                                  relative: str = ""):
        async with self.lock:
            try:
                game = await asyncio.to_thread(
                    _select_game, self.home, self.cache_path, library, appid
                )
                return await asyncio.to_thread(
                    browse_game_save_folders, Path(game["prefix_path"]), relative
                )
            except (SaveError, ManualSaveError, OSError, ValueError) as exc:
                return {"ok": False, "error": str(exc)}

    async def choose_save_folder(self, library: str, appid: str,
                                 relative: str):
        async with self.lock:
            try:
                game = await asyncio.to_thread(
                    _select_game, self.home, self.cache_path, library, appid
                )
                return await asyncio.to_thread(
                    select_manual_save_folder, self.cache_path, library,
                    appid, Path(game["prefix_path"]), relative
                )
            except (SaveError, ManualSaveError, OSError, ValueError) as exc:
                return {"ok": False, "error": str(exc)}

    async def reset_save_folder(self, library: str, appid: str):
        async with self.lock:
            try:
                await asyncio.to_thread(
                    clear_manual_save_folder, self.cache_path, library, appid
                )
                return {"ok": True}
            except (ManualSaveError, OSError, ValueError) as exc:
                return {"ok": False, "error": str(exc)}

    async def _unload(self):
        self.pending_deletions.clear()
        self.pending_restores.clear()
