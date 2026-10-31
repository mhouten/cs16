#!/usr/bin/env python3
"""Upgrade an existing game with optional modes/maps without replacing its engine."""
import argparse
from datetime import datetime
import importlib.util
from pathlib import Path
import re

spec = importlib.util.spec_from_file_location('features', Path(__file__).with_name('optional-features.py'))
features = importlib.util.module_from_spec(spec)
spec.loader.exec_module(features)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument('--game', type=Path, help='Windows/Linux Game directory (or a test directory)')
    target.add_argument('--mac-app', type=Path, help='Installed Mac app; writes into user settings, not the signed app')
    parser.add_argument('--userdir', type=Path, help='Override Mac writable directory for portable/isolated profiles')
    parser.add_argument('--map', type=Path, action='append', default=[], help='Optional map ZIP (repeatable)')
    parser.add_argument('--bookmark', nargs=2, metavar=('NAME', 'HOST_PORT'))
    parser.add_argument('--protocol', choices=['native', 'goldsrc'], default='native')
    args = parser.parse_args()
    if args.mac_app:
        base = args.mac_app.expanduser().resolve() / 'Contents/Resources/Game'
        game = (args.userdir or Path.home() / 'Library/Application Support/Counter-Strike 1.6 Complete').expanduser().resolve()
    else:
        game = base = args.game.expanduser().resolve()
    if (not (base / 'cstrike').is_dir() or not (base / 'valve').is_dir()
            or not any((base / name).is_file() for name in ('xash3d', 'xash3d.exe'))):
        parser.error('Target must be this native Game installation with xash3d, cstrike/ and valve/.')
    if args.userdir and not args.mac_app:
        parser.error('--userdir is for a --mac-app profile; use --game for Windows/Linux.')
    if args.bookmark:
        name, host = args.bookmark
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,24}', name) or not re.fullmatch(r'[A-Za-z0-9.\[\]:_-]{1,253}', host):
            parser.error('Use a simple bookmark name and a hostname/IP:port, without spaces or commands.')
    backup = game / 'FeatureBackups' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    features.install(game, base, backup)
    for archive in args.map:
        result = features.import_maps(archive, game, base, backup)
        print(f'{archive.name}: {len(result["imported"])} new resources; existing files kept.')
    maps = features.refresh_maps(game, base, backup)
    if args.bookmark:
        name, host = args.bookmark
        relative = Path('cstrike/servers.cfg')
        text = (game / relative).read_text()
        alias = 'server_' + name
        text = '\n'.join(line for line in text.splitlines() if not line.startswith('alias ' + alias + ' ')) + '\n'
        text += f'alias {alias} "connect {host}' + (' gs' if args.protocol == 'goldsrc' else '') + '"\n'
        features._write(game, relative, text.encode(), backup)
        print('Bookmark command: ' + alias)
    print('Updated: ' + str(game))
    print(f'{len(maps)} maps listed. Start/restart the game; type mode_help for host modes or join_help for connections.')
    if backup.exists():
        print('Original changed files backed up in: ' + str(backup))


if __name__ == '__main__':
    main()
