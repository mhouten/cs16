#!/usr/bin/env python3
"""Assemble self-contained clean CS 1.6 desktop packages from local releases."""
import argparse
import ctypes
import ctypes.util
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import stat
import struct
import subprocess
import sys
import tarfile
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / 'CS16'
BUILD = ROOT / 'build/distribution'
STOCK_MAPS = set('as_oilrig cs_747 cs_assault cs_backalley cs_estate cs_havana cs_italy cs_militia cs_office cs_siege de_airstrip de_aztec de_cbble de_chateau de_dust de_dust2 de_inferno de_nuke de_piranesi de_prodigy de_storm de_survivor de_torn de_train de_vertigo'.split())
STOCK_PLAYERS = set('arctic gign gsg9 guerilla leet sas terror urban vip'.split())
REFERENCED_MODELS = set()
REFERENCED_EVENTS = set()
PLATFORMS = {
    'macOS': ('xash3d-fwgs-apple-arm64.tar.xz', 'CS16Client-macOS-arm64.zip', 'xash3d'),
    'Linux': ('xash3d-fwgs-linux-amd64.tar.gz', 'CS16Client-Linux-x86_64.tar.gz', 'xash3d'),
    'Windows': ('xash3d-fwgs-win32-amd64.7z', 'CS16Client-Windows-x64.zip', 'xash3d.exe'),
}


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'Scripts' / filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


assets = module('assets', 'import-assets.py')
releases = module('releases', 'install-release.py')


def run(*command, **kwargs):
    subprocess.run([str(s) for s in command], check=True, **kwargs)


def keep_resource(path):
    parts = path.parts
    if any(s.startswith('.') for s in parts):
        return False
    if any(token in path.as_posix().lower() for token in ('royal', 'tgaming', 'shadowfighters', 'sarzamin', 'softgozar')):
        return False
    if not assets.asset_path(path.as_posix()):
        return False
    if parts[0] == 'cstrike':
        if len(parts) > 2 and parts[1] in ('maps', 'overviews') and path.stem not in STOCK_MAPS:
            return False
        if parts[1] == 'maps' and path.suffix.lower() == '.res' and path.name != 'default.res':
            return False  # Repack resource lists advertise plugin sound packs.
        if parts[1:3] in (('resource', 'images'), ('resource', '1background')):
            return False
        if parts[1:3] == ('gfx', 'images'):
            return False
        if len(parts) == 3 and parts[1] == 'gfx' and path.suffix.lower() != '.lmp':
            return False  # Repacks place advertising banners directly in gfx/.
        if parts[1] == 'models':
            model = Path(*parts[1:]).as_posix().lower()
            if model not in REFERENCED_MODELS:
                return False
        if parts[1] == 'sprites' and len(parts) > 3:
            return False
        if parts[1] == 'sound' and len(parts) > 3 and parts[2] in {'misc', 'money'}:
            return False
        if parts[1:4] == ('sound', 'radio', 'custom'):
            return False
        if parts[1] == 'events' and Path(*parts[1:]).as_posix().lower() not in REFERENCED_EVENTS:
            return False
    if path.name.lower() in {'motd.txt', 'readme.txt', 'steam_appid.txt', 'tempdecal.wad', 'cached.wad', 'commandmenu.txt',
                             'mapcycle.txt', 'maps.lst', 'liblist.gam', 'steam.inf', 'startupvids.txt'}:
        return False
    return True


