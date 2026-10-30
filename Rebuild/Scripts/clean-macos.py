#!/usr/bin/env python3
"""Move this project's old Mac installations and saved settings to the Trash.

Run in Terminal as your normal macOS user, outside an agent filesystem sandbox.
Game assets/source archives and new packages beside this script are preserved.
"""
from datetime import datetime
import os
from pathlib import Path
import plistlib
import shutil
import signal
import subprocess
import sys


IDENTIFIERS = {'local.cs16.lan', 'local.counterstrike.cs16', 'local.counterstrike.slash',
               'local.counterstrike.complete'}
APP_NAMES = {'CS 1.6.app', 'Counter-Strike.app', 'Counter-Strike-1.6-macos.app',
             'Counter-Strike-Slash-macos.app'}
SETTINGS = ['Counter-Strike 1.6', 'Counter-Strike Slash', 'Counter-Strike 1.6 Complete']


def main():
    if sys.platform != 'darwin':
        raise SystemExit('This cleanup tool is for macOS only.')
    # Stop only engine processes launched from these Counter-Strike app bundles.
    processes = subprocess.run(['pgrep', '-f', r'/Counter-Strike[^/]*\.app/Contents/(Resources/Game/xash3d|MacOS/CounterStrike)'],
                               text=True, capture_output=True)
    for value in processes.stdout.split():
        try:
            os.kill(int(value), signal.SIGTERM)
        except ProcessLookupError:
            pass
    trash = Path.home() / '.Trash' / ('Counter-Strike cleanup ' + datetime.now().strftime('%Y%m%d-%H%M%S'))
    candidates = []
    for base in (Path('/Applications'), Path.home() / 'Applications'):
        if not base.is_dir():
            continue
        for app in base.glob('*.app'):
            try:
                info = plistlib.loads((app / 'Contents/Info.plist').read_bytes())
            except (OSError, plistlib.InvalidFileException):
                info = {}
            if app.name in APP_NAMES or info.get('CFBundleIdentifier') in IDENTIFIERS:
                candidates.append(app)
    candidates += [Path.home() / 'Library/Application Support' / name for name in SETTINGS]
    candidates += [Path.home() / 'Library/Preferences' / (name + '.plist') for name in IDENTIFIERS]
    candidates += [Path.home() / 'Library/Caches' / name for name in IDENTIFIERS]
    failures = []
    for source in candidates:
        if not source.exists():
            continue
        group = ('System Applications' if source.parent == Path('/Applications') else
                 'User Applications' if source.parent == Path.home() / 'Applications' else source.parent.name)
        target = trash / group / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.move(str(source), target)
            print('Removed:', source)
        except OSError as exc:
            failures.append(str(source))
            print('Could not remove:', source, '-', exc, file=sys.stderr)
    if failures:
        raise SystemExit('Move the listed remaining items to Trash in Finder (administrator access may be required).')
    print('Old Counter-Strike installations and settings are cleared.')
    print('Backups are in:', trash)
    print('Remove obsolete Counter-Strike Dock shortcuts, then install the new Mac app.')


if __name__ == '__main__':
    main()
