#!/usr/bin/env python3
"""Verify Slash content/native binaries and optionally load every map on macOS."""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import time


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def native_arch(path, system):
    blob = path.read_bytes()
    if system == 'Windows':
        pe = struct.unpack_from('<I', blob, 0x3c)[0]
        assert blob[:2] == b'MZ' and blob[pe:pe + 4] == b'PE\0\0'
        assert struct.unpack_from('<H', blob, pe + 4)[0] == 0x8664, path
    elif system == 'Linux':
        assert blob[:5] == b'\x7fELF\x02' and struct.unpack_from('<H', blob, 18)[0] == 62, path
    else:
        assert blob[:4] == b'\xcf\xfa\xed\xfe' and struct.unpack_from('<I', blob, 4)[0] == 0x100000c, path


def check_content(packages, manifest):
    result = {}
    for system, root, libraries in [
        ('macOS', 'macOS/Counter-Strike.app/Contents/Resources/Game',
         ['xash3d', 'cstrike/cl_dlls/client_arm64.dylib', 'cstrike/cl_dlls/menu_arm64.dylib', 'cstrike/dlls/cs_arm64.dylib']),
        ('Linux', 'Linux/Game', ['xash3d', 'cstrike/cl_dlls/client_amd64.so', 'cstrike/cl_dlls/menu_amd64.so', 'cstrike/dlls/cs_amd64.so']),
        ('Windows', 'Windows/Game', ['xash3d.exe', 'cstrike/cl_dlls/client_amd64.dll', 'cstrike/cl_dlls/menu_amd64.dll', 'cstrike/dlls/mp_amd64.dll']),
    ]:
        game = packages / root
        for name, expected in manifest['output_content_sha256'].items():
            assert digest(game / name) == expected, str(game / name)
        for name in libraries:
            native_arch(game / name, system)
        maps = sorted(p.stem for p in (game / 'cstrike/maps').glob('*.bsp'))
        assert maps == manifest['maps'], system
        assert (game / 'cstrike/mapcycle.txt').read_text().splitlines() == maps
        for name in ['hw.dll', 'sw.dll', 'Steam.dll', 'steamclient.dll',
                     'cstrike/cl_dlls/client.dll', 'cstrike/dlls/mp.dll']:
            assert not (game / name).exists(), name
        host = (game / 'cstrike/gwlistenserver.cfg').read_text()
        assert 'rcon_password ""' in host and 'sv_lan 1' in host
        assert 'bot_enable 1' in (game / 'cstrike/game_init.cfg').read_text()
        assert 'console 1' in (game / 'cstrike/autoexec.cfg').read_text()
        if manifest.get('menu_style') == 'default':
            for folder in ('cstrike', 'valve'):
                resource = game / folder / 'resource'
                assert not (resource / 'BackgroundLayout.txt').exists()
                assert not (resource / 'ClientScheme.res').exists()
                assert not (game / folder / 'gfx/shell/colors.lst').exists()
                assert not list((game / folder / 'gfx/shell').glob('*'))
            assert 'setinfo "_vgui_menus" "1"' in (game / 'cstrike/config.cfg').read_text()
            assert 'gl_max_size' not in (game / 'cstrike/userconfig.cfg').read_text()
        result[system] = {'maps': len(maps), 'navigation_files': len(list((game / 'cstrike/maps').glob('*.nav'))),
                          'verified_content_files': len(manifest['output_content_sha256']),
                          'menu_style': manifest.get('menu_style', 'slash'),
                          'native_architecture': 'arm64' if system == 'macOS' else 'x86_64'}
    native_arch(packages / 'Windows/Counter-Strike.exe', 'Windows')
    return result


def load_maps(app, maps, logdir):
    logdir.mkdir(parents=True, exist_ok=True)
    results = {}
    for index, name in enumerate(maps):
        with tempfile.TemporaryDirectory(prefix='slash-map-') as tmp:
            env = os.environ.copy()
            env.update(CS16_USERDIR=tmp, SDL_VIDEODRIVER='dummy', SDL_AUDIODRIVER='dummy')
            logfile = logdir / (name + '.log')
            with logfile.open('wb') as log:
                process = subprocess.Popen([str(app / 'Contents/MacOS/CounterStrike'), '-dedicated',
                                            '-noip', '-noip6', '+maxplayers', '16', '+map', name],
                                           env=env, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
                try:
                    end = time.monotonic() + 15
                    while time.monotonic() < end and process.poll() is None:
                        if b'16 player server started' in logfile.read_bytes():
                            break
                        time.sleep(.05)
                    passed = b'16 player server started' in logfile.read_bytes()
                    results[name] = 'passed' if passed else 'FAILED'
                finally:
                    if process.poll() is None:
                        process.terminate()
                        try:
                            process.wait(timeout=3)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait()
            if not passed:
                print(name + ': FAILED; ' + str(logfile), flush=True)
        if index % 10 == 9 or index == len(maps) - 1:
            print(f'Map startup checks: {index + 1}/{len(maps)}', flush=True)
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packages', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--mac-runtime', action='store_true')
    args = parser.parse_args()
    args.packages = args.packages.resolve()
    manifest = json.loads(args.manifest.read_text())
    result = check_content(args.packages, manifest)
    if args.mac_runtime:
        app = args.packages / 'macOS/Counter-Strike.app'
        subprocess.run(['codesign', '--verify', '--deep', '--strict', str(app)], check=True)
        for name in ['client_arm64.dylib', 'menu_arm64.dylib']:
            ctypes.CDLL(str(app / 'Contents/Resources/Game/cstrike/cl_dlls' / name))
        result['macOS']['client_and_menu_dlopen'] = True
        result['macOS']['signature_verified'] = True
        result['macOS']['map_startup_tests'] = load_maps(app, manifest['maps'], args.report.parent / 'map-logs')
        result['macOS']['network_disabled_in_tests'] = True
    result['limitations'] = ['Graphical menu/gameplay not tested: no agent display access.',
                             'Windows/Linux runtime and mixed-OS LAN not tested on native machines.',
                             'Original GoldSrc Slash server compatibility not verified.']
    args.report.write_text(json.dumps(result, indent=2) + '\n')
    assert not any(v == 'FAILED' for v in result['macOS'].get('map_startup_tests', {}).values()), 'Map startup failed'
    print('Verified content and native architectures for all three platforms.')


if __name__ == '__main__':
    main()
