"""Build an offline, save-only index from Ludusavi's official manifest.

Run at release packaging time; PyYAML is a *build dependency only*.
Skip registry and non-save paths. This is a subset of Ludusavi's capabilities,
not a replacement for Ludusavi's complete detection/restore engine.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import yaml

SUPPORTED = (
    "<winAppData>", "<winLocalAppData>", "<winLocalAppDataLow>",
    "<winDocuments>", "<home>", "<winPublic>", "<winProgramData>",
)
PLACEHOLDERS = re.compile(r"<[^>]+>")
MAX_PATHS_PER_GAME = 150


def normalize_title(name: str) -> str:
    return " ".join(name.casefold().split())


def allowed_path(path: str, info: dict) -> bool:
    if not isinstance(path, str) or len(path) > 380:
        return False
    path = path.replace("\\", "/")
    if not path.startswith(SUPPORTED) or ".." in path.split("/"):
        return False
    if any(place != "<osUserName>" for place in PLACEHOLDERS.findall(path)
           if place not in SUPPORTED):
        return False
    if not isinstance(info, dict):
        return False
    tags = info.get("tags")
    if not isinstance(tags, list) or "save" not in tags:
        return False
    constraints = info.get("when", [])
    if isinstance(constraints, list) and constraints:
        # Save paths declared exclusively for Linux/macOS installs aren't
        # valid for Windows Proton prefixes.
        if all(isinstance(cond, dict) and cond.get("os") in ("linux", "mac")
               for cond in constraints):
            return False
    return True


def compile_manifest(raw: dict, enforce_minimum: bool = True) -> dict:
    steam: dict[str, list[str]] = {}
    names: dict[str, list[str]] = {}
    conflicts: set[str] = set()
    if not isinstance(raw, dict):
        raise ValueError("Ludusavi YAML must be a mapping")
    for title, info in raw.items():
        if not isinstance(title, str) or not isinstance(info, dict):
            continue
        paths = list(dict.fromkeys(
            str(path).replace("\\", "/")
            for path, detail in info.get("files", {}).items()
            if allowed_path(path, detail)
        ))[:MAX_PATHS_PER_GAME]
        if not paths:
            continue
        steam_id = info.get("steam", {}).get("id")
        other_ids = info.get("id", {}).get("steamExtra", [])
        for value in [steam_id, *(other_ids if isinstance(other_ids, list) else [])]:
            if isinstance(value, int) and value > 0:
                steam[str(value)] = paths
        key = normalize_title(title)
        if key in names and names[key] != paths:
            conflicts.add(key)
        else:
            names[key] = paths
    for key in conflicts:
        del names[key]
    if enforce_minimum and len(names) < 1000:
        raise RuntimeError("Too few save-tagged rules; manifest may be invalid")
    return {"schema": 1, "source": "Ludusavi Manifest", "by_steam_id": steam,
            "by_name": names}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    with args.manifest.open("r", encoding="utf-8") as handle:
        raw = yaml.load(handle, Loader=getattr(yaml, "CSafeLoader", yaml.SafeLoader))
    result = compile_manifest(raw)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")),
                           encoding="utf-8")
    print("Save-only rules:", len(result["by_steam_id"]), "Steam IDs,",
          len(result["by_name"]), "unique titles;",
          args.output.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
