# Portable project handoff

Updated 25 November 2026. This folder is the user's chosen project base.

## November 25 rebuild and GitHub downloads

Release `v2026.11.25` restores the README download URLs. The repository had no
GitHub release when the 404 was investigated. The three packages were rebuilt
from the original local Slash source and the same five extra maps, using the
official Xash3D FWGS release from November 24 (commit
`bc1b4515e1f61ebdb76465b498aec1bedde12217`) and CS16Client from November 23.
The lock file records the exact archives. All 4,960 shared game-content hashes
match the October build, including the 72 maps and 41 navigation files.

Use the latest `VERIFICATION.json` for this rebuild's test results. The October
sections below describe earlier builds and tests with the previous runtimes.

## Current product

Three playable native Counter-Strike 1.6 packages with default upstream
CS16Client/MainUI presentation, all original 67 Slash maps and 41 navigation files,
five additional public maps (72 total), compatible aliases/host rules, native bots,
nine optional host modes, and the supplied silver/soldier app icon.

- macOS: `Counter-Strike-1.6-macos.zip`, ARM64 / Apple Silicon, macOS 13+.
- Linux: `Counter-Strike-1.6-linux.tar.gz`, x86_64.
- Windows: `Counter-Strike-1.6-windows.zip`, x64.
- `README.md`: install/play instructions and manual rebuild recipes for all OSes.
- `Rebuild/` and `Rebuild-Kit.zip`: standalone builder/helper sources, icons,
  licenses, content manifest, runtime release lock, verification report.
- `Clean-Old-Mac-Installs.command`: optional clean-install migration helper.

The console readability update increased the new-install console default to
`con_fontscale "2"`, with automatic font selection (`con_fontnum "-1"`).
Existing saved settings take priority. In the installed game's console use:

```text
con_fontscale 2
host_writeconfig
```

Scale changes take effect live and are saved normally. The change belongs in
the default `config.cfg`; do not force it from autoexec on every launch.

## Source and build inputs

The packaged engine and client were checked on 25 November 2026. Exact archive
names, official download URLs and SHA256 values are in
`Rebuild/upstream-lock.json`. Check upstream again before describing these as the
latest continuous releases on a later date.

Slash's source was a local `cs-slash.rar` supplied by the user. Its original
download URL is unknown. The small rebuild kit does not contain a full game installation or engine
archives; it includes one fallback custom map (see the GitHub section below). Keep a separate copy of the source RAR, or provide
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
Large archives are excluded from Git and are delivered as GitHub Release assets
using `Rebuild/Scripts/publish-release.py`.

The builder now accepts `--source` (with the existing `--slash` alias). A Steam
folder containing `valve/` and `cstrike/` uses the public preset from
`Rebuild/Defaults/cstrike/`; original Slash inputs retain their existing behavior.
Steam saved `.cfg` files are excluded rather than imported into fresh packages.
Before the optional-mode update, public-source handling preserved all 4,898
baseline hashes. The optional-mode update intentionally adds files and adapts
startup files; the current shared inventory has 4,960 files after restoring
the original documentation.

`MAPS.md` and `Rebuild/map-sources.json` list the 42 extra maps. Public downloads
for `aim_map`, `kz_adv_underground`, and `kz_hauntedhouse_v1` were downloaded and
matched to the snapshot. Other variants have not been hash-verified. The old
`breakfloor_b5` listing reports all download servers offline, so the exact
454 KB map is included under `Rebuild/Maps/` with a raw GitHub URL. That file is
a shared game asset, not a saved user setting. Public inputs now allow a fresh
installation with all map names; exact old Steam/resource revisions can differ.

The initial GitHub source commit was
`b5e3ee587bf4e0c8feb20022639d606695a1fde0`. The October upload stopped at GitHub
authentication. The November session verified that the authenticated account has
push access. The workspace protects its `.git` path, so an isolated checkout is
used to commit and push the release metadata.

## Optional host modes and manual upgrade — 31 October 2026

The user requested optional features on all ports, manual upgrades for people
with older packages, and normal/legacy server joining alongside local modes.
All three updated local archives have 72 maps and shared optional presets:
`mode_classic`, `mode_dm`, `mode_ffa`, `mode_practice`, `mode_knives`,
`mode_pistols`, `mode_surf`, `mode_climb`, `mode_bhop`. `mode_help` / `join_help`
show commands. Client startup defines aliases and loads bookmarks only. Host
startup resets to Classic; selecting a mode restarts a round. A new hosted map
starts Classic again. Normal remote servers control their own rules.

Five added maps: de_tuscan, cs_mansion, awp_india, surf_ski_2, 35hp_2. Their public
archive URLs/digests are recorded in the map catalog and content manifest. All
67 original BSPs and all 41 original nav files are preserved. No native code or
upstream menu resources were replaced; the Mac app was re-signed for bundle data.

`Rebuild/Features/` contains the presets and descriptive JSON. The shared
`optional-features.py` module is used by the builder and `install-features.py`.
The builder accepts repeated `--extra-map` ZIPs. Map import preserves existing
assets and excludes executables, config scripts and menu art. Root
`Optional-Features.zip` is a small existing-installation upgrade with presets,
installer, map add-on and guide. Root `MODS.md` contains manual Python/copy steps,
bookmarks, Steam broker setup and external mod-server installation links.

Mac upgrades go into the writable Complete user profile, preserving the signed
app and saved config.cfg. This is also needed after swapping the app if older
writable startup files/map lists shadow new packaged defaults. Windows/Linux use
Game/. Changed startup/map-list files are backed up. Bookmarks are local aliases
in cstrike/servers.cfg; installer --bookmark NAME HOST:PORT --protocol goldsrc
creates server_NAME with the gs suffix. No addresses or passwords are auto-filled.