def make_clean_data(out):
    # Use game-code precaches and stock map entity references to retain actual
    # gameplay models, excluding the repack's downloaded skins and plugin models.
    for source in (ROOT / 'ReGameDLL_CS/regamedll').rglob('*'):
        if source.suffix in {'.cpp', '.h'}:
            text = source.read_text(errors='replace')
            REFERENCED_MODELS.update(s.lower() for s in re.findall(r'"(models/[^"%]+\.mdl)"', text))
            REFERENCED_EVENTS.update(s.lower() for s in re.findall(r'"(events/[^"%]+\.sc)"', text))
    for name in STOCK_MAPS:
        source = ROOT / 'game-data/cstrike/maps' / (name + '.bsp')
        blob = source.read_bytes()
        offset, size = struct.unpack_from('<ii', blob, 4)
        entities = blob[offset:offset + size].decode('latin1')
        REFERENCED_MODELS.update(s.lower() for s in re.findall(r'(models/[^"\s]+\.mdl)', entities))
    REFERENCED_MODELS.update(f'models/player/{name}/{name}.mdl' for name in STOCK_PLAYERS)
    for source in (ROOT / 'game-data').rglob('*'):
        rel = source.relative_to(ROOT / 'game-data')
        if not source.is_file() or source.is_symlink() or not keep_resource(rel):
            continue
        target = out / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    assets.defaults(out)
    config = out / 'cstrike/config.cfg'
    text = config.read_text().replace('LAN Player', 'Player').replace('hud_fastswitch "1"', 'hud_fastswitch "0"').replace('cl_dynamiccrosshair "0"', 'cl_dynamiccrosshair "1"')
    config.write_text(text + 'bind "z" "radio1"\nbind "x" "radio2"\nbind "c" "radio3"\nbind "k" "+voicerecord"\nbind "n" "nightvision"\ntouch_enable "0"\nxhair_enable "0"\n+mlook\n')
    game = out / 'cstrike'
    definition = game / 'gameinfo.txt'
    definition.write_text(definition.read_text().replace('trainmap "tr_1"', 'trainmap ""'))
    (game / 'motd.txt').write_text('Welcome to Counter-Strike 1.6.\n')
    (game / 'mapcycle.txt').write_text('\n'.join(sorted(STOCK_MAPS)) + '\n')
    (game / 'maps.lst').write_text('\n'.join(f'{m} "{m}"' for m in sorted(STOCK_MAPS)) + '\n')
    (game / 'server.cfg').write_text('hostname "Counter-Strike 1.6"\nsv_lan 1\nmp_timelimit 20\nmp_freezetime 6\nmp_roundtime 5\nmp_friendlyfire 0\n')
    (game / 'listenserver.cfg').write_text('exec server.cfg\n')


