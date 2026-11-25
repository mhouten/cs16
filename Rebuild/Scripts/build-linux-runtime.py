#!/usr/bin/env python3
"""Fetch the locked sources and build the Linux runtime in the AlmaLinux 8 image."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
IMAGE = 'cs16-linux-build:glibc228'


def run(*args, **kwargs):
    subprocess.run(args, check=True, **kwargs)


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def fetch(path, spec):
    if path.exists():
        if digest(path) != spec['sha256']:
            raise ValueError(f'Checksum mismatch: {path}. Restore the exact locked archive.')
        return
    with tempfile.TemporaryDirectory(prefix='download-', dir=path.parent) as temporary:
        target = Path(temporary) / path.name
        request = urllib.request.Request(spec['url'], headers={'User-Agent': 'cs16-runtime-builder'})
        with urllib.request.urlopen(request, timeout=120) as response, target.open('xb') as stream:
            shutil.copyfileobj(response, stream)
        if digest(target) != spec['sha256']:
            raise ValueError(f'Checksum mismatch: {spec["url"]}')
        target.replace(path)


def assert_clean(path):
    tracked = subprocess.check_output(['git', '-C', path, 'status', '--porcelain',
                                       '--untracked-files=no', '--ignore-submodules=all'], text=True)
    untracked = subprocess.check_output(['git', '-C', path, 'ls-files', '--others', '-z'])
    if tracked or untracked:
        raise ValueError(f'Source checkout contains local files or changes: {path}. Use a separate cache.')


def checkout(path, spec):
    commit = spec['commit']
    if not path.exists():
        path.mkdir()
        run('git', 'init', path)
        run('git', '-C', path, 'remote', 'add', 'origin', spec['url'])
    if subprocess.run(['git', '-C', path, 'cat-file', '-e', f'{commit}^{{commit}}'],
                      stderr=subprocess.DEVNULL).returncode:
        run('git', '-C', path, 'fetch', '--depth', '1', spec['url'], commit)
    assert_clean(path)
    run('git', '-C', path, 'checkout', '--detach', commit)
    modules = spec['submodules']
    run('git', '-C', path, '-c', 'http.version=HTTP/1.1', 'submodule', 'update',
        '--init', '--recursive', '--checkout', '--depth', '1', '--jobs', '6', '--', *modules)
    status = subprocess.check_output(['git', '-C', path, 'submodule', 'status',
                                      '--recursive', '--', *modules], text=True)
    for row in status.splitlines():
        if row[0] != ' ':
            raise ValueError(f'Submodule does not match its pinned revision: {row}')
        relative = row[1:].split()[1]
        assert_clean(path / relative)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='Fresh runtime output directory')
    parser.add_argument('--jobs', type=int, default=min(os.cpu_count() or 1, 8))
    args = parser.parse_args()
    if args.jobs < 1:
        parser.error('--jobs must be positive')
    cache, output = args.cache.resolve(), args.output.resolve()
    if output.exists() or output.is_relative_to(cache) or cache.is_relative_to(output):
        parser.error('Use a fresh --output path separate from --cache.')
    assets = ROOT / 'Linux'
    lock = json.loads((assets / 'sources.json').read_text())
    cache.mkdir(parents=True, exist_ok=True)
    for name, spec in lock['archives'].items():
        fetch(cache / name, spec)
    for name in ('engine', 'client'):
        checkout(cache / ('upstream-' + name), lock[name])
    run('docker', 'build', '--platform', 'linux/amd64', '-t', IMAGE, assets)
    output.mkdir(parents=True)
    run('docker', 'run', '--rm', '--platform', 'linux/amd64', '--network', 'none',
        '--user', f'{os.getuid()}:{os.getgid()}', '-e', 'HOME=/tmp',
        '--mount', f'type=bind,src={cache},dst=/inputs,readonly',
        '--mount', f'type=bind,src={assets},dst=/recipe,readonly',
        '--mount', f'type=bind,src={ROOT / "Scripts"},dst=/scripts,readonly',
        '--mount', f'type=bind,src={output},dst=/output',
        IMAGE, 'bash', '/recipe/build-runtime.sh', str(args.jobs))


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as exc:
        sys.exit(str(exc))