Validation: five upgrader/public-source unit tests; all nine native Mac mode
profiles and all nine transitions back to Classic checked via actual cvar
readback, including bot restrictions; zero unknown commands. All 72 maps passed
headless Mac startup with the final startup files. A standalone add-on upgraded
an existing 67-map Mac app through a user overlay, preserved custom config.cfg and
its signature, listed 72 maps and loaded a new map on that original engine.
All 4,954 shared hashes were checked across the final three archives; Mac strict
signature verified after extraction; Linux links/modes preserved. Graphical play,
Windows/Linux execution and real legacy/mod-server connections are still untested.

### Mode startup correction — 31 October

The user successfully installed the add-on, but shortcuts were not loaded:
the original installer depended on autoexec.cfg. The pinned engine's Host_Init
explicitly runs `userconfigd` after saved client configuration; the new shared
`cstrike/userconfig.d/optional-features.cfg` loads aliases and bookmarks there.
No mode or personal preference is applied by that startup file. The original
autoexec hook remains for compatibility. Do not rely on autoexec alone again.

Six unit tests pass. The native runtime test now exercises `userconfigd`, rather
than directly loading optional_modes.cfg, before checking all nine modes and
nine Classic resets. Both the new app and the actual installed /Applications
app with an isolated upgraded profile passed. These are headless dispatcher
checks, not graphical startup/gameplay tests. All 4,955 shared hashes are verified
across the updated archives, and the edited Mac bundle is re-signed.

The user's real profile cannot be written from this session. Updated extracted
`Optional-Features/` and Optional-Features.zip are synchronized. The user must
quit the game and rerun the same installer command, then reopen. No app reinstall
or settings deletion is needed. For the current session use
`exec optional_modes.cfg`, then `mode_practice` after hosting a map. The screenshot
also includes an optional missing overview warning for aim_map; it does not
explain missing mode shortcuts.

Critical limits: full Zombie/GunGame/Deathrun AMXX plugin hosting is not bundled
as a native preset. MODS.md gives a separate supported classic Windows/Linux
mod-server route, plus FWGS native plugin development links. Mac ARM64 local
classic-plugin hosting needs a compatible port; do not imply copying 32-bit
modules works. Old GoldSrc joining still uses connect HOST:PORT gs. Where Steam
authentication is needed, the official broker currently supports Linux; authentic
account ownership and server acceptance remain required. The user was asked for
a real Slash server address for connection testing; none has been supplied.

The local `WORK_STATE.json` tracks progress when memory tools are unavailable.

## Original documentation restoration — 31 October

User requested the default documents behind HL Readme and CS Manual. The original
root Half-Life readme (version 1.1.1.1, dated 12/2/02) was found in the supplied
source archive; CS manual/manual.htm was already in all packages. Their contents
are retained byte-for-byte under Rebuild/Documentation, with source hashes and
public fallback URLs in sources.json. These are historical documents, not current
native runtime instructions. Builder now also retains CSS in source manuals.

Important: MainUI's pinned readme button has no onReleased callback: see
Velaron/mainui_cpp commit 4922113b7477d9073e9f483f46b0e10b3be888b7,
menus/Main.cpp (the TODO before readme.SetNameAndStatus). Adding data does not
fix that button. Native menu/runtime binaries and artwork remain unmodified;
do not report the in-game documentation buttons as fixed or graphically tested.

Each package now includes a browser-readable Documentation folder beside its
launcher/app, with both original documents and an index. The same documents are
inside Game/Documentation, the original HL readme is at Game/readme.txt and
Game/valve/readme.txt, and the existing CS manual is retained. Root Documentation/
can be opened immediately; Documentation.zip is the small standalone download.
The optional installer adds these to a writable Mac profile without editing its
signed app. It prints the index path. This session cannot modify the real profile
or /Applications; user-run installation remains necessary there.

Validation: seven unit tests, all shared hashes across three package archives,
document links/content hashes, Linux runtime links/modes and Mac signature after
archive extraction. Current native mode/dispatcher checks passed again; the 72
earlier headless map checks cover unchanged maps/binaries. Graphical browser/menu
clicks, Windows/Linux execution and actual old-server connections remain untested.

## Linux portability branch

The Linux candidate is in `build/linux-portability/release/`. The old
November archive links Counter-Strike client and ReGameDLL libm imports to
`GLIBC_2.43`. Other engine, renderer, UI and SDL modules also exceed the
older ABI. AlmaLinux 8 and Debian 11 reproduced the old loader failure.

The candidate uses the pinned AlmaLinux 8 glibc 2.28 environment and source
revisions in `Rebuild/Linux/sources.json`. The stage and archive audits
passed for 19 ELF objects. All 4,960 shared files, 72 maps, 41 navs and both
resource PK3s match the previous package. The Linux launcher preserves
player arguments, and a separate writable profile supports read-only
installs. ReGameDLL resolves the packaged filesystem through its RUNPATH.

AlmaLinux 8, Debian 11, Ubuntu 20.04, Fedora 44 and Arch passed non-root
container startup checks. All 72 dedicated map startups, nine host modes,
nine Classic resets and a native bot join passed. Fedora virtual X11 and
Wayland passed local-game sign-on in windowed and fullscreen modes. The
X11 audio test captured nonzero PulseAudio samples. A client completed
sign-on to a second container over an isolated IPv4 LAN.

See `Rebuild/Linux/PORTABILITY.md` and the staged verification and checksum
reports. Physical desktops, input/audio hardware, LAN discovery and public
servers remain unverified. Git history is local on `fix/linux-portability`.
The archives in the project root still correspond to the November release.
