# Optional modes, extra maps and server connections

The same mode files work in Windows x64, Linux x86_64 and Mac ARM64 packages.
Fresh packages contain **72 maps**: all 67 original Slash maps plus `de_tuscan`,
`cs_mansion`, `awp_india`, `surf_ski_2` and `35hp_2`.

## Host a game with optional rules

Create a game and wait for the map to finish loading. In the `~` console:

| Command | Your hosted game |
| --- | --- |
| `mode_classic` | Original package rules; resets every optional mode setting |
| `mode_dm` | Team deathmatch, two-second respawn, armor and starting rifles |
| `mode_ffa` | Deathmatch with everyone against everyone |
| `mode_practice` | Respawn, unlimited reserve ammunition and buying anywhere |
| `mode_knives` | Knife rounds; purchasing and map weapons disabled |
| `mode_pistols` | Pistol rounds with Deagles; purchasing and map weapons disabled |
| `mode_surf` | Surf physics, no falling damage and respawn |
| `mode_climb` | Climbing practice without falling damage |
| `mode_bhop` | Automatic bunnyhop practice |
| `mode_help` | Show the host mode commands |

Selecting a mode restarts the current round. New hosted maps start in Classic;
select the desired mode after a map change. Classic restores this package's
Slash host rules, including friendly fire on. Bot count and difficulty are your
choice: `bot_add_ct`, `bot_add_t`, `bot_difficulty 0` through `3`, `bot_kick`.
Surf/climbing presets do not include checkpoint/timer plugins; bots are designed
for normal CS maps and may not navigate these movement maps successfully.

These are **host rules**. They do not install a client gameplay mod, change the
network protocol or automatically turn on when joining another server. A remote
server controls its own rules. To leave your game, `disconnect`, then connect to
the other server. Other players do not need your preset files to join a compatible
host. Use the matching native packages for the simplest cross-platform LAN setup.

## Upgrade an existing installation without downloading the full game again

