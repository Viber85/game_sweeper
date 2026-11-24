# GameSweep v0.6.0

GameSweep is a fullscreen Decky Loader storage manager for SteamOS Game Mode.

## What's new in v0.6.0

- **Full four-way controller navigation** uses Steam's native `vgp_ondirection` / `BTakeFocus` focus system: D-pad or left analog moves up/down/left/right. A selects; B exits fullscreen or dismisses the confirmation dialog. The sidebar, results and confirmation modal are navigable without touch or mouse.
- New **Delete entire game data (prefix + shaders)** action appears when both compatdata and shader cache folders are present. Both paths and their combined estimated size are displayed in **one** irreversible-deletion confirmation. It does NOT uninstall the main game.
- Before combined deletion, both targets are checked: owner/status, Steam libraries, running processes and stable inodes. Any mismatch rejects the operation before deleting either. A filesystem error in the second removal can leave the first deleted; GameSweep explicitly reports partial deletion and requires a rescan.

### Safety of combined deletion

The action permanently removes all **GameSweep-managed game data** within that Steam library for the AppID: `steamapps/compatdata/<AppID>` and `steamapps/shadercache/<AppID>`. It does not delete Steam's game installation, downloads, external Wine prefixes, Steam Cloud data or other locations. Locally saved progress in compatdata may be lost. There is no undo or backup. Close the game first.

### Controller controls

| Control | Action |
|---|---|
| D-pad or left analog ↑ ↓ ← → | Move between sidebar, filters, game rows and action buttons |
| A | Select/activate the highlighted control |
| B | Exit fullscreen; close confirmation dialog if open |
| Right analog | Steam-native scrolling of long content when supported |

For unsupported versions of Steam's native focus tree, the handler leaves the event to Steam's default navigation rather than swallowing inputs.

## Previously available features

- Selecting GameSweep from Decky's Quick Access menu **opens the fullscreen route directly**. There is no separate "Open fullscreen" button.
- Every scan result is labelled **Steam**, **Non-Steam**, or **Unknown source**, with source filters alongside status filters.
- Active Steam game manifests and Non-Steam `shortcuts.vdf` entries determine type. The last verified type is cached for use after uninstall/removal; unknown numbers are **never** guessed to be Non-Steam merely because they are large.
- **Installed-game data can be deleted too**, but only with an explicit installed-game override and two separate on-screen acknowledgements. The Python backend requires a different, stronger confirmation token for installed entries.
- Existing protections remain: re-scan before deleting, no arbitrary paths, blocked offline libraries, stable device+inode, symbolic-link protection, checks for running games and short-lived single-use confirmation tokens.

**Important:** GameSweep removes only the selected game's **compatdata (Proton prefix)** or **shader cache** directory. **It does NOT uninstall the actual game or remove its main installation files.** Deleting an installed game's compatdata can permanently erase local saves, configuration, or launcher data. Games may recreate the data the next time they run.

## Installation

1. Install Decky Loader on SteamOS.
2. Download **GameSweep-v0.6.0.zip** from [GitHub Releases](https://github.com/Viber85/game_sweeper/releases).
3. In Decky developer settings, select **Install Plugin from ZIP File** and choose the downloaded release ZIP.
4. Select GameSweep in the Decky menu; it automatically enters fullscreen.
5. Open **Settings → Check for updates** to check GitHub Releases for future versions.

Use the **Release asset ZIP**, not GitHub's automatically generated source ZIP.

## Storage scan

- Detects installed Steam libraries on SSD, microSD and registered drives.
- Compares `steamapps/appmanifest_*.acf` with `compatdata` and `shadercache`.
- Parses binary `userdata/<id>/config/shortcuts.vdf` across Steam profiles for active Non-Steam entries and optional backup files for historical names.
- Caches known names and proven source types; a missing shortcut or manifest alone never proves a prefix is unused.
- Presents totals, disk usage rings, prefix/cache sizes, known game names and AppIDs.
- Entries with missing evidence are shown as **Unknown source**, not mislabelled.
- Reports inaccessible Steam libraries and refuses deletion while a registered library is offline.

## Deletion safety

1. Open a game row and choose **Delete compatdata** or **Delete shader cache**. Both are separate operations.
2. Review the folder path, selected data type, source, size and status.
3. Acknowledge permanent data loss.
4. If the game is installed, explicitly acknowledge **the game is still installed** in a second control.
5. Confirm permanent deletion. The backend re-checks current Steam metadata and directory identity before removing exactly the selected directory.

Save-only backup and restore are supported for recognized Proton games; no full-prefix backup, recycle bin, or restoration of deleted game installations exists. Close games and launchers before cleaning. The running-process check is best effort, so do not depend on it alone. The UI has **no bulk or unattended cleanup**.

## Updating

GameSweep checks `Viber85/game_sweeper` GitHub Release assets and asks Decky Loader to install the update through Decky's own installer. Releases include Mozilla's trusted CA certificate bundle (certifi) to verify HTTPS without disabling certificate checks.

## Developing

Requires Node.js 22+, npm and Python 3.10+.

```bash
npm install
npm run typecheck
npm run build
python -m unittest discover -s tests -v
```

GitHub Actions builds the plugin ZIP, runs frontend and backend tests and creates a versioned prerelease. It includes the bundled CA root certificates and license.

**Limitations:** Identification and cleanup depend on Steam metadata that may be incomplete, especially for deleted Non-Steam shortcuts. Automatic tests do not prove that the Game Mode navigation works on every Decky Loader version. Fullscreen auto-navigation, controller focus and installed-game removal should be tested on a real SteamOS device using disposable non-essential data first.

## Save Backup Manager (v0.6.0)

Only SAVE files are included: GameSweep does not back up whole Proton prefixes, game installs or shader caches.

- Open a game row and choose **Backup Saves** to preview discovered save files, sizes and source paths.
- Save detection uses an offline, save-tagged subset of Ludusavi Manifest by Steam AppID or exact known title.
- Steam and Non-Steam games in Proton Windows prefixes are supported when the rules match.
- Backups live outside the plugin at ~/.local/share/GameSweep/save-backups and survive plugin updates.
- Save Backups sidebar shows snapshots and lets you restore them after confirming possible overwrites.
- Saved files are SHA-256 verified before restoring; games must be closed.
- The prefix and combined-delete confirmation offer **Back up saves before deleting**.
- No match does NOT mean that the game has no saves. Empty backups are never created.
- Native Linux, registry-only, external Wine prefix, and Steam Cloud-only save locations are not supported yet.
- Restore is file-by-file, not transactional; an interrupted restore can be partial, but the backup remains untouched.
- Only explicitly save-tagged Ludusavi paths are bundled; the full Ludusavi detection engine is not implemented.
- Ludusavi Manifest is distributed under MIT license; see SAVE-RULES-LICENSE inside the release ZIP.
