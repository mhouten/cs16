"""Regression fixtures for the Linux release ELF gate."""
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('linux_audit', Path(__file__).with_name('audit-linux.py'))
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


@unittest.skipUnless(sys.platform == 'linux' and os.uname().machine == 'x86_64'
                     and shutil.which('cc') and shutil.which('readelf'), 'requires x86-64 Linux build tools')
class LinuxAuditTests(unittest.TestCase):
    def setUp(self):
        work = tempfile.TemporaryDirectory()
        self.addCleanup(work.cleanup)
        self.root = Path(work.name)
        self.package = self.root / 'package with spaces'
        self.game = self.package / 'Game'
        self.game.mkdir(parents=True)
        (self.package / 'Play').touch(mode=0o755)
        (self.root / 'provider.c').write_text('int abi_probe(void) { return 0; }\n')
        (self.root / 'main.c').write_text('int abi_probe(void); void _start(void) { abi_probe(); }\n')

    def compile(self, version='GLIBC_2.28', runpath='$ORIGIN', interpreter=audit.INTERPRETER):
        versions = self.root / 'versions'
        versions.write_text(f'{version} {{ global: abi_probe; }};\n')
        subprocess.run(['cc', '-fPIC', '-shared', '-nostdlib', '-o', self.game / 'libfixture.so',
                        self.root / 'provider.c', '-Wl,-soname,libfixture.so',
                        f'-Wl,--version-script={versions}'], check=True)
        subprocess.run(['cc', '-nostdlib', '-pie', '-o', self.game / 'xash3d',
                        self.root / 'main.c', '-L' + str(self.game), '-lfixture',
                        f'-Wl,-rpath,{runpath}', f'-Wl,--dynamic-linker,{interpreter}'], check=True)

    def errors(self):
        with patch.object(audit, 'REQUIRED', {'xash3d', 'libfixture.so'}):
            return audit.audit(self.package, 'readelf')[1]

    def test_relocatable_private_provider(self):
        self.compile()
        self.assertEqual(self.errors(), [])

    def test_rejects_new_symbol_and_missing_provider(self):
        self.compile(version='GLIBC_2.43')
        self.assertTrue(any('GLIBC_2.43' in error for error in self.errors()))
        (self.game / 'libfixture.so').unlink()
        self.assertTrue(any('unresolved private dependency' in error for error in self.errors()))

    def test_rejects_host_alias_and_unsafe_runpath(self):
        self.compile(runpath='/tmp/build', interpreter='/tmp/ld-linux.so')
        (self.game / 'libc.so.6').symlink_to('libfixture.so')
        errors = self.errors()
        for message in ('unexpected ELF interpreter', 'unsafe RUNPATH', 'host runtime alias'):
            self.assertTrue(any(message in error for error in errors), errors)