def clean_extras(source, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(source) as original, zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as package:
        for info in original.infolist():
            parts = Path(info.filename).parts
            if not parts or any(s.startswith('.') or s == '..' for s in parts):
                continue
            if parts[0] in {'addons', 'touch', 'touch_presets', 'touch_default', 'maps'}:
                continue
            if info.filename in {'touch.cfg', 'userconfig.d/touch_defalias.cfg'}:
                continue
            # Keep upstream UI assets, fonts/licenses and gameplay resources.
            package.writestr(info, original.read(info))


def unpack_7z(source, out):
    """Read regular members only; official Windows builds do not need links."""
    lib = ctypes.CDLL(ctypes.util.find_library('archive'))
    definitions = {
        'archive_read_new': (ctypes.c_void_p, []),
        'archive_read_support_filter_all': (ctypes.c_int, [ctypes.c_void_p]),
        'archive_read_support_format_all': (ctypes.c_int, [ctypes.c_void_p]),
        'archive_read_open_filename': (ctypes.c_int, [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_size_t]),
        'archive_read_next_header': (ctypes.c_int, [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]),
        'archive_entry_pathname': (ctypes.c_char_p, [ctypes.c_void_p]),
        'archive_entry_filetype': (ctypes.c_uint, [ctypes.c_void_p]),
        'archive_read_data': (ctypes.c_ssize_t, [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t]),
        'archive_error_string': (ctypes.c_char_p, [ctypes.c_void_p]),
        'archive_read_free': (ctypes.c_int, [ctypes.c_void_p]),
    }
    for name, (restype, argtypes) in definitions.items():
        getattr(lib, name).restype, getattr(lib, name).argtypes = restype, argtypes
    reader = lib.archive_read_new()
    try:
        lib.archive_read_support_filter_all(reader)
        lib.archive_read_support_format_all(reader)
        if lib.archive_read_open_filename(reader, os.fsencode(source), 65536) != 0:
            raise RuntimeError(lib.archive_error_string(reader).decode())
        entry = ctypes.c_void_p()
        buffer = ctypes.create_string_buffer(65536)
        while True:
            status = lib.archive_read_next_header(reader, ctypes.byref(entry))
            if status == 1:
                break
            if status != 0:
                raise RuntimeError(lib.archive_error_string(reader).decode())
            rel = Path(lib.archive_entry_pathname(entry).decode().replace('\\', '/'))
            if rel.is_absolute() or '..' in rel.parts:
                raise RuntimeError('Unsafe archive member')
            if lib.archive_entry_filetype(entry) != stat.S_IFREG:
                continue
            target = out / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open('wb') as stream:
                while True:
                    size = lib.archive_read_data(reader, buffer, len(buffer))
                    if size < 0:
                        raise RuntimeError(lib.archive_error_string(reader).decode())
                    if size == 0:
                        break
                    stream.write(buffer.raw[:size])
    finally:
        lib.archive_read_free(reader)


def make_icons():
    icons = BUILD / 'icons'
    icons.mkdir(parents=True, exist_ok=True)
    if (icons / 'CounterStrike.icns').exists():
        return icons
    source = ROOT / 'game-data/cstrike/game.ico'
    shutil.copyfile(source, icons / 'CounterStrike.ico')
    run('sips', '-s', 'format', 'png', source, '--out', icons / 'CounterStrike.png', stdout=subprocess.DEVNULL)
    iconset = icons / 'CounterStrike.iconset'
    iconset.mkdir(exist_ok=True)
    for size in (16, 32, 128, 256, 512):
        for scale in (1, 2):
            name = f'icon_{size}x{size}' + ('@2x' if scale == 2 else '') + '.png'
            run('sips', '-z', size * scale, size * scale, icons / 'CounterStrike.png', '--out', iconset / name, stdout=subprocess.DEVNULL)
    # ICNS is a container for PNG representations; constructing it does not
    # require the GUI services that iconutil needs in this restricted session.
    chunks = []
    for kind, name in [('icp4', '16x16'), ('icp5', '32x32'), ('icp6', '32x32@2x'),
                       ('ic07', '128x128'), ('ic08', '256x256'),
                       ('ic09', '512x512'), ('ic10', '512x512@2x')]:
        png = (iconset / f'icon_{name}.png').read_bytes()
        chunks.append(kind.encode() + struct.pack('>I', len(png) + 8) + png)
    payload = b''.join(chunks)
    (icons / 'CounterStrike.icns').write_bytes(b'icns' + struct.pack('>I', len(payload) + 8) + payload)
    return icons


def mac_launcher(folder, icons):
    contents = folder / 'Counter-Strike.app/Contents'
    (contents / 'MacOS').mkdir(parents=True, exist_ok=True)
    resources = contents / 'Resources'
    resources.mkdir(exist_ok=True)
    shutil.copyfile(icons / 'CounterStrike.icns', resources / 'CounterStrike.icns')
    info = {'CFBundleName': 'Counter-Strike', 'CFBundleDisplayName': 'Counter-Strike 1.6',
            'CFBundleIdentifier': 'local.counterstrike.cs16', 'CFBundleExecutable': 'CounterStrike',
            'CFBundleIconFile': 'CounterStrike.icns', 'CFBundlePackageType': 'APPL',
            'CFBundleVersion': '1', 'CFBundleShortVersionString': '1.6',
            'LSMinimumSystemVersion': '13.0', 'NSHighResolutionCapable': True,
            'NSLocalNetworkUsageDescription': 'Play Counter-Strike with people on your local network.'}
    (contents / 'Info.plist').write_bytes(plistlib.dumps(info))
    code = BUILD / 'mac-launcher.c'
    code.write_text('''#include <mach-o/dyld.h>
#include <libgen.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>
static int directories(char *path) {
    for (char *p=path+1; *p; ++p) {
        if (*p=='/') { *p=0; mkdir(path,0700); *p='/'; }
    }
    mkdir(path,0700);
    struct stat st;
    return stat(path,&st) || !S_ISDIR(st.st_mode);
}
int main(int argc, char **argv) {
    char path[PATH_MAX], resolved[PATH_MAX], game[PATH_MAX], engine[PATH_MAX], writable[PATH_MAX], link[PATH_MAX], library[PATH_MAX];
    uint32_t size = sizeof(path);
    if (_NSGetExecutablePath(path, &size) || !realpath(path, resolved)) return 1;
    snprintf(game, sizeof(game), "%s/../Resources/Game", dirname(resolved));
    if (!realpath(game,path)) return 1;
    snprintf(game,sizeof(game),"%s",path);
    const char *custom=getenv("CS16_USERDIR"), *home=getenv("HOME");
    if (custom && custom[0]=='/') snprintf(writable,sizeof(writable),"%s",custom);
    else if (home) snprintf(writable,sizeof(writable),"%s/Library/Application Support/Counter-Strike 1.6",home);
    else return 1;
    if (directories(writable) || chdir(writable)) return 1;
    mkdir("valve",0700); mkdir("cstrike",0700);
    snprintf(library,sizeof(library),"%s/filesystem_stdio.dylib",game);
    snprintf(link,sizeof(link),"%s/filesystem_stdio.dylib",writable);
    unlink(link);
    if (symlink(library,link)) return 1;
    setenv("XASH3D_BASEDIR", writable, 1);
    setenv("XASH3D_RODIR", game, 1);
    snprintf(engine, sizeof(engine), "%s/xash3d", game);
    char **args = calloc((size_t)argc + 3, sizeof(char *));
    if (!args) return 1;
    args[0] = engine; args[1] = "-game"; args[2] = "cstrike";
    for (int i = 1; i < argc; i++) args[i+2] = argv[i];
    execv(engine, args);
    return 1;
}
''')
    run('clang', '-arch', 'arm64', '-O2', '-mmacosx-version-min=13.0', code, '-o', contents / 'MacOS/CounterStrike')
    return resources / 'Game'


def linux_launcher(folder, icons):
    launcher = folder / 'Play'
    launcher.write_text('''#!/bin/sh
set -eu
game="$(CDPATH='' cd -- "$(dirname -- "$0")/Game" && pwd)"
# Register the normal application-menu entry and icon on the user's first run.
(
    data="${XDG_DATA_HOME:-$HOME/.local/share}"
    mkdir -p "$data/applications" "$data/icons/hicolor/128x128/apps"
    cp "$game/CounterStrike.png" "$data/icons/hicolor/128x128/apps/counter-strike.png"
    app="${game%/Game}"
    escaped=$(printf '%s' "$app/Play" | sed 's/[\\\\"`$]/\\\\&/g; s/\\\\/\\\\\\\\/g; s/%/%%/g')
    printf '%s\\n' '[Desktop Entry]' 'Type=Application' 'Name=Counter-Strike 1.6' \\
        "Exec=\\"$escaped\\"" 'Icon=counter-strike' 'Terminal=false' \\
        'Categories=Game;ActionGame;' 'StartupWMClass=CounterStrike' \\
        > "$data/applications/counter-strike.desktop"
) 2>/dev/null || true
export XASH3D_BASEDIR="$game"
export SDL_VIDEO_X11_WMCLASS=CounterStrike
export LD_LIBRARY_PATH="$game${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
cd "$game"
exec ./xash3d -game cstrike "$@"
''')
    launcher.chmod(0o755)
    # No absolute installation paths are embedded in the portable launcher.
    desktop = folder / 'Counter-Strike.desktop'
    command = 'exec "$(dirname "$1")/Play"'
    escaped = ''.join('\\' + ch if ch in '\\"`$' else ch for ch in command)
    quoted = '"' + escaped.replace('\\', '\\\\') + '"'
    desktop.write_text('''[Desktop Entry]
Type=Application
Name=Counter-Strike 1.6
Comment=Counter-Strike
Exec=sh -c ''' + quoted + ''' sh %k
Icon=counter-strike
Terminal=false
Categories=Game;ActionGame;
StartupWMClass=CounterStrike
''')
    desktop.chmod(0o755)
    return folder / 'Game'


def windows_launcher(folder, icons):
    launcher_dir = ROOT / 'Scripts/windows-launcher'
    run(sys.executable, ROOT / 'Scripts/windows-icon.py', icons / 'CounterStrike.ico', launcher_dir / 'icon_windows_amd64.syso')
    env = os.environ.copy()
    env.update(GOOS='windows', GOARCH='amd64', CGO_ENABLED='0', GO111MODULE='off',
               GOTOOLCHAIN='local', GOPROXY='off', GOSUMDB='off', GOCACHE=str(BUILD / 'go-cache'))
    run('go', 'build', '-trimpath', '-ldflags=-H=windowsgui -s -w', '-o', folder / 'Counter-Strike.exe', '.', cwd=launcher_dir, env=env)
    return folder / 'Game'


def assemble(platform, icons):
    engine_name, client_name, executable = PLATFORMS[platform]
    archives = [next((directory / name for directory in (ROOT, ROOT / 'downloads', ROOT / 'ALL') if (directory / name).is_file()), None)
                for name in (engine_name, client_name)]
    if not all(archives):
        print(f'{platform}: waiting for ' + ', '.join(name for name, path in zip((engine_name, client_name), archives) if path is None))
        return False
    with tempfile.TemporaryDirectory(prefix='cs16-package-', dir=BUILD) as temporary:
        temporary = Path(temporary)
        engine, client, package = temporary / 'engine', temporary / 'client', temporary / 'package'
        for path in (engine, client, package):
            path.mkdir()
        for archive, target in zip(archives, (engine, client)):
            if archive.suffix == '.7z':
                unpack_7z(archive, target)
            else:
                releases.unpack(archive, target)
        matches = list(engine.rglob(executable))
        if len(matches) != 1:
            raise RuntimeError(f'{platform}: expected one {executable}')
        native = matches[0].parent
        if platform == 'macOS':
            game = mac_launcher(package, icons)
        elif platform == 'Linux':
            game = linux_launcher(package, icons)
        else:
            game = windows_launcher(package, icons)
        shutil.copytree(BUILD / 'clean-data', game)
        if platform == 'Linux':
            shutil.copyfile(icons / 'CounterStrike.png', game / 'CounterStrike.png')
        for source in native.iterdir():
            if source.name == executable or (source.is_file() and source.suffix.lower() in {'.dll', '.dylib', '.so'}) or '.so.' in source.name:
                if source.name in {'libmenu_tui.dylib', 'libmenu_tui.so', 'menu_tui.dll'}:
                    continue
                if source.is_symlink():
                    target = Path(os.readlink(source))
                    if target.is_absolute() or '..' in target.parts:
                        raise RuntimeError('Unexpected external runtime library link')
                    (game / source.name).symlink_to(target)
                else:
                    shutil.copy2(source, game / source.name)
            elif source.name == 'SDL2.framework':
                shutil.copytree(source, game / source.name, symlinks=True)
        if platform != 'Windows':
            (game / executable).chmod(0o755)
        for folder in ('cl_dlls', 'dlls'):
            sources = list(client.rglob(folder))
            for directory in sources:
                if directory.parent.name != 'cstrike':
                    continue
                for source in directory.iterdir():
                    if source.is_file() and source.suffix.lower() in {'.dll', '.so', '.dylib'} and source.name.lower().startswith(('client', 'menu', 'cs', 'mp')):
                        dest = game / 'cstrike' / folder / source.name
                        dest.parent.mkdir(exist_ok=True)
                        shutil.copy2(source, dest)
        extras = list(client.rglob('cstrike/extras.pk3'))
        if len(extras) != 1:
            raise RuntimeError(f'{platform}: expected client UI resources')
        clean_extras(extras[0], game / 'cstrike/extras.pk3')
        if (native / 'valve/extras.pk3').exists():
            clean_extras(native / 'valve/extras.pk3', game / 'valve/extras.pk3')
        (game / 'Licenses').mkdir(exist_ok=True)
        (game / 'Licenses/Components.txt').write_text('Xash3D FWGS: https://github.com/FWGS/xash3d-fwgs\nCS16Client and ReGameDLL: https://github.com/FWGS/cs16-client\nOriginal Counter-Strike resources remain property of their respective owners.\n')
        if platform == 'macOS':
            # Resolve the release's Homebrew-specific path inside the app bundle.
            local_menu = ROOT / 'game-data/cstrike/cl_dlls'
            for name in ('menu_arm64.dylib', 'libfreetype.6.dylib'):
                shutil.copy2(local_menu / name, game / 'cstrike/cl_dlls' / name)
            run('xattr', '-dr', 'com.apple.quarantine', package)
            run('codesign', '--force', '--deep', '--sign', '-', package / 'Counter-Strike.app')
        elif platform == 'Windows':
            goroot = Path(subprocess.check_output(['go', 'env', 'GOROOT'], text=True).strip())
            license_file = next(p for p in (goroot / 'LICENSE', goroot.parent / 'LICENSE') if p.is_file())
            shutil.copyfile(license_file, game / 'Licenses/Go.txt')
        final = OUTPUT / platform
        if final.exists():
            raise RuntimeError(f'{final} already exists; refusing to overwrite a finished package')
        shutil.move(str(package), final)
    manifest = {'platform': platform, 'engine_archive': engine_name, 'client_archive': client_name,
                'engine_sha256': releases.digest(archives[0]), 'client_sha256': releases.digest(archives[1]),
                'output': str(final), 'stock_maps': sorted(STOCK_MAPS)}
    (BUILD / f'{platform}-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'{platform}: packaged at {final}')
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('platforms', nargs='*', choices=list(PLATFORMS), default=list(PLATFORMS))
    args = parser.parse_args()
    BUILD.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(exist_ok=True)
    if not (BUILD / 'clean-data').exists():
        make_clean_data(BUILD / 'clean-data')
    icons = make_icons()
    missing = []
    for platform in args.platforms:
        if (OUTPUT / platform).exists():
            print(f'{platform}: already packaged')
            continue
        if not assemble(platform, icons):
            missing.append(platform)
    if missing:
        raise SystemExit('Not complete yet: ' + ', '.join(missing))


if __name__ == '__main__':
    main()
