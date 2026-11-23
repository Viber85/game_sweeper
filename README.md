# GameSweep

Decky Loader plugin for SteamOS Game Mode. **v0.1.0 is read-only**:
it scans Steam compatdata and shader cache, estimates storage use, and labels
installed games and possible leftovers. It cannot delete files.

## Features
- Discover Steam libraries from Steam's libraryfolders.vdf (including microSD).
- Read appmanifest_*.acf, cache game names locally, and show friendly names beside AppIDs.
- Look up an unknown Steam AppID on Steam Store on demand (requires internet).
- Show per-game compatdata and shader cache sizes and paths.
- Mark installed games as protected, apparent leftovers as candidates (not safe to delete), and ambiguous / Non-Steam entries as needing review.
- Detect unavailable libraries and avoid guessing when a drive is disconnected.
- Check GitHub Releases and request updates via Decky Loader's own installer. Updates require the normal Decky confirmation prompt.
- Gamepad-focusable Quick Access interface.

## Install
1. Install Decky Loader on SteamOS.
2. Open [GitHub Releases](https://github.com/Viber85/game_sweeper/releases) and download **GameSweep-v0.1.0.zip**.
3. In Decky developer options, select **Install Plugin from ZIP File**, then choose the downloaded ZIP.
4. Open GameSweep from the Decky Quick Access menu; scan your libraries.
5. Use **Settings & updates -> Check GitHub updates** to check for and install future versions.

If no ZIP appears in Releases, enable **Actions** for this repository and run **Build & publish GameSweep preview** manually. The first run must finish successfully before a Decky-installable ZIP exists.

The ZIP includes a top-level **GameSweep/** plugin folder. Do not install GitHub's automatic source-code ZIP.

## Build from source
Requires Node.js 22+ and npm.

    npm install
    npm run build
    python -m unittest discover -s tests -v

Decky plugin files are main.py, scanner.py, plugin.json, package.json and dist/index.js.

## Current safety limitations
- **No cleanup or deletion capability in v0.1.0.** The "possible leftover" label is informational, not a safety verdict.
- Steam AppID names are recovered offline from current manifests and from GameSweep's prior scans; unknown removed games may require Steam Store lookup.
- Custom shortcuts, Proton launchers, Wine prefixes outside Steam libraries, and shared compatdata are deliberately not automatically classified as safe.
- If a Steam library path is offline, entries without a manifest are marked **Needs review**.
- Scan file sizes are estimates and may take some time on large prefixes.
- Steam may keep data for games that are not currently installed.

## GitHub update workflow
The GitHub Actions workflow builds and tests on each push to main, publishes the ZIP
as an Actions artifact, and creates the matching prerelease if not yet published.
The app checks the repository's GitHub Release ZIP assets. It does not overwrite its
own files or execute downloaded scripts.

Next steps: improve metadata identification for Non-Steam games and add carefully
reviewed backup and cleanup flows.
