#!/usr/bin/env python3
"""Publish the prepared Windows/Linux/macOS assets after gh auth login."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
PACKAGES = ['Counter-Strike-1.6-windows.zip', 'Counter-Strike-1.6-linux.tar.gz',
            'Counter-Strike-1.6-macos.zip']
EXTRAS = ['Rebuild-Kit.zip', 'Optional-Features.zip', 'Documentation.zip', 'MODS.md', 'SHA256SUMS.txt', 'VERIFICATION.json',
          'Clean-Old-Mac-Installs.command']


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def remote_assets(repo, release_id):
    raw = subprocess.check_output(['gh', 'api', f'repos/{repo}/releases/{release_id}/assets',
                                   '--paginate', '--slurp'], text=True)
    return {asset['name']: asset for page in json.loads(raw) for asset in page}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', default='mhouten/cs16')
    parser.add_argument('--tag', required=True, help='Explicit release tag, e.g. v2026.11.25')
    parser.add_argument('--target', default='main', help='GitHub branch or commit to tag')
    args = parser.parse_args()
    subprocess.run(['gh', 'auth', 'status', '--hostname', 'github.com'], check=True)
    for name in PACKAGES + EXTRAS:
        if not (ROOT / name).is_file():
            raise SystemExit('Missing release asset: ' + name)
    checksums = {'SHA256SUMS.txt': digest(ROOT / 'SHA256SUMS.txt')}
    for line in (ROOT / 'SHA256SUMS.txt').read_text().splitlines():
        expected, name = line.split('  ', 1)
        path = ROOT / name
        if not path.is_relative_to(ROOT) or '..' in Path(name).parts:
            raise SystemExit('Unsafe checksum path: ' + name)
        if digest(path) != expected:
            raise SystemExit('Checksum mismatch: ' + name)
        checksums[name] = expected
    if missing := set(PACKAGES + EXTRAS) - checksums.keys():
        raise SystemExit('Missing checksums: ' + ', '.join(sorted(missing)))
    subprocess.run([sys.executable, str(ROOT / 'Rebuild/Scripts/audit-linux.py'),
                    str(ROOT / 'Counter-Strike-1.6-linux.tar.gz')], check=True)
    view = ['gh', 'release', 'view', args.tag, '--repo', args.repo,
            '--json', 'databaseId,isDraft,isPrerelease,targetCommitish,url']
    existing = subprocess.run(view, capture_output=True, text=True)
    if existing.returncode:
        if existing.stderr.strip() != 'release not found':
            raise SystemExit(existing.stderr.strip() or 'GitHub release lookup failed.')
        subprocess.run(['gh', 'release', 'create', args.tag, '--repo', args.repo,
                        '--target', args.target, '--draft', '--title',
                        'Counter-Strike 1.6 — Windows, Linux, macOS',
                        '--notes-file', str(ROOT / 'RELEASE-NOTES.md')], check=True)
    release = json.loads(subprocess.check_output(view, text=True))
    if release['targetCommitish'] != args.target or release['isPrerelease']:
        raise SystemExit('The existing release has a different target or is a prerelease.')
    release_id = release['databaseId']

    def matches(assets, name):
        asset = assets.get(name, {})
        return asset.get('state') == 'uploaded' and asset.get('digest') == 'sha256:' + checksums[name]

    assets = remote_assets(args.repo, release_id)
    pending = [name for name in PACKAGES + EXTRAS if not matches(assets, name)]
    if pending:
        if not release['isDraft']:
            raise SystemExit('Assets differ on the published release. Use a new tag.')
        for name in pending:
            print('Uploading ' + name, flush=True)
        subprocess.run(['gh', 'release', 'upload', args.tag, *(str(ROOT / name) for name in pending),
                        '--repo', args.repo, '--clobber'], check=True)
        assets = remote_assets(args.repo, release_id)
    if failed := [name for name in PACKAGES + EXTRAS if not matches(assets, name)]:
        raise SystemExit('GitHub asset verification failed: ' + ', '.join(failed))
    subprocess.run(['gh', 'release', 'edit', args.tag, '--repo', args.repo,
                    '--draft=false', '--latest'], check=True)
    print(json.loads(subprocess.check_output(view, text=True))['url'])


if __name__ == '__main__':
    try:
        main()
    except (OSError, subprocess.CalledProcessError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
