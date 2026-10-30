#!/usr/bin/env python3
"""Copy CS 1.6 resources from a local installation or RAR SFX; never run it."""
import argparse
import ctypes as C
import ctypes.util
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import tempfile

ROOT = Path(__file__).resolve().parent.parent
EXTENSIONS = set('.bsp .wad .mdl .spr .wav .mp3 .ogg .tga .bmp .pcx .lmp .pal .res .txt .lst .sc .seq .png .jpg .jpeg .dds .ico .nav'.split())


def asset_path(name):
    """Return a normalized data path, excluding binaries, scripts and configs."""
    name = name.replace('\\', '/')
    p = PurePosixPath(name)
    if p.is_absolute() or '..' in p.parts or ':' in name:
        return None
    parts = p.parts
    for i, part in enumerate(parts):
        if part.lower() in ('valve', 'cstrike'):
            rel = PurePosixPath(part.lower(), *parts[i + 1:])
            if len(rel.parts) < 2:
                return None
            if any(s.lower() in ('addons', 'download', 'downloads', 'cache', 'cl_dlls', 'dlls') for s in rel.parts[1:-1]):
                return None
            if rel.name.lower() in ('liblist.gam', 'steam.inf') or rel.suffix.lower() in EXTENSIONS:
                return rel
            return None
    return None


def destination(root, rel):
    target = root.joinpath(*rel.parts)
    if not target.resolve().is_relative_to(root.resolve()):
        raise ValueError(f'Path escapes destination: {rel}')
    return target


def archive_assets(source, out):
    with source.open('rb') as stream:
        prefix = stream.read(1024 * 1024)
        offset = prefix.find(b'Rar!\x1a\x07')
        if offset > 0:
            # libarchive's RAR seeking assumes the archive begins at byte zero.
            with tempfile.TemporaryDirectory(prefix='cs16-rar-') as tmp:
                archive = Path(tmp) / 'resources.rar'
                stream.seek(offset)
                with archive.open('wb') as dst:
                    shutil.copyfileobj(stream, dst)
                return archive_assets(archive, out)
    library = ctypes.util.find_library('archive')
    if not library:
        raise RuntimeError('libarchive is required. On Debian/Ubuntu: sudo apt install libarchive13')
    lib = C.CDLL(library)
    signatures = {
        'archive_read_new': (C.c_void_p, []),
        'archive_read_support_filter_all': (C.c_int, [C.c_void_p]),
        'archive_read_support_format_all': (C.c_int, [C.c_void_p]),
        'archive_read_open_fd': (C.c_int, [C.c_void_p, C.c_int, C.c_size_t]),
        'archive_read_next_header': (C.c_int, [C.c_void_p, C.POINTER(C.c_void_p)]),
        'archive_entry_pathname': (C.c_char_p, [C.c_void_p]),
        'archive_entry_filetype': (C.c_uint, [C.c_void_p]),
        'archive_entry_hardlink': (C.c_char_p, [C.c_void_p]),
        'archive_read_data': (C.c_ssize_t, [C.c_void_p, C.c_void_p, C.c_size_t]),
        'archive_read_free': (C.c_int, [C.c_void_p]),
        'archive_error_string': (C.c_char_p, [C.c_void_p]),
    }
    for key, (restype, argtypes) in signatures.items():
        fn = getattr(lib, key)
        fn.restype, fn.argtypes = restype, argtypes
    handle = lib.archive_read_new()
    total = count = 0
    try:
        lib.archive_read_support_filter_all(handle)
        lib.archive_read_support_format_all(handle)
        with source.open('rb', buffering=0) as stream:
            if lib.archive_read_open_fd(handle, stream.fileno(), 65536) != 0:
                raise RuntimeError(lib.archive_error_string(handle).decode(errors='replace'))
            entry = C.c_void_p()
            buf = C.create_string_buffer(65536)
            while True:
                status = lib.archive_read_next_header(handle, C.byref(entry))
                if status == 1:
                    break
                if status != 0:
                    raise RuntimeError(lib.archive_error_string(handle).decode(errors='replace'))
                name = lib.archive_entry_pathname(entry).decode('utf-8', 'replace')
                rel = asset_path(name)
                if rel is None or lib.archive_entry_filetype(entry) != stat.S_IFREG or lib.archive_entry_hardlink(entry):
                    continue
                target = destination(out, rel)
                target.parent.mkdir(parents=True, exist_ok=True)
                # Do not overwrite existing user data on a repeated import.
                if target.exists():
                    continue
                try:
                    with target.open('xb') as dst:
                        while True:
                            size = lib.archive_read_data(handle, buf, len(buf))
                            if size < 0:
                                raise RuntimeError(lib.archive_error_string(handle).decode(errors='replace'))
                            if not size:
                                break
                            total += size
                            if total > 8 * 1024 ** 3:
                                raise RuntimeError('Resource import exceeds 8 GiB')
                            dst.write(buf.raw[:size])
                except BaseException:
                    target.unlink(missing_ok=True)
                    raise
                count += 1
    finally:
        lib.archive_read_free(handle)
    return count, total


