#!/usr/bin/env python3
_bootstrap = (__file__.rpartition('/')[0] or '.') + '/../../engine/source_runtime.py'
with open(_bootstrap, 'rb') as _source:
    exec(compile(_source.read(), _bootstrap, 'exec'), {'__name__': '_publication_source_runtime'})

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import configure


class ConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='product-config-', dir='/private/tmp')
        self.root = Path(self.tmp.name)
        self.content = self.root / 'content with spaces'
        self.content.mkdir()
        (self.content/'README.md').write_text('content sentinel\n')
        env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        for args in [('init', '-q'), ('add', 'README.md'),
                     ('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
                      '-c', 'commit.gpgsign=false', '-c', 'core.hooksPath=/dev/null', 'commit', '-qm', 'fixture')]:
            subprocess.run(['git', '-C', str(self.content), *args], env=env, check=True, capture_output=True)
        self.workspace = self.root / 'outside workspace'
        self.before = self.inventory(self.content)

    @staticmethod
    def inventory(root):
        return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in root.rglob('*') if p.is_file()}

    def tearDown(self):
        self.assertEqual(self.before, self.inventory(self.content))
        self.tmp.cleanup()

    def test_external_descriptor_and_engine_pin(self):
        path = configure.configure(self.content, self.workspace)
        config = json.loads(path.read_text())
        self.assertEqual(config['engine']['commit'], configure.PIN)
        self.assertEqual(config['product_root'], str(configure.PRODUCT))
        self.assertEqual(config['content_root'], str(self.content))
        self.assertEqual(len(config['profiles']), 6)
        selected = configure.project.load(configure.ENGINE, path, 'cpp-handbook', configure.pub)
        self.assertEqual(selected.output, self.workspace/'output')
        self.assertFalse(selected.output.exists())

    def test_existing_nonempty_workspace_is_unchanged(self):
        self.workspace.mkdir()
        (self.workspace/'history.bin').write_bytes(b'untouched')
        with self.assertRaises(configure.pub.PreparationError):
            configure.configure(self.content, self.workspace)
        self.assertEqual(list(self.workspace.iterdir()), [self.workspace/'history.bin'])
        self.assertEqual((self.workspace/'history.bin').read_bytes(), b'untouched')

    def test_repeat_configuration_never_overwrites(self):
        path = configure.configure(self.content, self.workspace)
        before = path.read_bytes()
        with self.assertRaises(configure.pub.PreparationError):
            configure.configure(self.content, self.workspace)
        self.assertEqual(path.read_bytes(), before)

    def test_content_descendant_rejected(self):
        with self.assertRaises(configure.pub.PreparationError):
            configure.configure(self.content, self.content/'publication/build')

    def test_content_ancestor_rejected(self):
        with self.assertRaises(configure.pub.PreparationError):
            configure.configure(self.content, self.root)

    def test_engine_cannot_be_content(self):
        with self.assertRaises(configure.pub.PreparationError):
            configure.configure(configure.ENGINE, self.workspace)
        self.assertFalse(self.workspace.exists())

    def test_product_and_engine_roots_rejected(self):
        for target in (configure.ENGINE, configure.PRODUCT, configure.PRODUCT/'output', configure.ENGINE/'engine/output'):
            with self.subTest(target=target), self.assertRaises(configure.pub.PreparationError):
                configure.configure(self.content, target)

    def test_linked_ancestor_never_touches_archive(self):
        archive = self.root/'archive'
        archive.mkdir()
        (archive/'history.bin').write_bytes(b'untouched')
        link = self.root/'link'
        link.symlink_to(archive, target_is_directory=True)
        with self.assertRaises(OSError):
            configure.configure(self.content, link/'new')
        self.assertEqual(list(archive.iterdir()), [archive/'history.bin'])

    def test_changed_product_is_rejected_before_output(self):
        copied = self.root/'product'
        shutil.copytree(configure.PRODUCT, copied, ignore=shutil.ignore_patterns('__pycache__'))
        (copied/'publication/profiles/cpp-handbook/template.tex').write_text('changed')
        with patch.object(configure, 'PRODUCT', copied), self.assertRaises(configure.pub.PreparationError):
            configure.configure(self.content, self.workspace)
        self.assertFalse(self.workspace.exists())

    def test_changed_pin_is_rejected_before_output(self):
        with patch.object(configure, 'PIN', '0'*40), self.assertRaises(configure.pub.PreparationError):
            configure.configure(self.content, self.workspace)
        self.assertFalse(self.workspace.exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
