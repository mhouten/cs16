#!/usr/bin/env python3
"""Publish the prepared Windows/Linux/macOS assets after gh auth login."""
import argparse
import hashlib
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
PACKAGES = ['Counter-Strike-1.6-windows.zip', 'Counter-Strike-1.6-linux.tar.gz',
            'Counter-Strike-1.6-macos.zip']
EXTRAS = ['Rebuild-Kit.zip', 'SHA256SUMS.txt', 'VERIFICATION.json',
          'Clean-Old-Mac-Installs.command']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', default='mhouten/cs16')
    parser.add_argument('--tag', default='v2026.10.31')
    args = parser.parse_args()
    subprocess.run(['gh', 'auth', 'status', '--hostname', 'github.com'], check=True)
    for name in PACKAGES + EXTRAS:
        if not (ROOT / name).is_file():
            raise SystemExit('Missing release asset: ' + name)
    for line in (ROOT / 'SHA256SUMS.txt').read_text().splitlines():
        expected, name = line.split('  ', 1)
        path = ROOT / name
        if not path.is_relative_to(ROOT) or '..' in Path(name).parts:
            raise SystemExit('Unsafe checksum path: ' + name)
        with path.open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != expected:
                raise SystemExit('Checksum mismatch: ' + name)
    existing = subprocess.run(['gh', 'release', 'view', args.tag, '--repo', args.repo],
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if existing.returncode:
        subprocess.run(['gh', 'release', 'create', args.tag, '--repo', args.repo,
                        '--target', 'main', '--draft', '--title',
                        'Counter-Strike 1.6 — Windows, Linux, macOS',
                        '--notes-file', str(ROOT / 'RELEASE-NOTES.md')], check=True)
    # Uploads are sequential so a failed transfer can be resumed with this script.
    for name in PACKAGES + EXTRAS:
        print('Uploading ' + name, flush=True)
        subprocess.run(['gh', 'release', 'upload', args.tag, str(ROOT / name),
                        '--repo', args.repo, '--clobber'], check=True)
    subprocess.run(['gh', 'release', 'edit', args.tag, '--repo', args.repo,
                    '--draft=false', '--latest'], check=True)
    subprocess.run(['gh', 'release', 'view', args.tag, '--repo', args.repo,
                    '--json', 'url,assets'], check=True)


if __name__ == '__main__':
    try:
        main()
    except (OSError, subprocess.CalledProcessError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