def directory_assets(source, out):
    count = total = 0
    for parent, dirs, files in os.walk(source, followlinks=False):
        dirs[:] = [d for d in dirs if not (Path(parent) / d).is_symlink()]
        for name in files:
            src = Path(parent) / name
            rel = asset_path(src.relative_to(source).as_posix())
            if src.is_symlink() or not rel:
                continue
            dst = destination(out, rel)
            if dst.exists():
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)
            count += 1
            total += src.stat().st_size
    return count, total


def defaults(out):
    game = out / 'cstrike'
    game.mkdir(parents=True, exist_ok=True)
    # Use portable library basenames; Xash selects the architecture suffix.
    (game / 'gameinfo.txt').write_text('''title "Counter-Strike"
basedir "valve"
gamedir "cstrike"
gamedll "dlls/mp.dll"
gamedll_linux "dlls/cs.so"
gamedll_osx "dlls/cs.dylib"
dllpath "cl_dlls"
gamemode "multiplayer_only"
mp_entity "info_player_start"
startmap "de_dust2"
trainmap "tr_1"
nomodels 1
''')
    config = game / 'config.cfg'
    if not config.exists():
        config.write_text('''bind "ESCAPE" "cancelselect"
bind "`" "toggleconsole"
bind "~" "toggleconsole"
bind "w" "+forward"
bind "s" "+back"
bind "a" "+moveleft"
bind "d" "+moveright"
bind "SPACE" "+jump"
bind "CTRL" "+duck"
bind "SHIFT" "+speed"
bind "MOUSE1" "+attack"
bind "MOUSE2" "+attack2"
bind "MWHEELUP" "invprev"
bind "MWHEELDOWN" "invnext"
bind "r" "+reload"
bind "e" "+use"
bind "g" "drop"
bind "q" "lastinv"
bind "b" "buy"
bind "," "buyammo1"
bind "." "buyammo2"
bind "m" "chooseteam"
bind "TAB" "+showscores"
bind "y" "messagemode"
bind "u" "messagemode2"
bind "f" "impulse 100"
bind "t" "impulse 201"
bind "1" "slot1"
bind "2" "slot2"
bind "3" "slot3"
bind "4" "slot4"
bind "5" "slot5"
bind "6" "slot6"
bind "7" "slot7"
bind "8" "slot8"
bind "9" "slot9"
bind "0" "slot10"
name "LAN Player"
sensitivity "3"
volume "0.7"
hud_fastswitch "1"
cl_dynamiccrosshair "0"
''')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path, help='Folder containing valve/cstrike, or local RAR/SFX installer')
    parser.add_argument('--output', type=Path, default=ROOT / 'game-data')
    args = parser.parse_args()
    source, out = args.source.resolve(), args.output.resolve()
    if source == out or out.is_relative_to(source):
        parser.error('Output must be outside the source folder')
    out.mkdir(parents=True, exist_ok=True)
    count, size = directory_assets(source, out) if source.is_dir() else archive_assets(source, out)
    required = ['valve', 'cstrike/maps/de_dust2.bsp', 'cstrike/models/v_knife.mdl']
    missing = [p for p in required if not (out / p).exists()]
    if missing:
        raise RuntimeError('Incomplete CS 1.6 resources: ' + ', '.join(missing))
    defaults(out)
    report = {'source': str(source), 'files_copied': count, 'bytes_copied': size,
              'native_runtime_installed': False, 'windows_programs_executed': False}
    if source.is_file():
        with source.open('rb') as stream:
            report['source_sha256'] = hashlib.file_digest(stream, 'sha256').hexdigest()
    (out / 'import-report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'Imported {count} resource files ({size / 1024 ** 2:.1f} MiB) into {out}')


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, ValueError) as exc:
        raise SystemExit(str(exc))
