# Counter-Strike 1.6

Native Windows, Linux and macOS packages with default menus, 67 maps, bots,
LAN hosting and readable console text.

## Downloads

| System | Package | Run |
| --- | --- | --- |
| Windows x64 | [Windows ZIP](https://github.com/mhouten/cs16/releases/latest/download/Counter-Strike-1.6-windows.zip) | Extract; open `Counter-Strike.exe` |
| Linux x86_64 | [Linux tar.gz](https://github.com/mhouten/cs16/releases/latest/download/Counter-Strike-1.6-linux.tar.gz) | Extract; run `./Play` |
| macOS 13+, Apple Silicon | [macOS ZIP](https://github.com/mhouten/cs16/releases/latest/download/Counter-Strike-1.6-macos.zip) | Extract; open the `.app` |

[All releases](https://github.com/mhouten/cs16/releases) ·
[Checksums](https://github.com/mhouten/cs16/releases/latest/download/SHA256SUMS.txt) ·
[Small rebuild kit](https://github.com/mhouten/cs16/releases/latest/download/Rebuild-Kit.zip)

Windows may need [Visual C++ x64](https://aka.ms/vc14/vc_redist.x64.exe).
Keep `Game` beside the Windows/Linux launcher. Copy the Mac app to `/Applications`.

## Build from Steam and public maps, without our game packages

1. Install your owned [Counter-Strike on Steam](https://store.steampowered.com/app/10/).
   Its `steamapps/common/Half-Life/` folder supplies `cstrike/` and `valve/`.
2. Get the [42 custom maps](MAPS.md). Merge each archive's `maps/`, `models/`,
   `sound/`, `gfx/`, `sprites/` and `.wad` files into `cstrike/`, preserving paths.
   One old map's mirror is offline; its small BSP is hosted in this repository.
3. Install [Python 3.12+](https://www.python.org/downloads/),
   [Go](https://go.dev/dl/) for Windows packaging, and
   [7-Zip](https://www.7-zip.org/download.html) or libarchive for extraction.
4. Get the small builder sources: `git clone https://github.com/mhouten/cs16.git`.
   Run these commands from the cloned `cs16` folder. No finished game package
   or private Slash archive is needed for this route.

**Mac: build all three packages.** Install Xcode Command Line Tools and
[FreeType](https://formulae.brew.sh/formula/freetype):

```sh
xcode-select --install
brew install freetype
python3 Rebuild/Scripts/package-slash.py --source /path/to/Half-Life \
  --fetch --platforms macOS Linux Windows \
  --freetype "$(brew --prefix freetype)/lib/libfreetype.6.dylib" \
  --work Rebuild/build/all --output Rebuild/output
```

**Linux:** install `libarchive-tools` and your distribution's libarchive package.

```sh
python3 Rebuild/Scripts/package-slash.py --source /path/to/Half-Life \
  --fetch --platforms Linux --work Rebuild/build/linux --output Rebuild/output-linux
```

**Windows PowerShell:** install Go/7-Zip and reopen the shell.

```powershell
$env:Path += ";C:\Program Files\7-Zip"
py -3 Rebuild/Scripts/package-slash.py --source "C:\path\to\Half-Life" --fetch --platforms Windows --work Rebuild/build/windows --output Rebuild/output-windows
```

Use fresh work/output directories each time. Mac apps require a Mac to build;
Mac/Linux can also create the Windows launcher. The builder includes the icon,
default configuration, compatible Slash aliases, bots and host rules.

Public map revisions can differ from the Slash snapshot. Its original URL is
unknown, so exact asset-for-asset reproduction still requires matching source
content. [Map hashes and source links](MAPS.md) identify the known differences.
If you have the original RAR, `--source /path/to/cs-slash.rar` also works.

## Original downloads and manual installation

These links let you install the native game without downloading our packages,
rebuild kit or repository:

| System | Xash3D FWGS engine | CS16Client: client, game code, menus and bots |
| --- | --- | --- |
| Windows x64 | [Engine `.7z`](https://github.com/FWGS/xash3d-fwgs/releases/download/continuous/xash3d-fwgs-win32-amd64.7z) | [Client `.zip`](https://github.com/FWGS/cs16-client/releases/download/continuous/CS16Client-Windows-x64.zip) |
| Linux x86_64 | [Engine `.tar.gz`](https://github.com/FWGS/xash3d-fwgs/releases/download/continuous/xash3d-fwgs-linux-amd64.tar.gz) | [Client `.tar.gz`](https://github.com/FWGS/cs16-client/releases/download/continuous/CS16Client-Linux-x86_64.tar.gz) |
| Mac ARM64 | [Engine `.tar.xz`](https://github.com/FWGS/xash3d-fwgs/releases/download/continuous/xash3d-fwgs-apple-arm64.tar.xz) | [Client `.zip`](https://github.com/FWGS/cs16-client/releases/download/continuous/CS16Client-macOS-arm64.zip) |

1. Create `Game/` and put your Steam `valve/` and `cstrike/` inside it.
2. Extract the engine; copy the directory containing `xash3d`/`xash3d.exe` into
   `Game/`, including runtime libraries and `valve/extras.pk3`. Preserve Linux
   library links and the Mac `SDL2.framework`.
3. Merge the client download's `cstrike/` into `Game/cstrike/`, including native
   `cl_dlls/`, `dlls/` and `extras.pk3`. Match the OS and architecture.
4. Install the custom maps and all their resources from the links in [MAPS.md](MAPS.md).
   Keep the upstream menus; do not install another repack's engine or menu skin.
5. Put `bot_enable 1` in `cstrike/game_init.cfg`, `bot_quota 0` in
   `cstrike/game.cfg`, and `con_fontscale 2` in `cstrike/config.cfg`.
6. From `Game/`, run the command for your OS:

   - Windows: `xash3d.exe -game cstrike`
   - Linux: `LD_LIBRARY_PATH="$PWD${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" ./xash3d -game cstrike`
   - Mac: `./xash3d -game cstrike`. Install FreeType and make its dylib available
     at the path reported by `otool -L cstrike/cl_dlls/menu_arm64.dylib`.

This creates the native game with bots and the downloaded maps. For a portable
Mac `.app` with bundled libraries, the supplied icon, GUI launchers and the Slash
configuration preset, use the builder above. Upstream setup:
[CS16Client installation](https://github.com/FWGS/cs16-client#installation).
Continuous URLs change; [upstream-lock.json](Rebuild/upstream-lock.json) records
our packaged runtime snapshot.

## Play

Create a game, join a team, then open the console with `~`:

```text
bot_add_ct
bot_add_t
```

Join LAN: `connect HOST_IP:27015`. Try `connect HOST_IP:27015 gs` for an old
Slash host; [server acceptance varies](https://github.com/FWGS/xash3d-fwgs/blob/master/Documentation/goldsrc-protocol-support.md).
Console size: `con_fontscale 2`, then `host_writeconfig` to save it.
Some supplied bot navigation needs `bot_nav_analyze`.
[Verification and limits](VERIFICATION.json).
