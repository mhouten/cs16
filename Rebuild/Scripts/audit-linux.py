#!/usr/bin/env python3
"""Audit the x86-64 Linux package statically, then optionally use trusted ldd."""
import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile

INTERPRETER = '/lib64/ld-linux-x86-64.so.2'
HOST = {
    'ld-linux-x86-64.so.2', 'libc.so.6', 'libm.so.6', 'libdl.so.2',
    'libpthread.so.0', 'librt.so.1', 'libresolv.so.2', 'libutil.so.1',
    'libgcc_s.so.1', 'libstdc++.so.6',
}
CAPS = {'GLIBC': (2, 28), 'GLIBCXX': (3, 4, 25), 'CXXABI': (1, 3, 11), 'GCC': (7, 0, 0)}
REQUIRED = {
    'xash3d', 'libxash.so', 'filesystem_stdio.so', 'libmenu.so',
    'libref_gl.so', 'libref_gl4es.so', 'libref_gles1.so', 'libref_gles2.so',
    'libref_gles3compat.so', 'libref_null.so', 'libSDL2-2.0.so.0',
    'libavcodec.so.63', 'libavformat.so.63', 'libavutil.so.61',
    'libswresample.so.7', 'libswscale.so.10',
    'cstrike/cl_dlls/client_amd64.so', 'cstrike/cl_dlls/menu_amd64.so',
    'cstrike/dlls/cs_amd64.so',
}


def inspect(readelf, path):
    output = subprocess.check_output(
        [readelf, '-W', '-h', '-l', '-d', '-V', '-n', str(path)],
        text=True, stderr=subprocess.STDOUT,
    )
    definitions, requirements = set(), {}
    section = provider = None
    for line in output.splitlines():
        if line.startswith('Version '):
            section = line.split()[1]
        if section == 'needs':
            if match := re.search(r'File: (\S+)', line):
                provider = match[1]
            if match := re.search(r'Name: (\S+)', line):
                requirements.setdefault(provider, set()).add(match[1])
        if section == 'definition' and (match := re.search(r'Name: (\S+)', line)):
            definitions.add(match[1])
    return {
        'output': output,
        'interpreter': re.findall(r'Requesting program interpreter: ([^\]]+)', output),
        'paths': re.findall(r'\((RPATH|RUNPATH)\)[^\n]*\[([^\]]*)\]', output),
        'needed': re.findall(r'\(NEEDED\)[^\n]*\[([^\]]+)\]', output),
        'sonames': re.findall(r'\(SONAME\)[^\n]*\[([^\]]+)\]', output),
        'definitions': definitions,
        'requirements': requirements,
    }


