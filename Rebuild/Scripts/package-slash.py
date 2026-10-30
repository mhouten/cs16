#!/usr/bin/env python3
"""Build native Slash editions from local game data and official FWGS releases.

Run --help for inputs. No original Windows game executable is ever run.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent.parent


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).parent / filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


pack = module('slash_pack_helpers', 'package-clean.py')
DATA_EXTENSIONS = set('''.bsp .wad .mdl .spr .wav .mp3 .ogg .tga .bmp .pcx .lmp
    .pal .res .txt .lst .sc .seq .png .jpg .jpeg .dds .ico .nav .nod .scr .htm
    .html .ttf .otf .fgd'''.split())
SKIP_FILES = {'cached.wad', 'tempdecal.wad', 'steam_appid.txt', 'snapshot0000.bmp'}
ADAPTED_CONFIGS = {'config.cfg', 'autoexec.cfg', 'userconfig.cfg', 'gwlistenserver.cfg',
                   'server.cfg', 'listenserver.cfg', 'okk1.cfg'}


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def read_text(path):
    return Path(path).read_bytes().decode('latin1').replace('\r\n', '\n')


def supported_data(rel):
    """Import game content, while keeping old native code and saved state out."""
    parts = tuple(p.lower() for p in rel.parts)
    if not parts or parts[0] not in {'cstrike', 'valve'}:
        return False
    if any(p.startswith('.') or p in {'cl_dlls', 'dlls', 'addons', 'save', 'cache',
                                     'download', 'downloads', 'hw'} for p in parts):
        return False
    if parts[-1] in SKIP_FILES or parts[-1].startswith(('snapshot', 'screenshot')):
        return False
    return rel.suffix.lower() in DATA_EXTENSIONS or (rel.suffix.lower() == '.cfg' and len(parts) == 2)


def remove_commands(text, commands):
    # Retain comments and aliases; only rewrite standalone legacy commands.
    result = []
    for line in text.splitlines():
        match = re.match(r'\s*([^\s/]+)', line)
        if match and match[1].lower() in commands:
            continue
        result.append(line)
    return '\n'.join(result) + '\n'


def is_menu_override(rel):
    parts = tuple(p.lower() for p in rel.parts)
    if parts[1:3] == ('gfx', 'shell'):
        return True
    if len(parts) > 2 and parts[1] == 'resource':
        # Keep localization used by the native client, but let upstream MainUI
        # supply its own artwork, controls and colors.
        return not (len(parts) == 3 and rel.suffix.lower() == '.txt' and '_' in rel.stem)
    return parts[1:] == ('media', 'gamestartup.mp3')


def make_data(source, target, menu_style='default'):
    if not (source / 'cstrike/maps/de_dust2.bsp').is_file() or not (source / 'valve').is_dir():
        raise RuntimeError('Source must contain cstrike/ and valve/ (including de_dust2.bsp).')
    copied, excluded = [], []
    # Steam installations do not contain the repack's custom startup scripts.
    # Supply the public portable preset instead of depending on private files
    # or importing a Steam user's saved configuration.
    slash_source = (source / 'cstrike/gwlistenserver.cfg').is_file()
    config_source = source / 'cstrike' if slash_source else ROOT / 'Defaults/cstrike'
    if not slash_source and menu_style != 'default':
        raise RuntimeError('Slash menu mode requires original Slash source assets.')
    def config_text(name):
        return read_text(config_source / name)
    for folder in ('valve', 'cstrike'):
        (target / folder).mkdir(parents=True, exist_ok=True)
        for path in sorted((source / folder).rglob('*')):
            if not path.is_file() or path.is_symlink():
                continue
            rel = path.relative_to(source)
            if (not supported_data(rel) or (menu_style == 'default' and is_menu_override(rel))
                    or (not slash_source and rel.suffix.lower() == '.cfg')):
                excluded.append(rel.as_posix())
                continue
            if path.suffix.lower() == '.wad':
                with path.open('rb') as stream:
                    valid_wad = stream.read(4) in {b'WAD2', b'WAD3'}
                if not valid_wad:
                    excluded.append(rel.as_posix())
                    continue
            dest = target / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, dest)
            copied.append(rel.as_posix())
    game = target / 'cstrike'
    config = remove_commands(config_text('config.cfg'), {'console', 'name', '+jlook'})
    config += '''\n// Native Slash defaults; personal settings are saved by the engine.
name "Player"
console "1"
bind "`" "toggleconsole"
bind "~" "toggleconsole"
touch_enable "0"
xhair_enable "0"
ui_prefer_won_background "0"
ui_background_stretch "0"
bot_enable "1"
bot_quota "0"
+mlook
'''
    (game / 'config.cfg').write_text(config, encoding='latin1')
    if menu_style == 'default':
        # Start from desktop bindings/settings rather than the repack's locked
        # renderer cvars. Gameplay aliases are retained separately below.
        (game / 'config.cfg').unlink()
        pack.assets.defaults(target)
        config = (game / 'config.cfg').read_text().replace('LAN Player', 'Player')
        config = config.replace('hud_fastswitch "1"', 'hud_fastswitch "0"')
        config = config.replace('cl_dynamiccrosshair "0"', 'cl_dynamiccrosshair "1"')
        config += '''bind "z" "radio1"
bind "x" "radio2"
bind "c" "radio3"
bind "k" "+voicerecord"
bind "n" "nightvision"
bind "h" "+commandmenu"
bind "F1" "autobuy"
bind "F2" "rebuy"
setinfo "_vgui_menus" "1"
console 1
touch_enable 0
xhair_enable 0
ui_prefer_won_background 1
+mlook
'''
        (game / 'config.cfg').write_text(config)
    # A readable desktop console, including on Retina displays. Keep this in
    # config.cfg so the engine can save each player's preferred scale normally.
    with (game / 'config.cfg').open('a') as stream:
        stream.write('\n// Larger console text; use con_fontscale to adjust.\n'
                     'con_fontscale "2"\ncon_fontnum "-1"\n')
    # Slash autoexec only locks the console. Keep the opt-in lockconsole.cfg,
    # while starting the portable edition with a usable console and native UI.
    (game / 'autoexec.cfg').write_text('''// Counter-Strike Slash native startup
console 1
bind "`" "toggleconsole"
bind "~" "toggleconsole"
exec userconfig.cfg
''')
    user = config_text('userconfig.cfg')
    user = remove_commands(user, {'clear'})
    # These aliases describe the replaced Windows engine/emulator, not this build.
    user = '\n'.join(line for line in user.splitlines() if not re.match(
        r'\s*alias\s+(?:gwcfgfv|gwguiv|revemuv|gcffv|gwversion)\s', line, re.I)) + '\n'
    if menu_style == 'default':
        user = '// Compatible Slash buy/demo aliases, with default native UI settings.\n' + '\n'.join(
            line for line in user.splitlines() if re.match(r'\s*alias\s+', line, re.I)
            and not re.match(r'\s*alias\s+shield\s', line, re.I)) + '\n'
    user += '''\n// Show the actual native runtime version.
alias gwversion "version"
// Slash gameplay shortcuts remain available.
console 1
touch_enable 0
xhair_enable 0
'''
    (game / 'userconfig.cfg').write_text(user, encoding='latin1')
    host = remove_commands(config_text('gwlistenserver.cfg'),
                           {'rcon_password', 'sv_contact', 'sv_lan', 'hostname', 'bot_enable', 'bot_quota',
                            'sv_clipmode', 'sv_lan_rate', 'sv_proxies'})
    host = host.replace('CS 1.6 P48B4554', 'native edition')
    host += '''\n// Native Slash LAN host; original gameWARE round rules are retained.
hostname "Counter-Strike Slash"
sv_lan 1
rcon_password ""
bot_enable 1
bot_quota 0
'''
    (game / 'gwlistenserver.cfg').write_text(host, encoding='latin1')
    if menu_style == 'default':
        (game / 'gwlistenserver.cfg').write_text(host.replace('hostname "Counter-Strike Slash"',
                                                           'hostname "Counter-Strike 1.6"'), encoding='latin1')
    for name in ('server.cfg', 'listenserver.cfg'):
        (game / name).write_text('exec gwlistenserver.cfg\n')
    (game / 'game_init.cfg').write_text('// Enable native CS bots before GameDLL initialization.\nbot_enable 1\n')
    (game / 'game.cfg').write_text('// No automatic bots; use bot_add / bot_add_ct / bot_add_t.\nbot_quota 0\n')
    # Keep Slash's alternate bindings, without a repack player's identity.
    alternate = config_source / 'okk1.cfg'
    if alternate.exists():
        (game / 'okk1.cfg').write_text(remove_commands(read_text(alternate), {'name', 'console'}) +
                                      'name "Player"\nconsole 1\n', encoding='latin1')
    # The source valve.rc predates Xash3D's startup/configuration sequence.
    # Use the upstream engine's startup script, shipped in valve/extras.pk3.
    # No legacy valve.rc is imported; ordinary Slash assets are unchanged.
    maps = sorted(p.stem for p in (game / 'maps').glob('*.bsp'))
    (game / 'mapcycle.txt').write_text('\n'.join(maps) + '\n')
    (game / 'maps.lst').write_text('\n'.join(f'{m} "{m}"' for m in maps) + '\n')
    (game / 'gameinfo.txt').write_text('''title "Counter-Strike Slash"
basedir "valve"
gamedir "cstrike"
gamedll "dlls/mp.dll"
gamedll_linux "dlls/cs.so"
gamedll_osx "dlls/cs.dylib"
dllpath "cl_dlls"
gamemode "multiplayer_only"
mp_entity "info_player_start"
startmap "de_dust2"
trainmap ""
nomodels 1
''')
    (target / 'valve/gameinfo.txt').write_text('''title "Half-Life"
gamedir "valve"
startmap "c0a0"
trainmap "t0a0"
''')
    # MainUI reads colors.lst instead of the original Windows VGUI scheme.
    # Translate Slash's amber text and dark panels to the native controls.
    scheme = read_text(source / 'cstrike/resource/ClientScheme.res') if menu_style == 'slash' else ''
    colors = {}
    for native, legacy in {'HELP_COLOR': 'BaseText', 'PROMPT_BG_COLOR': 'WindowBG',
                           'PROMPT_TEXT_COLOR': 'ControlText', 'PROMPT_FOCUS_COLOR': 'BrightControlText',
                           'INPUT_TEXT_COLOR': 'ControlText', 'INPUT_BG_COLOR': 'ControlDarkBG',
                           'INPUT_FG_COLOR': 'SelectedText'}.items():
        match = re.search(r'"' + legacy + r'"\s+"(\d+\s+\d+\s+\d+)', scheme)
        if match:
            colors[native] = ' '.join(match[1].split())
    if menu_style == 'slash':
        colors['CON_TEXT_COLOR'] = '255 180 30'
        (game / 'gfx/shell/colors.lst').write_text('\n'.join(k + ' ' + v for k, v in colors.items()) + '\n')
    else:
        definition = game / 'gameinfo.txt'
        definition.write_text(definition.read_text().replace('Counter-Strike Slash', 'Counter-Strike'))
    # The current menu supports the original tiled BackgroundLayout and uses
    # its own native controls. Preserve all original RES files for reference.
    report = {'source_files_copied': len(copied), 'maps': maps,
              'navigation_files': len(list((game / 'maps').glob('*.nav'))),
              'adapted_files': sorted('cstrike/' + n for n in ADAPTED_CONFIGS) +
                               ['cstrike/mapcycle.txt', 'cstrike/maps.lst', 'cstrike/gameinfo.txt',
                                'cstrike/game_init.cfg', 'cstrike/game.cfg', 'cstrike/gfx/shell/colors.lst',
                                'valve/gameinfo.txt'],
              'excluded_files': excluded,
              'menu_style': menu_style,
              'source_profile': 'Slash archive' if slash_source else 'Steam data and public maps',
              'menu': ('Unmodified upstream CS16Client/MainUI artwork and colors; no Slash menu overrides.'
                       if menu_style == 'default' else 'Slash artwork and colors with native MainUI controls.'),
              'network': 'Native Xash LAN; old GoldSrc/Slash host compatibility is not guaranteed.'}
    if menu_style == 'default':
        report['adapted_files'].remove('cstrike/gfx/shell/colors.lst')
    # A digest inventory allows independent verification of every carried asset.
    report['source_content_sha256'] = {name: digest(source / name) for name in copied}
    report['output_content_sha256'] = {p.relative_to(target).as_posix(): digest(p)
                                      for p in sorted(target.rglob('*')) if p.is_file()}
    return report


def fetch_releases(cache, platforms):
    """Verify cached files against current GitHub metadata; fetch missing/changed files."""
    cache.mkdir(parents=True, exist_ok=True)
    result = {}
    for repo, index in [('FWGS/xash3d-fwgs', 0), ('FWGS/cs16-client', 1)]:
        url = f'https://api.github.com/repos/{repo}/releases/tags/continuous'
        req = urllib.request.Request(url, headers={'User-Agent': 'Slash-native-builder'})
        with urllib.request.urlopen(req, timeout=45) as stream:
            metadata = json.load(stream)
        for system in platforms:
            name = pack.PLATFORMS[system][index]
            asset = next(a for a in metadata['assets'] if a['name'] == name)
            target = cache / name
            expected = asset.get('digest')
            if not expected or not expected.startswith('sha256:'):
                raise RuntimeError(f'GitHub did not publish a SHA256 digest for {name}.')
            if not target.is_file() or 'sha256:' + digest(target) != expected:
                partial = target.with_name(target.name + '.partial')
                try:
                    with urllib.request.urlopen(asset['browser_download_url'], timeout=120) as src, partial.open('wb') as dst:
                        shutil.copyfileobj(src, dst)
                    if 'sha256:' + digest(partial) != expected:
                        raise RuntimeError(f'Checksum mismatch: {name}')
                    partial.replace(target)
                finally:
                    partial.unlink(missing_ok=True)
            result[name] = {'url': asset['browser_download_url'], 'sha256': expected[7:],
                            'release_published_at': metadata['published_at'],
                            'target_commitish': metadata['target_commitish']}
    write_json(cache / 'slash-upstream-lock.json', result)
    return result


def archive_extract(path, dest):
    dest.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() not in {'.rar', '.7z'}:
        pack.releases.unpack(path, dest)
        return
    # macOS's bsdtar handles this RAR revision better than the independently
    # installed libarchive selected by ctypes on some machines.
    bsdtar = shutil.which('bsdtar')
    if path.suffix.lower() == '.rar' and bsdtar:
        names = subprocess.check_output([bsdtar, '-tf', str(path)], text=True).splitlines()
        for name in names:
            rel = Path(name.replace('\\', '/'))
            if rel.is_absolute() or '..' in rel.parts or ':' in name:
                raise RuntimeError('Unsafe archive member: ' + name)
        pack.run(bsdtar, '-xf', path, '-C', dest, '--no-same-owner', '--no-same-permissions')
        return
    if pack.ctypes.util.find_library('archive'):
        pack.unpack_7z(path, dest)  # libarchive supports both 7z and RAR.
        return
    exe = next((shutil.which(n) for n in ('7zz', '7z', '7z.exe') if shutil.which(n)), None)
    if not exe:
        raise RuntimeError('Install 7-Zip (7z/7zz on PATH) or libarchive to extract RAR/7z inputs.')
    # Check member paths before allowing an external extractor to write files.
    listing = subprocess.check_output([exe, 'l', '-slt', str(path)], text=True)
    members = listing.split('----------', 1)[-1]
    for name in re.findall(r'^Path = (.+)$', members, re.M):
        rel = Path(name.replace('\\', '/'))
        if rel.is_absolute() or '..' in rel.parts or ':' in name:
            raise RuntimeError('Unsafe archive member: ' + name)
    if re.search(r'^(?:Symbolic Link|Hard Link) = ', members, re.M):
        raise RuntimeError('Links are not supported in RAR/7z source inputs.')
    pack.run(exe, 'x', '-y', '-o' + str(dest), path, stdout=subprocess.DEVNULL)


def portable_freetype(menu, library):
    """Bundle non-system dylib dependencies, including recursive Homebrew dependencies."""
    pending, visited = [menu], set()
    while pending:
        current = pending.pop()
        if current in visited:
            continue
        visited.add(current)
        lines = subprocess.check_output(['otool', '-L', str(current)], text=True).splitlines()[1:]
        for line in lines:
            dependency = line.strip().split(' (', 1)[0]
            if not dependency.startswith('/') or dependency.startswith(('/usr/lib/', '/System/')):
                continue
            if dependency == str(current):
                continue
            source = Path(dependency)
            if 'freetype' in source.name and library:
                source = library
            if not source.is_file():
                raise RuntimeError(f'Missing macOS dependency {dependency}; use --freetype or install brew freetype.')
            target = menu.parent / source.name
            if not target.exists():
                shutil.copyfile(source, target)
            pack.run('install_name_tool', '-change', dependency, '@loader_path/' + target.name, current)
            pending.append(target)
    for current in visited:
        pack.run('codesign', '--force', '--sign', '-', current, stderr=subprocess.DEVNULL)


def assemble(system, data, cache, dest, icons, work, freetype, menu_style='default'):
    with tempfile.TemporaryDirectory(prefix=system + '-', dir=work) as tmp:
        tmp = Path(tmp)
        engine, client, package = tmp / 'engine', tmp / 'client', tmp / 'package'
        for name, folder in zip(pack.PLATFORMS[system][:2], (engine, client)):
            archive_extract(cache / name, folder)
        package.mkdir()
        executable = pack.PLATFORMS[system][2]
        matches = list(engine.rglob(executable))
        if len(matches) != 1:
            raise RuntimeError('Expected one native engine: ' + executable)
        native = matches[0].parent
        if system == 'macOS':
            if platform.system() != 'Darwin':
                raise RuntimeError('Build the macOS app on macOS with Xcode Command Line Tools.')
            game = pack.mac_launcher(package, icons)
            import plistlib
            plist = package / 'Counter-Strike.app/Contents/Info.plist'
            info = plistlib.loads(plist.read_bytes())
            info.update(CFBundleDisplayName='Counter-Strike 1.6' if menu_style == 'default' else 'Counter-Strike Slash',
                        CFBundleName='Counter-Strike 1.6' if menu_style == 'default' else 'Counter-Strike Slash',
                        CFBundleIdentifier='local.counterstrike.complete' if menu_style == 'default' else 'local.counterstrike.slash')
            plist.write_bytes(plistlib.dumps(info))
        elif system == 'Linux':
            game = pack.linux_launcher(package, icons)
            for name in ('Play', 'Counter-Strike.desktop'):
                path = package / name
                path.write_text(path.read_text().replace('Counter-Strike 1.6',
                                'Counter-Strike 1.6' if menu_style == 'default' else 'Counter-Strike Slash')
                                .replace('counter-strike', 'counter-strike-complete' if menu_style == 'default' else 'counter-strike-slash'))
        else:
            game = pack.windows_launcher(package, icons)
        shutil.copytree(data, game)
        for source in native.iterdir():
            if source.name == executable or source.suffix.lower() in {'.dll', '.dylib', '.so'} or '.so.' in source.name:
                if source.name in {'libmenu_tui.dylib', 'libmenu_tui.so', 'menu_tui.dll'}:
                    continue
                if source.is_symlink():
                    target = Path(os.readlink(source))
                    if target.is_absolute() or '..' in target.parts:
                        raise RuntimeError('External runtime symlink: ' + str(source))
                    (game / source.name).symlink_to(target)
                else:
                    shutil.copy2(source, game / source.name)
            elif source.name == 'SDL2.framework':
                shutil.copytree(source, game / source.name, symlinks=True)
        if system != 'Windows':
            (game / executable).chmod(0o755)
        # Use the engine and client startup resources/fonts, and native CS bots.
        # Slash's loose resource files have priority over these PK3 archives.
        for source, target in [(native / 'valve/extras.pk3', game / 'valve/extras.pk3'),
                                (client / 'cstrike/extras.pk3', game / 'cstrike/extras.pk3')]:
            if not source.is_file():
                raise RuntimeError('Missing upstream resources: ' + str(source))
            # Optional touch/YaPB data is retained from upstream, but touch input
            # is disabled by the desktop config. Do not replace the native bots.
            shutil.copyfile(source, target)
        for folder in ('cl_dlls', 'dlls'):
            for source in (client / 'cstrike' / folder).iterdir():
                if source.suffix.lower() in {'.dll', '.dylib', '.so'} and source.name.lower().startswith(('client', 'menu', 'cs', 'mp')):
                    target = game / 'cstrike' / folder / source.name
                    target.parent.mkdir(exist_ok=True)
                    shutil.copy2(source, target)
        # Keep icons and application identity separate from Slash's game assets.
        if system == 'Linux':
            shutil.copyfile(icons / 'CounterStrike.png', game / 'CounterStrike.png')
        (game / 'Licenses').mkdir()
        (game / 'Licenses/Components.txt').write_text('''Xash3D FWGS: https://github.com/FWGS/xash3d-fwgs (GPL)
CS16Client/ReGameDLL/MainUI: https://github.com/FWGS/cs16-client (GPL)
Slash assets and scripts: supplied local cs-slash.rar; original download URL unknown.
Original Counter-Strike/Half-Life content belongs to its respective owners.
Upstream font licenses are preserved in extras.pk3.
''')
        if system == 'macOS':
            menu = game / 'cstrike/cl_dlls/menu_arm64.dylib'
            portable_freetype(menu, freetype)
            license_path = ROOT / 'Licenses/FreeType-FTL.txt'
            if not license_path.is_file():
                raise RuntimeError('Missing FreeType license: ' + str(license_path))
            shutil.copyfile(license_path, game / 'Licenses/FreeType-FTL.txt')
            with (game / 'Licenses/Components.txt').open('a') as notice:
                notice.write('This software uses the FreeType library; see FreeType-FTL.txt.\n')
            # Isolate settings from the previous clean edition.
            launcher = package / 'Counter-Strike.app/Contents/MacOS/CounterStrike'
            code = work / 'mac-launcher.c'
            original = code.read_text()
            code.write_text(original.replace('Application Support/Counter-Strike 1.6',
                                             'Application Support/Counter-Strike 1.6 Complete' if menu_style == 'default'
                                             else 'Application Support/Counter-Strike Slash'))
            pack.run('clang', '-arch', 'arm64', '-O2', '-mmacosx-version-min=13.0', code, '-o', launcher)
            pack.run('xattr', '-dr', 'com.apple.quarantine', package)
            pack.run('codesign', '--force', '--deep', '--sign', '-', package / 'Counter-Strike.app')
        elif system == 'Windows':
            goroot = Path(subprocess.check_output(['go', 'env', 'GOROOT'], text=True).strip())
            license_file = next(p for p in (goroot / 'LICENSE', goroot.parent / 'LICENSE') if p.is_file())
            shutil.copyfile(license_file, game / 'Licenses/Go.txt')
        shutil.copytree(package, dest, symlinks=True)
    print(system + ': assembled at ' + str(dest), flush=True)


def publish(system, source, output, menu_style='default'):
    stem = ('Counter-Strike-1.6-' if menu_style == 'default' else 'Counter-Strike-Slash-') + {'macOS': 'macos', 'Linux': 'linux', 'Windows': 'windows'}[system]
    if system == 'macOS':
        target = output / (stem + '.zip')
        with tempfile.TemporaryDirectory(prefix='mac-archive-', dir=output) as temporary:
            app = Path(temporary) / (stem + '.app')
            shutil.copytree(source / 'Counter-Strike.app', app, symlinks=True)
            pack.run('ditto', '-c', '-k', '--keepParent', app, target)
    elif system == 'Linux':
        target = output / (stem + '.tar.gz')
        with tarfile.open(target, 'w:gz', compresslevel=6) as archive:
            archive.add(source, arcname=stem)
    else:
        target = output / (stem + '.zip')
        with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for path in sorted(source.rglob('*')):
                if path.is_file():
                    archive.write(path, stem + '/' + path.relative_to(source).as_posix())
    print('Created ' + target.name, flush=True)
    return target


def main():
    if sys.version_info < (3, 12):
        raise RuntimeError('Python 3.12 or newer is required.')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', '--slash', dest='slash', type=Path, required=True,
                        help='Steam Half-Life folder with cstrike/ and valve/, or a Slash RAR/extracted folder')
    parser.add_argument('--downloads', type=Path, default=ROOT / 'downloads')
    parser.add_argument('--output', type=Path, default=ROOT / 'build/slash-ready', help='Must be absent or empty; never overwrites a release')
    parser.add_argument('--work', type=Path, default=ROOT / 'build/slash-package', help='Fresh build directory (must not exist)')
    parser.add_argument('--icons', type=Path, default=next((p for p in (ROOT / 'Icons', ROOT / 'Assets/Icons') if p.is_dir()), ROOT / 'build/distribution/icons'))
    parser.add_argument('--freetype', type=Path, help='macOS FreeType dylib; brew install freetype is another option')
    parser.add_argument('--fetch', action='store_true', help='Check current official releases and download/replace changed archives')
    parser.add_argument('--data-only', action='store_true', help='Prepare portable Slash data/configs for manual assembly; no runtime archives needed')
    parser.add_argument('--menu', choices=['default', 'slash'], default='default', help='Default upstream native menus (recommended), or legacy Slash artwork/colors')
    parser.add_argument('--platforms', nargs='+', choices=list(pack.PLATFORMS), default=list(pack.PLATFORMS))
    args = parser.parse_args()
    for field in ('slash', 'downloads', 'output', 'work', 'icons', 'freetype'):
        value = getattr(args, field)
        if value is not None:
            setattr(args, field, value.expanduser().resolve())
    if args.work.exists():
        raise RuntimeError('Use a fresh --work directory; already exists: ' + str(args.work))
    if args.output.exists() and any(args.output.iterdir()):
        raise RuntimeError('Use an empty --output directory: ' + str(args.output))
    args.work.mkdir(parents=True)
    args.output.mkdir(parents=True, exist_ok=True)
    pack.BUILD = args.work
    # These helpers need Scripts/ next to the builder, including the Go source.
    pack.ROOT = ROOT
    if args.fetch and not args.data_only:
        fetch_releases(args.downloads, args.platforms)
    for system in ([] if args.data_only else args.platforms):
        for name in pack.PLATFORMS[system][:2]:
            if not (args.downloads / name).exists():
                raise RuntimeError(f'Missing {name}; put it in --downloads or use --fetch.')
    source = args.slash
    if source.is_file():
        unpacked = args.work / 'slash-source'
        archive_extract(source, unpacked)
        candidates = [p.parent for p in unpacked.rglob('cstrike') if p.is_dir() and (p.parent / 'valve').is_dir()]
        if len(candidates) != 1:
            raise RuntimeError('Expected one cstrike/valve pair in Slash archive.')
        source = candidates[0]
    data = args.work / 'slash-data'
    report = make_data(source, data, args.menu)
    report['created_utc'] = datetime.now(timezone.utc).isoformat()
    report['source_archive_sha256'] = digest(args.slash) if args.slash.is_file() else None
    report['release_archives'] = {n: digest(args.downloads / n) for s in ([] if args.data_only else args.platforms) for n in pack.PLATFORMS[s][:2]}
    write_json(args.work / 'content-manifest.json', report)
    (data / 'slash-build.txt').write_text('Counter-Strike 1.6 native edition; Slash gameplay content\nMenu: ' + args.menu + '\n' + report['created_utc'] + '\n')
    if args.data_only:
        print('Prepared portable data: ' + str(data))
        return
    for system in args.platforms:
        dest = args.work / 'packages' / system
        assemble(system, data, args.downloads, dest, args.icons, args.work, args.freetype, args.menu)
        publish(system, dest, args.output, args.menu)
    print('Content inventory: ' + str(args.work / 'content-manifest.json'))


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, ValueError) as exc:
        raise SystemExit(str(exc))