Get [Optional-Features.zip](https://github.com/mhouten/cs16/releases/latest/download/Optional-Features.zip),
extract it, and quit the game. The add-on contains the portable presets,
`Extra-Maps.zip`, and a Python installer. Install [Python 3.12+](https://www.python.org/downloads/)
or use the manual copy steps below. Run commands from the extracted `Optional-Features` folder.

**Windows PowerShell** — point at the folder containing `cstrike` and `valve`:

```powershell
py -3 Rebuild/Scripts/install-features.py --game "C:\Games\Counter-Strike\Game" --map Extra-Maps.zip
```

**Linux:**

```sh
python3 Rebuild/Scripts/install-features.py --game /path/to/Counter-Strike/Game --map Extra-Maps.zip
```

**macOS:**

```sh
python3 Rebuild/Scripts/install-features.py \
  --mac-app /Applications/Counter-Strike-1.6-macos.app --map Extra-Maps.zip
```

The Mac installer writes to `~/Library/Application Support/Counter-Strike 1.6 Complete`,
keeping the signed application intact. Use `--userdir /path/to/profile` if you
launch the app with a custom `CS16_USERDIR`. Windows/Linux write into `Game/`.
The installer backs up changed startup/map-list files, keeps saved player settings
and existing map resources, and preserves your server bookmarks. It never
replaces client/game DLLs or menu artwork. Start the game again, then use `mode_help`.
It also restores the original HL Readme and CS Manual and prints the path to
`Documentation/index.html`. Open that file in your browser; the upstream menu's
Readme button is unfinished. A separate [documentation ZIP](https://github.com/mhouten/cs16/releases/latest/download/Documentation.zip)
can be read without running an installer.

## Manual installation without Python

Your writable `cstrike` directory is:

- Windows/Linux: the package's `Game/cstrike/`.
- Mac: `~/Library/Application Support/Counter-Strike 1.6 Complete/cstrike/`.
  If a startup file is not present there, first copy it from the app's
  `Contents/Resources/Game/cstrike/`, then edit the writable copy.

1. Copy `Rebuild/Features/cstrike/modes/` and `optional_modes.cfg` into it.
2. Copy `servers.cfg.example` as `servers.cfg` if you do not already have one.
3. Copy `Rebuild/Features/cstrike/userconfig.d/optional-features.cfg` into
   `cstrike/userconfig.d/` (create the folder if needed). The native engine runs
   this folder after saved client settings; `autoexec.cfg` alone is not reliable.
   The supplied file contains:

   ```text
   exec optional_modes.cfg
   exec servers.cfg
   ```

   If an older upgrade reports `Unknown command: mode_practice`, rerun the
   updated installer. For the current session, enter `exec optional_modes.cfg`,
   then `mode_practice` after hosting a map. Use `mode_classic` to reset.

4. Add `exec modes/_reset.cfg` at the beginning of both `server.cfg` and
   `listenserver.cfg`, before their existing commands. This resets host rules
   when a new map starts. It does not execute a mode from your client startup.
   Ensure `game_init.cfg` contains `bot_enable 1` so native bot settings exist.
5. Merge the `cstrike/` content of `Extra-Maps.zip` into the writable `cstrike/`.
   Keep existing files. Add these names to `mapcycle.txt` and add entries such as
   `de_tuscan "de_tuscan"` to `maps.lst`:

   ```text
   de_tuscan
   cs_mansion
   awp_india
   surf_ski_2
   35hp_2
   ```

More maps can be added with repeated `--map /path/to/map.zip` arguments to the
installer. It imports map resources, excludes native code/configs/menu skins,
and refreshes the full map list. Use [MAPS.md](MAPS.md) for public downloads.
For another source build, add `--extra-map /path/to/map.zip` to
`Rebuild/Scripts/package-slash.py`; repeat for each ZIP. Existing source assets
are preserved. The map add-on contains only the new resources needed by our
67-map packages; use the original map archives when assembling from Steam data.

## Join normal or old servers

A native Xash server:

```text
connect HOST_IP:27015
```

An older GoldSrc/Slash server:

```text
connect HOST_IP:27015 gs
```

Do not execute host presets while playing on somebody else's server. You do not
need its server plugins installed locally; its map/model/sound downloads may
still be needed. Client DLL replacement mods are a separate compatibility case.

For one-command bookmarks, add your own addresses to writable `cstrike/servers.cfg`:

```text
alias server_office "connect 192.168.1.50:27015 gs"
alias server_home "connect 192.168.1.51:27015"
```

Load with `exec servers.cfg`, then type `server_office` or `server_home`. They
load automatically on later launches. The installer can create a bookmark too:

```sh
python3 Rebuild/Scripts/install-features.py --game /path/to/Game \
  --bookmark office 192.168.1.50:27015 --protocol goldsrc
```

On Mac replace `--game` with `--mac-app /path/to/Counter-Strike-1.6-macos.app`;
on Windows use `py -3`. For a passworded server, enter `password YOUR_PASSWORD`
in your own console before connecting; do not put private passwords in this repo.

### Steam-authenticated GoldSrc servers

The native engine does not guarantee access to every old server. FWGS documents
[GoldSrc protocol support and server checks](https://github.com/FWGS/xash3d-fwgs/blob/master/Documentation/goldsrc-protocol-support.md).
Where Steam authentication is required, FWGS specifies a purchased Half-Life 1 account and the [official Steam broker](https://github.com/FWGS/steam-broker).
That broker currently supports Linux. With your own broker running, configure
its reachable address in the game:

```text
cl_ticket_generator steam
cl_steam_broker_addr YOUR_BROKER_IP:27420
connect HOST_IP:27015 gs
```

The broker uses one active session; it is not a shared login for a group of players.
Mac/Windows clients can target a broker on their own reachable Linux setup, but
this combination has not been tested in these packages. A server can still reject
Xash clients through its protocol/authentication/anti-cheat checks. Extra maps and
mode presets cannot change that. Servers rejecting this engine may require the
official Valve client; no config file can promise universal legacy compatibility.

## Full Zombie, GunGame and Deathrun mods

These are separate server plugin systems, not the native presets above. Traditional
AMX Mod X/Metamod modules target classic server architectures; the
[official installation guide](https://wiki.alliedmods.net/Installing_AMX_Mod_X_Manually)
specifies supported binaries and notes the old AMD64 limitation. Do not copy a
32-bit Windows DLL or Linux module into these native 64-bit/Mac ARM64 game folders.

A practical route is a separate supported Windows/Linux GoldSrc mod server:

1. Set up a clean dedicated server using [Valve SteamCMD](https://developer.valvesoftware.com/wiki/SteamCMD).
   Match the server architecture required by your selected plugin stack.
2. Install Metamod, then [AMX Mod X base and Counter-Strike addon](https://www.amxmodx.org/downloads-new.php),
   following the official installation guide.
3. Install one mode and all its resources, then follow its module/config instructions:

   | Mode | Original downloads/instructions |
   | --- | --- |
   | GunGame | [Download](https://gungame-amxx.org/download.php) / [Installation](https://gungame-amxx.org/installation.php) |
   | Zombie Plague | [MeRcyLeZZ's release](https://forums.alliedmods.net/showthread.php?t=72505) |
   | Deathrun | [xPaw's Deathrun Manager](https://forums.alliedmods.net/showthread.php?t=78197) |

4. `.amxx` plugins go in `cstrike/addons/amxmodx/plugins/`; enable them in
   `addons/amxmodx/configs/plugins.ini`. Put accompanying configs, translations,
   models and sounds in their provided paths. Check `meta list`, `amxx modules`
   and `amxx plugins` in the server console before inviting players.
5. Keep a clean normal server and separate mod server installations/ports, then
   create bookmarks for each. All three client ports can try those hosts with
   `connect HOST:PORT gs`; actual acceptance and each mod's client messages/assets
   need real server testing. Installing the plugins on every player's machine
   is not required for server-side mods.

For future native plugin development, see [Metamod-FWGS](https://github.com/FWGS/metamod-fwgs)
and [NodeMod](https://nodemod.org/docs/). They are not bundled or verified here;
they do not automatically run existing Pawn `.amxx` mods. Full local hosting of
these classic plugins on native Mac ARM64 would need a compatible port and tests.

## What was verified

Nine mode profiles and nine resets to Classic were checked by reading native
Mac server cvars, including the bot weapon restrictions. All 72 maps passed Mac
headless startup. Original map hashes, native libraries, upstream menus and the
provided app icon are preserved. This is not graphical play testing. Windows/Linux
execution, real legacy-server connections and the external plugin stacks still
need native testing. See [VERIFICATION.json](VERIFICATION.json).
