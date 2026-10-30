#!/usr/bin/env python3
"""Install official FWGS development binaries, or cached release archives."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent.parent


def download(repo, filename, cache):
    cache.mkdir(parents=True, exist_ok=True)
    archive = cache / filename
    if not archive.is_file() and (ROOT / filename).is_file():
        archive = ROOT / filename
    if archive.is_file():
        print(f'Using local archive: {archive}')
        return archive, {'file': filename, 'sha256': digest(archive), 'source': 'local cache'}
    request = urllib.request.Request(
        f'https://api.github.com/repos/{repo}/releases/tags/continuous',
        headers={'User-Agent': 'CS16-LAN-setup', 'Accept': 'application/vnd.github+json'})
    with urllib.request.urlopen(request, timeout=30) as response:
        release = json.load(response)
    asset = next((a for a in release['assets'] if a['name'] == filename), None)
    if asset is None:
        raise RuntimeError(f'{repo} has no {filename}. Use the source build instead.')
    url = asset['browser_download_url']
    if not url.startswith(f'https://github.com/{repo}/releases/download/'):
        raise RuntimeError('Unexpected download origin')
    print(f'Downloading {url}', flush=True)
    partial = archive.with_suffix(archive.suffix + '.partial')
    try:
        with urllib.request.urlopen(url, timeout=60) as response, partial.open('wb') as dst:
            shutil.copyfileobj(response, dst)
        actual = digest(partial)
        expected = asset.get('digest')
        if expected and expected != 'sha256:' + actual:
            raise RuntimeError(f'Checksum mismatch: {filename}')
        partial.replace(archive)
    finally:
        partial.unlink(missing_ok=True)
    return archive, {'file': filename, 'sha256': actual, 'url': url,
                     'release_published_at': release['published_at'],
                     'github_digest_verified': bool(expected)}


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def unpack(archive, output):
    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as package:
            for member in package.infolist():
                if '\\' in member.filename:
                    raise RuntimeError('Unexpected backslash in release archive path')
                dest = output / member.filename
                if not dest.resolve().is_relative_to(output.resolve()):
                    raise RuntimeError('Unsafe release archive path')
                package.extract(member, output)
    else:
        with tarfile.open(archive) as package:
            package.extractall(output, filter='data')


def install(engine_archive, client_archive, target):
    runtime = ROOT / 'runtime' / target
    data = ROOT / 'game-data'
    with tempfile.TemporaryDirectory(prefix='cs16-install-') as tmp:
        tmp = Path(tmp)
        engine, client = tmp / 'engine', tmp / 'client'
        engine.mkdir()
        client.mkdir()
        unpack(engine_archive, engine)
        unpack(client_archive, client)
        engines = list(engine.rglob('xash3d'))
        if len(engines) != 1:
            raise RuntimeError('Expected one xash3d executable in the engine archive')
        game = client / 'cstrike'
        if not (game / 'cl_dlls').is_dir():
            raise RuntimeError('Expected cstrike/cl_dlls in the client archive')
        # Preserve relative framework links from the official macOS package.
        shutil.copytree(engines[0].parent, runtime, dirs_exist_ok=True, symlinks=True)
        shutil.copytree(game, data / 'cstrike', dirs_exist_ok=True)
    (runtime / 'xash3d').chmod(0o755)
    print(f'Installed native runtime in {runtime}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, default=ROOT / 'downloads')
    args = parser.parse_args()
    if sys.version_info < (3, 12):
        raise RuntimeError('Python 3.12 or newer is required for safe tar extraction')
    pair = platform.system(), platform.machine()
    targets = {
        ('Darwin', 'arm64'): ('macos-arm64', 'apple-arm64.tar.xz', 'macOS-arm64.zip'),
        ('Darwin', 'x86_64'): ('macos-x86_64', 'apple-amd64.tar.xz', 'macOS-x86_64.zip'),
        ('Linux', 'x86_64'): ('linux-x86_64', 'linux-amd64.tar.gz', 'Linux-x86_64.tar.gz'),
    }
    if pair not in targets:
        raise RuntimeError(f'No matching release pair for {pair}. Use Scripts/build-native.sh.')
    target, engine_suffix, client_suffix = targets[pair]
    engine, e_info = download('FWGS/xash3d-fwgs', 'xash3d-fwgs-' + engine_suffix, args.cache)
    client, c_info = download('FWGS/cs16-client', 'CS16Client-' + client_suffix, args.cache)
    install(engine, client, target)
    if platform.system() == 'Darwin':
        # The user authorized clearing quarantine on this local game installation.
        for directory in (ROOT / 'runtime' / target, ROOT / 'game-data/cstrike'):
            subprocess.run(['xattr', '-dr', 'com.apple.quarantine', str(directory)], check=True)
        subprocess.run([sys.executable, str(ROOT / 'Scripts/fix-macos-freetype.py')], check=True)
    (ROOT / 'runtime' / target / 'release-manifest.json').write_text(
        json.dumps({'engine': e_info, 'client': c_info}, indent=2) + '\n')
    print('Run ./play.command --map de_dust2 to test a local map first.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, ValueError, tarfile.TarError, zipfile.BadZipFile) as exc:
        raise SystemExit(str(exc))
