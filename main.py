"""GameSweep v0.3.1 Decky backend with guarded opt-in cleanup."""
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
from cleanup import CleanupError, preview_cleanup, execute_cleanup

VERSION = "0.3.1"
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
                return {"found": True, "name": name}
            return {"found": False, "name": ""}
        except (OSError, HTTPError, URLError, ValueError, RuntimeError) as exc:
            return {"found": False, "name": "", "error": _network_error(exc)}

    async def check_update(self):
        try:
            return await asyncio.to_thread(_github_update)
        except (OSError, HTTPError, URLError, ValueError, RuntimeError) as exc:
            return {"available": False, "version": VERSION, "url": "", "error": _network_error(exc)}

    async def prepare_cleanup(self, library: str, appid: str, kind: str):
        """Issue a short-lived, single-use confirmation token for one directory."""
        async with self.lock:
            try:
                selected = await asyncio.to_thread(
                    preview_cleanup, self.home, self.cache_path, library, appid, kind
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
                    "appid": selected["appid"], "kind": selected["kind"],
                    "status": selected["status"], "bytes": selected["bytes"],
                    "path": selected["target"]
                }
            except (CleanupError, OSError, ValueError) as exc:
                return {"ok": False, "error": str(exc)}

    async def delete_storage(self, token: str, confirmation: str):
        """Permanently remove exactly the previewed folder after explicit consent."""
        if confirmation != "PERMANENT_DELETE":
            return {"ok": False, "error": "Explicit confirmation is required"}
        async with self.lock:
            pending = self.pending_deletions.pop(token, None)
            if not pending or monotonic() - pending[0] > 120:
                return {"ok": False, "error": "Confirmation expired; preview again"}
            try:
                outcome = await asyncio.to_thread(
                    execute_cleanup, self.home, self.cache_path, pending[1]
                )
                decky.logger.info("GameSweep removed %s from %s",
                                  outcome["kind"], pending[1]["appid"])
                return {"ok": True, **outcome}
            except (CleanupError, OSError, ValueError) as exc:
                decky.logger.warning("Cleanup refused or failed: %s", exc)
                return {"ok": False, "error": str(exc)}

    async def _unload(self):
        self.pending_deletions.clear()
