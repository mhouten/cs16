import importlib.util
from pathlib import Path
import tempfile
import unittest
import zipfile

spec = importlib.util.spec_from_file_location('features', Path(__file__).with_name('optional-features.py'))
features = importlib.util.module_from_spec(spec)
spec.loader.exec_module(features)


class UpgradeTests(unittest.TestCase):
    def test_documentation_upgrade_keeps_existing_manual_and_signed_base(self):
        with tempfile.TemporaryDirectory() as tmp:
            base, user = Path(tmp) / 'SignedGame', Path(tmp) / 'SavedGame'
            manual = base / 'cstrike/manual/manual.htm'
            manual.parent.mkdir(parents=True)
            manual.write_bytes(b'<html>Existing original manual</html>')
            (manual.parent / 'cssnet.css').write_bytes(b'body { color: black; }')
            before = {p.relative_to(base): p.read_bytes() for p in base.rglob('*') if p.is_file()}
            features.install_documentation(user, base)
            self.assertEqual(before, {p.relative_to(base): p.read_bytes() for p in base.rglob('*') if p.is_file()})
            self.assertEqual(manual.read_bytes(), (user / 'Documentation/CS-Manual.htm').read_bytes())
            self.assertEqual((manual.parent / 'cssnet.css').read_bytes(),
                             (user / 'Documentation/cssnet.css').read_bytes())
            self.assertFalse((user / 'cstrike/manual/manual.htm').exists())
            self.assertEqual((features.DOCUMENTATION / 'HL-Readme.txt').read_bytes(),
                             (user / 'readme.txt').read_bytes())
            self.assertEqual((user / 'readme.txt').read_bytes(), (user / 'valve/readme.txt').read_bytes())

    def test_upgrade_preserves_preferences_bookmarks_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            game = Path(tmp) / 'Game'
            (game / 'cstrike').mkdir(parents=True)
            original = b'name "My player"\ncon_fontscale 1.5\n'
            (game / 'cstrike/config.cfg').write_bytes(original)
            (game / 'cstrike/servers.cfg').write_text('alias my_friend "connect example.org:27015 gs"\n')
            (game / 'cstrike/autoexec.cfg').write_text('echo custom_startup\n')
            (game / 'cstrike/listenserver.cfg').write_text('mp_startmoney 1234\n')
            (game / 'cstrike/game_init.cfg').write_text('echo keep_custom_init\nbot_enable 0\n')
            backup = game / 'backups'
            features.install(game, backup=backup)
            once = (game / 'cstrike/autoexec.cfg').read_bytes()
            features.install(game, backup=backup)
            self.assertEqual(once, (game / 'cstrike/autoexec.cfg').read_bytes())
            self.assertEqual(original, (game / 'cstrike/config.cfg').read_bytes())
            self.assertIn('my_friend', (game / 'cstrike/servers.cfg').read_text())
            self.assertEqual('echo custom_startup\n', (backup / 'cstrike/autoexec.cfg').read_text())
            self.assertIn('mp_startmoney 1234', (game / 'cstrike/listenserver.cfg').read_text())
            self.assertIn('echo keep_custom_init', (game / 'cstrike/game_init.cfg').read_text())
            self.assertTrue((game / 'cstrike/game_init.cfg').read_text().endswith('bot_enable 1\n'))
            self.assertNotIn('exec modes/', once.decode())

    def test_mac_overlay_lists_packaged_and_user_maps_without_writing_the_app(self):
        with tempfile.TemporaryDirectory() as tmp:
            base, user = Path(tmp) / 'SignedGame', Path(tmp) / 'SavedGame'
            (base / 'cstrike/maps').mkdir(parents=True)
            (base / 'cstrike/maps/de_dust2.bsp').write_bytes(b'original')
            (user / 'cstrike/maps').mkdir(parents=True)
            (user / 'cstrike/maps/new_map.bsp').write_bytes(b'extra')
            features.install(user, base)
            self.assertEqual(['de_dust2', 'new_map'], features.refresh_maps(user, base))
            self.assertFalse((base / 'cstrike/autoexec.cfg').exists())

    def test_map_import_keeps_stock_assets_and_excludes_code_and_menu_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            game = Path(tmp) / 'Game'
            (game / 'cstrike/models').mkdir(parents=True)
            (game / 'cstrike/models/existing.mdl').write_bytes(b'original')
            archive = Path(tmp) / 'map.zip'
            with zipfile.ZipFile(archive, 'w') as z:
                for name in ['maps/new.bsp', 'models/existing.mdl', 'cl_dlls/client.dll',
                             'autoexec.cfg', 'gfx/shell/new_menu.tga', 'gfx/env/new_sky.tga']:
                    z.writestr('MapPack/cstrike/' + name, b'new')
            features.import_maps(archive, game)
            self.assertEqual(b'original', (game / 'cstrike/models/existing.mdl').read_bytes())
            self.assertTrue((game / 'cstrike/maps/new.bsp').exists())
            self.assertTrue((game / 'cstrike/gfx/env/new_sky.tga').exists())
            self.assertFalse((game / 'cstrike/cl_dlls/client.dll').exists())
            self.assertFalse((game / 'cstrike/autoexec.cfg').exists())
            self.assertFalse((game / 'cstrike/gfx/shell/new_menu.tga').exists())

    def test_startup_dispatcher_does_not_depend_on_saved_autoexec_or_userconfig(self):
        with tempfile.TemporaryDirectory() as tmp:
            base, user = Path(tmp) / 'SignedGame', Path(tmp) / 'SavedGame'
            (base / 'cstrike').mkdir(parents=True)
            (base / 'cstrike/autoexec.cfg').write_text('echo packaged_startup\n')
            (user / 'cstrike/userconfig.d').mkdir(parents=True)
            custom = user / 'cstrike/userconfig.d/my-settings.cfg'
            custom.write_text('echo personal_startup\n')
            features.install(user, base)
            hook = user / 'cstrike/userconfig.d/optional-features.cfg'
            self.assertEqual(['exec optional_modes.cfg', 'exec servers.cfg'],
                             [line for line in hook.read_text().splitlines()
                              if line and not line.startswith('//')])
            self.assertEqual('echo personal_startup\n', custom.read_text())
            self.assertFalse((base / 'cstrike/userconfig.d').exists())
            before = hook.read_bytes()
            features.install(user, base)
            self.assertEqual(before, hook.read_bytes())

    def test_map_import_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive = Path(tmp) / 'bad.zip'
            with zipfile.ZipFile(archive, 'w') as z:
                z.writestr('../maps/bad.bsp', b'bad')
            with self.assertRaises(ValueError):
                features.import_maps(archive, Path(tmp) / 'Game')


if __name__ == '__main__':
    unittest.main()
