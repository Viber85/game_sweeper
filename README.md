# GameSweep

Decky Loader plugin for SteamOS Game Mode. **v0.3.0 has opt-in permanent cleanup**.
It scans Steam compatdata and shader cache, estimates storage usage, identifies
known Steam and Non-Steam entries, and allows deleting one verified directory at
a time only after an explicit confirmation.

v0.3.0 opens a real full-screen SteamOS route from a button in the Decky quick access panel. The Dashboard uses the actual filesystem capacity for a selected Steam library, a circular used/free disk meter, storage summaries, and expandable game results. The UI is gamepad-focusable and pressing B returns to Steam.

## Features
- Discover Steam libraries from Steam's libraryfolders.vdf (including microSD).
- Read appmanifest_*.acf, cache game names locally, and show friendly names beside AppIDs.
- Look up an unknown Steam AppID on Steam Store on demand (requires internet).
- Show per-game compatdata and shader cache sizes and paths.
- Mark installed games as protected, apparent leftovers as candidates (not safe to delete), and ambiguous / Non-Steam entries as needing review.
- Detect unavailable libraries and avoid guessing when a drive is disconnected.
- Check GitHub Releases and request updates via Decky Loader's own installer. Updates require the normal Decky confirmation prompt.
- Fullscreen Game Mode interface launched from a compact Decky Quick Access entry. Gamepad-focusable navigation and back/exit controls.

## Install
1. Install Decky Loader on SteamOS.
2. Open [GitHub Releases](https://github.com/Viber85/game_sweeper/releases) and download **GameSweep-v0.3.0.zip**.
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
- Steam AppID names are recovered offline from current manifests, from binary Non-Steam shortcuts.vdf files, optional shortcut backup files, and GameSweep's prior scans. Deleted shortcuts with no surviving evidence cannot always be named.
- Custom shortcuts, Proton launchers, Wine prefixes outside Steam libraries, and shared compatdata are not automatically classified as safe; active shortcuts are protected. No automatic deletion is performed.
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

## Update verification (v0.2.1)

- Fixed: the older version called `utilities/install_plugin` through the plugin-scoped `@decky/api.call`, which cannot access Loader utilities.
- Now uses Decky Loader's global WebSocket installer bridge `window.DeckyBackend.callable("utilities/install_plugin")`, with `install_type=2` (UPDATE). The Loader shows its standard confirmation prompt. The plugin does not self-overwrite.
- The old v0.2.0 updater could not reliably install v0.2.1. If you currently have v0.2.0 installed, install v0.2.1 manually **once** from this repository's GitHub Release ZIP. Later versions can use Settings -> Check for updates -> Install update.
- Verify on a real SteamOS device that the prompt appears, installation completes, and the newer version is shown; CI cannot test the actual Game Mode installation UI.

## Safe cleanup contract (v0.3.0)

- Delete individual **compatdata** or **shadercache** folders only; no bulk cleanup yet.
- The API accepts only a registered Steam library, decimal AppID, and allowed category.
- The backend verifies there is no installed game manifest or active Non-Steam shortcut for that AppID, and no offline Steam library.
- A preview pins the target directory device and inode; a short-lived, one-use token is required to execute.
- The execution re-scans all relevant Steam metadata and rejects a changed target or active process advertising the game / Proton prefix.
- Deletion uses a directory file descriptor and Python's symlink-attack-resistant rmtree. It refuses to proceed on platforms without the needed protection.
- **No backup, trash, or restore option exists.** A Proton prefix can contain unique saves and settings. Close running games first.
- Unidentified Non-Steam entries require careful manual verification; the app cannot infer ownership from AppID alone.
