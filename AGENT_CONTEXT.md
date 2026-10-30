# Portable project handoff

Updated 31 October 2026. This folder is the user's chosen project base.

## Current product

Three playable native Counter-Strike 1.6 packages with default upstream
CS16Client/MainUI presentation, all 67 CS maps and 41 navigation files from the
user's Slash archive, compatible buy/demo aliases and gameWARE host rules, native
bots, and the user's high-resolution silver/soldier app icon.

- macOS: `Counter-Strike-1.6-macos.zip`, ARM64 / Apple Silicon, macOS 13+.
- Linux: `Counter-Strike-1.6-linux.tar.gz`, x86_64.
- Windows: `Counter-Strike-1.6-windows.zip`, x64.
- `README.md`: install/play instructions and manual rebuild recipes for all OSes.
- `Rebuild/` and `Rebuild-Kit.zip`: standalone builder/helper sources, icons,
  licenses, content manifest, runtime release lock, verification report.
- `Clean-Old-Mac-Installs.command`: optional clean-install migration helper.

The latest change increases the new-install console default to
`con_fontscale "2"`, with automatic font selection (`con_fontnum "-1"`).
Existing saved settings take priority. In the installed game's console use:

```text
con_fontscale 2
host_writeconfig
```

Scale changes take effect live and are saved normally. The change belongs in
the default `config.cfg`; do not force it from autoexec on every launch.

## Source and build inputs

The engine release was checked on 30 October 2026: Xash3D FWGS continuous commit
`3daa67eca9a9f9651b37d63babe6dfc8ec6961ac`. CS16Client continuous release was
published 23 October 2026. Exact archive names, official download URLs and SHA256
values are in `Rebuild/upstream-lock.json`. Do not describe these as freshly
checked latest releases after that date without verifying upstream again.

Slash's source was a local `cs-slash.rar` supplied by the user. Its original
download URL is unknown. The small rebuild kit does not contain the proprietary
game data or engine archives. Keep a separate copy of the source RAR, or provide
an extracted source folder containing `cstrike/` and `valve/`. The playable
packages contain the assembled game content. They work without the old parent
workspace. Exact source rebuilding requires the external inputs documented in
`README.md`; do not imply the small kit alone contains everything.

The builder entry point from this root is `Rebuild/Scripts/package-slash.py`.
It expects Python 3.12+, Go for Windows packaging, 7-Zip/libarchive for archive
extraction, and macOS developer tools plus a portable FreeType dylib for Mac.
Run `--help` and follow the README. Use fresh work/output directories.

## Decisions to preserve

An earlier release copied Slash menu artwork. The user explicitly replaced
that requirement with **default native menus and all compatible Slash gameplay
content**. Do not restore Slash menu branding. Default upstream Create Game art
may look old-fashioned; that alone does not indicate a missing replacement.
Original Windows VGUI binaries cannot be copied into a native Mac/Linux app.

Preserved host rules: friendly fire on, 5-second freeze, 1.75-minute rounds,
35-second bomb timer, $800 start money, team balance off. No fixed RCON password.
Console enabled, touch input off, graphical buy menus enabled. Native bots are
enabled before GameDLL initialization in `game_init.cfg`, but not automatically
spawned. Host a map, join a team, then `bot_add_ct` / `bot_add_t`.

Legacy Windows GoldSrc binaries, Steam emulator, HLTV utilities, DLLs and Windows
anti-cheat integrations are excluded from native runtime packages. Compatible
assets and scripts are retained. No guarantee of legacy demo/server support.

## Validation and limits

The baseline release passed all 67 native Mac headless map startups, client/menu
library loading, and deep strict app signature checks, including after ZIP
extraction. All 4,898 shared content files were hash-verified across the three
packages; all 67 BSPs match Slash. Native architectures, Windows icon embedding,
Linux symlinks/executable bits, original upstream menu archives and supplied
icons were checked. Standalone data rebuilding reproduced the content exactly.

