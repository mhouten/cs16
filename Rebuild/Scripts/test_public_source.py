"""Check rebuilding from Steam-style content without repack configuration."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('builder', Path(__file__).with_name('package-slash.py'))
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class PublicSourceTest(unittest.TestCase):
    def test_steam_content_uses_portable_defaults_without_player_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'steam'
            (source / 'cstrike/maps').mkdir(parents=True)
            (source / 'valve').mkdir()
            # Asset fixtures exercise import/configuration, not map loading.
            (source / 'cstrike/maps/de_dust2.bsp').write_bytes(b'map fixture')
            (source / 'cstrike/maps/fy_example.bsp').write_bytes(b'custom map fixture')
            (source / 'cstrike/config.cfg').write_text('name "Personal name"\ncon_fontscale 9\n')
            (source / 'cstrike/userconfig.cfg').write_text('alias private_alias "echo personal settings"\n')
            (source / 'valve/config.cfg').write_text('name "Half-Life personal name"\n')
            (source / 'valve/autoexec.cfg').write_text('rcon_password "personal-secret"\n')
            output = Path(tmp) / 'out'
            report = builder.make_data(source, output)
            config = (output / 'cstrike/config.cfg').read_text()
            aliases = (output / 'cstrike/userconfig.cfg').read_text()
            self.assertNotIn('Personal name', config)
            self.assertNotIn('private_alias', aliases)
            self.assertFalse((output / 'valve/config.cfg').exists())
            self.assertFalse((output / 'valve/autoexec.cfg').exists())
            self.assertIn('con_fontscale "2"', config)
            self.assertNotIn('con_fontscale', (output / 'cstrike/autoexec.cfg').read_text())
            self.assertIn('bot_enable 1', (output / 'cstrike/game_init.cfg').read_text())
            self.assertIn('mp_friendlyfire', (output / 'cstrike/gwlistenserver.cfg').read_text())
            self.assertEqual(report['maps'], ['de_dust2', 'fy_example'])
            self.assertEqual(report['source_profile'], 'Steam data and public maps')


if __name__ == '__main__':
    unittest.main()
