"""GameSweep v0.2.0 Decky backend. Read-only for Steam storage."""
from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import decky
import sys
sys.path.insert(0, str(Path(__file__).parent))
from scanner import read_cache, scan, write_cache

VERSION = "0.2.0"
REPO = "Viber85/game_sweeper"


def _download_json(url: str):
    request = Request(url, headers={
        "User-Agent": "GameSweep/" + VERSION,
        "Accept": "application/vnd.github+json" if "api.github.com" in url else "application/json",
    })
    with urlopen(request, timeout=8) as response:
        if response.status != 200:
            raise RuntimeError("Server returned HTTP " + str(response.status))
        raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise RuntimeError("Metadata response too large")
        return json.loads(raw)


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
        decky.logger.info("GameSweep %s ready (read-only)", VERSION)

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
            return {"found": False, "name": "", "error": str(exc)}

    async def check_update(self):
        try:
            return await asyncio.to_thread(_github_update)
        except (OSError, HTTPError, URLError, ValueError, RuntimeError) as exc:
            return {"available": False, "version": VERSION, "url": "", "error": str(exc)}

    async def _unload(self):
        pass