For the console update, all 4,898 shared hashes were rechecked in each final
archive, ZIP integrity and Linux runtime symlinks/modes passed, and the Mac app
passed deep strict signature verification after final ZIP extraction. Only
`cstrike/config.cfg` changed in shared game content. `VERIFICATION.json` records
the results. The engine binaries and maps were not changed. Earlier
67-map results describe that unchanged baseline; they are not graphical tests.
Graphical console appearance/gameplay, Windows/Linux execution and mixed-OS LAN
have not been tested by the agent. The user reports the Mac game runs.

37 supplied navigation files report map-version mismatch warnings. Bots can be
added on `de_dust2`; navigation elsewhere may need `bot_nav_analyze`. Keep the
source navigation files; do not claim every route is correct.

## Multiplayer compatibility

All players using these matching native packages avoids differing engine
implementations. Colleagues using the old Slash Windows release have GoldSrc,
so authentication/protocol/server checks can reject connections. Not tested.
To try joining their host: `connect HOST_IP:27015 gs`. Start on `de_dust2`.
Ask for the exact rejection message if it fails; never promise interoperability
from copied maps alone. Official protocol documentation is linked in README.

## Mac installation and pending user action

App identity: `local.counterstrike.complete`. Writable settings:
`~/Library/Application Support/Counter-Strike 1.6 Complete`.
`CS16_USERDIR` overrides this path for isolated tests. Packaged game data is
read-only through `XASH3D_RODIR`; user settings/saves go in `XASH3D_BASEDIR`.

Older workspace launchers were retired. A previous 25-map menu report came from
launching an old installation: its filesystem symlink pointed at the old clean
app. The Slash app itself contained all 67 maps. Always open the exact current
app and replace stale Dock shortcuts.

The agent could not write old settings in `~/Library` due to sandbox policy.
The user-run cleanup helper was provided; completion has not been confirmed.
It also targets the current app/settings, so run it **before** a clean install,
not as a font-size fix. An installed app was seen in `/Applications` on 31
October. For font size use the console commands without clearing settings.

Future agents should keep working context here. Do not require the old parent
directory, old temporary build paths, or memory service to understand this folder.

## GitHub publication and independent source rebuilding

The user requested `git@github.com:mhouten/cs16.git`, all three OS packages in
GitHub Releases, and a concise README with public downloads and independent
rebuild steps. The repository was public and empty when checked on 31 October.
Large archives stay local and are excluded from Git; publish them as release
assets under `v2026.10.31` using `Rebuild/Scripts/publish-release.py`.

The builder now accepts `--source` (with the existing `--slash` alias). A Steam
folder containing `valve/` and `cstrike/` uses the public preset from
`Rebuild/Defaults/cstrike/`; original Slash inputs retain their existing behavior.
Steam saved `.cfg` files are excluded rather than imported into fresh packages.
`test_public_source.py` passes and the original Slash data preparation still
reproduces all 4,898 baseline shared hashes exactly. Published game archives have
not changed during this repository preparation.

`MAPS.md` and `Rebuild/map-sources.json` list the 42 extra maps. Public downloads
for `aim_map`, `kz_adv_underground`, and `kz_hauntedhouse_v1` were downloaded and
matched to the snapshot. Other variants have not been hash-verified. The old
`breakfloor_b5` listing reports all download servers offline, so the exact
454 KB map is included under `Rebuild/Maps/` with a raw GitHub URL. That file is
a shared game asset, not a saved user setting. Public inputs now allow a fresh
installation with all map names; exact old Steam/resource revisions can differ.

GitHub publication remains pending until authenticated transport succeeds.
This session initially had no `gh` login or GitHub token, and SSH resolution
failed. The user was asked to run `gh auth login --hostname github.com
--git-protocol ssh --web` in Terminal. Do not claim a pushed commit or a
published release without checking the remote. The workspace protects its `.git`
path; an isolated temporary checkout is used for publishing, without changing
that protected path.