def audit(root, readelf, host=False):
    root = root.resolve()
    rows, errors, objects = [], [], {}
    game = root / 'Game'
    if not game.is_dir() or not (root / 'Play').is_file() or not os.access(root / 'Play', os.X_OK):
        errors.append('Expected Game/ and executable Play at the package root')
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            if path.name in HOST:
                errors.append(f'{path.relative_to(root)}: host runtime alias must not be bundled')
            if not path.resolve().is_relative_to(root) or not path.resolve().is_file():
                errors.append(f'{path.relative_to(root)}: broken or external symlink')
            continue
        if not path.is_file():
            continue
        with path.open('rb') as stream:
            if stream.read(4) != b'\x7fELF':
                continue
        try:
            objects[path] = inspect(readelf, path)
        except subprocess.CalledProcessError as exc:
            errors.append(f'{path.relative_to(root)}: readelf failed: {exc.output.strip()}')
    for name in sorted(REQUIRED):
        if (game / name).resolve() not in objects:
            errors.append(f'Game/{name}: missing required ELF')
    if (game / 'xash3d').is_file() and not os.access(game / 'xash3d', os.X_OK):
        errors.append('Game/xash3d: missing executable bit')
    for path, data in objects.items():
        label = path.relative_to(root)
        output = data['output']
        if any(not re.search(pattern, output) for pattern in (
            r'Class:\s+ELF64', r'Data:.*little endian', r'Machine:.*X86-64',
            r'Type:\s+(DYN|EXEC)\b',
        )):
            errors.append(f'{label}: expected x86-64 little-endian executable or shared object')
        if re.search(r'x86 ISA needed:[^\n]*x86-64-v[234]', output):
            errors.append(f'{label}: requires a newer x86-64 instruction set baseline')
        expected = [INTERPRETER] if path == game / 'xash3d' else []
        if data['interpreter'] != expected or (not expected and re.search(r'Type:\s+EXEC\b', output)):
            errors.append(f'{label}: unexpected ELF interpreter or executable type')
        if {'AUDIT', 'DEPAUDIT', 'FILTER', 'AUXILIARY'} & set(re.findall(r'\(([A-Z_]+)\)', output)):
            errors.append(f'{label}: unsupported dynamic loader tag')
        if {path.name, *data['sonames']} & HOST:
            errors.append(f'{label}: host runtime libraries must not be bundled')
        directories = []
        for kind, value in data['paths']:
            for entry in value.split(':'):
                match = re.fullmatch(r'\$ORIGIN(?:/([a-zA-Z0-9_./-]+))?', entry)
                if not match:
                    errors.append(f'{label}: unsafe {kind} entry {entry!r}')
                    continue
                directory = (path.parent / (match[1] or '.')).resolve()
                if not directory.is_relative_to(game) or not directory.is_dir():
                    errors.append(f'{label}: {kind} entry leaves Game or does not exist: {entry}')
                    continue
                directories.append(directory)
        for library in sorted(set(data['needed']) | data['requirements'].keys()):
            if not re.fullmatch(r'[a-zA-Z0-9_.+-]+\.so(?:\.[a-zA-Z0-9_.+-]+)?', library):
                errors.append(f'{label}: unsafe dependency {library!r}')
                continue
            versions = data['requirements'].get(library, set())
            if library not in HOST:
                provider = next(((directory / library).resolve() for directory in directories
                                 if (directory / library).is_file()), None)
                if provider not in objects:
                    errors.append(f'{label}: unresolved private dependency {library}')
                elif missing := versions - objects[provider]['definitions']:
                    errors.append(f'{label}: {library} lacks {", ".join(sorted(missing))}')
            for version in sorted(versions):
                namespace, _, number = version.partition('_')
                if namespace in CAPS:
                    if not re.fullmatch(r'\d+(?:\.\d+)*', number) or tuple(map(int, number.split('.'))) > CAPS[namespace]:
                        errors.append(f'{label}: {library} requires {version} above the allowed ABI')
                elif library in HOST:
                    errors.append(f'{label}: unknown host ABI {library} {version}')
        rows.append(f'{label}\n'
                    f'  interpreter: {", ".join(data["interpreter"]) or "-"}\n'
                    f'  search paths: {data["paths"] or "-"}\n'
                    f'  needed: {", ".join(data["needed"]) or "-"}')
        rows.extend(f'  {lib}: {", ".join(sorted(versions))}'
                    for lib, versions in sorted(data['requirements'].items()))
    if host and not errors:
        env = {key: value for key, value in os.environ.items() if not key.startswith('LD_')}
        env['LC_ALL'] = 'C'
        for path in objects:
            if not objects[path]['needed'] and not objects[path]['interpreter']:
                continue
            result = subprocess.run(['ldd', '-v', str(path)], env=env,
                                    text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            if result.returncode or 'not found' in result.stdout:
                errors.append(f'{path.relative_to(root)}: host ldd failed\n{result.stdout.strip()}')
    return rows, errors, len(objects)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package', type=Path, help='Extracted package or trusted .tar.gz')
    parser.add_argument('--report', type=Path)
    parser.add_argument('--host', action='store_true', help='Use ldd on a trusted package after static validation, on Linux')
    args = parser.parse_args()
    readelf = next((path for name in ('readelf', 'greadelf', 'llvm-readelf')
                    if (path := shutil.which(name))), None)
    if not readelf:
        parser.error('Install GNU binutils (brew install binutils on macOS) and put readelf or greadelf on PATH.')
    if args.host and (sys.platform != 'linux' or not shutil.which('ldd')):
        parser.error('--host requires glibc Linux and ldd.')
    os.environ['LC_ALL'] = 'C'
    with tempfile.TemporaryDirectory(prefix='cs16-audit-') as tmp:
        root = args.package
        if not root.is_dir():
            with tarfile.open(root, 'r:gz') as archive:
                archive.extractall(tmp, filter='data')
            children = list(Path(tmp).iterdir())
            if len(children) != 1 or not children[0].is_dir():
                parser.error('Expected one package directory inside the archive.')
            root = children[0]
        rows, errors, count = audit(root, readelf, args.host)
    report = '\n'.join([
        'Counter-Strike 1.6 Linux ELF compatibility audit',
        'x86-64 | GLIBC <= 2.28 | GLIBCXX <= 3.4.25 | CXXABI <= 1.3.11 | GCC <= 7.0.0',
        f'{count} ELF objects | host dependency check: {"requested" if args.host else "static only"}',
        '', *rows, '', *(f'FAIL: {error}' for error in errors),
        f'{"FAIL" if errors else "PASS"} ({len(errors)} errors)', '',
    ])
    if args.report:
        args.report.write_text(report)
    print(report, end='')
    return bool(errors)


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, RuntimeError, ValueError, tarfile.TarError) as exc:
        sys.exit(str(exc))
