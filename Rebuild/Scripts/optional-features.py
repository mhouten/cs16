"""Portable host presets and safe map import, shared by builder and upgrader."""
from pathlib import Path, PurePosixPath
import shutil
import stat
import zipfile

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'Features/cstrike'
RESOURCE_FOLDERS = {'maps', 'models', 'sound', 'sprites', 'gfx', 'overviews'}
RESOURCE_EXTENSIONS = {'.bsp', '.nav', '.res', '.txt', '.mdl', '.wav', '.mp3',
                       '.ogg', '.spr', '.tga', '.bmp', '.png', '.wad'}


def _write(game, relative, content, backup=None):
    target = game / relative
    if not target.resolve().is_relative_to(game.resolve()):
        raise ValueError('Refusing to write through an external symlink: ' + str(target))
    if target.is_file() and target.read_bytes() == content:
        return
    if backup and target.is_file():
        saved = backup / relative
        saved.parent.mkdir(parents=True, exist_ok=True)
        if not saved.exists():
            shutil.copy2(target, saved)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(content)


def install(game, base=None, backup=None):
    """Do not touch saved config.cfg, keys, identity, auth or menu resources."""
    game = Path(game)
    base = Path(base) if base else game
    written = []
    for source in sorted(SOURCE.rglob('*')):
        if source.is_file():
            rel = Path('cstrike') / source.relative_to(SOURCE)
            _write(game, rel, source.read_bytes(), backup)
            written.append(rel.as_posix())
    def existing(name):
        for folder in (game, base):
            p = folder / 'cstrike' / name
            if p.is_file():
                return p.read_text(encoding='latin1')
        return ''
    text = existing('game_init.cfg')
    if 'bot_enable 1' not in text.splitlines():
        text += '\n// Native bots must be enabled before GameDLL initialization.\nbot_enable 1\n'
    _write(game, Path('cstrike/game_init.cfg'), text.encode('latin1'), backup)
    written.append('cstrike/game_init.cfg')
    text = existing('autoexec.cfg')
    for command in ['exec optional_modes.cfg', 'exec servers.cfg']:
        if command not in text.splitlines():
            text += '\n' + command + '\n'
    _write(game, Path('cstrike/autoexec.cfg'), text.encode('latin1'), backup)
    written.append('cstrike/autoexec.cfg')
    for name in ('server.cfg', 'listenserver.cfg'):
        text = existing(name)
        command = 'exec modes/_reset.cfg'
        if command not in text.splitlines():
            text = command + '\n' + text
        _write(game, Path('cstrike') / name, text.encode('latin1'), backup)
        written.append('cstrike/' + name)
    # Preserve custom host rules, but provide the default if none exists.
    if not (game / 'cstrike/gwlistenserver.cfg').exists() and not (base / 'cstrike/gwlistenserver.cfg').exists():
        _write(game, Path('cstrike/gwlistenserver.cfg'),
               (ROOT / 'Defaults/cstrike/gwlistenserver.cfg').read_bytes(), backup)
        written.append('cstrike/gwlistenserver.cfg')
    if not (game / 'cstrike/servers.cfg').exists():
        _write(game, Path('cstrike/servers.cfg'), (SOURCE / 'servers.cfg.example').read_bytes(), backup)
        written.append('cstrike/servers.cfg')
    return written


def import_maps(archive_path, game, base=None, backup=None):
    """Import only new map resources; keep existing stock assets and binaries."""
    game = Path(game)
    base = Path(base) if base else game
    imported, skipped = [], []
    with zipfile.ZipFile(archive_path) as archive:
        for info in archive.infolist():
            if info.is_dir():
                continue
            name = info.filename.replace('\\', '/')
            rel = PurePosixPath(name)
            if rel.is_absolute() or '..' in rel.parts or ':' in name or stat.S_ISLNK(info.external_attr >> 16):
                raise ValueError('Unsafe map archive member: ' + name)
            # Accept common wrapper directories around a normal cstrike tree.
            parts = rel.parts
            start = next((i for i, p in enumerate(parts) if p.lower() in RESOURCE_FOLDERS), None)
            if start is not None:
                rel = PurePosixPath(*parts[start:])
            elif rel.suffix.lower() == '.wad':
                rel = PurePosixPath(rel.name)
            else:
                skipped.append(name)
                continue
            if rel.suffix.lower() not in RESOURCE_EXTENSIONS:
                skipped.append(name)
                continue
            if rel.parts[0].lower() == 'gfx' and (len(rel.parts) < 3 or rel.parts[1].lower() != 'env'):
                skipped.append(name)  # Map imports may add skies, never menu artwork.
                continue
            dest = Path('cstrike') / rel.as_posix()
            if (game / dest).exists() or (base / dest).exists():
                skipped.append(name)
                continue
            _write(game, dest, archive.read(info), backup)
            imported.append(dest.as_posix())
    return {'imported': imported, 'skipped': skipped}


def refresh_maps(game, base=None, backup=None):
    game = Path(game)
    base = Path(base) if base else game
    maps = sorted({p.stem for folder in (base, game)
                   for p in (folder / 'cstrike/maps').glob('*.bsp')})
    _write(game, Path('cstrike/mapcycle.txt'), ('\n'.join(maps) + '\n').encode(), backup)
    _write(game, Path('cstrike/maps.lst'), ('\n'.join(f'{m} "{m}"' for m in maps) + '\n').encode(), backup)
    return maps
