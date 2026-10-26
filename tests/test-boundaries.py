"""Synthetic boundary/lock tests; no knowledge-base repository is required."""
_bootstrap = (__file__.rpartition('/')[0] or '.') + '/../engine/source_runtime.py'
with open(_bootstrap, 'rb') as _source:
    exec(compile(_source.read(), _bootstrap, 'exec'), {'__name__': '_publication_source_runtime'})
import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).absolute().parent
spec=importlib.util.spec_from_file_location('isolation_fixture',HERE/'test-publication-isolation.py')
fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)
pub,project=fixture.pub,fixture.project
import boundaries
import product_lock


class Contracts(fixture.Fixture,unittest.TestCase):
    def lock(self):
        files=[p for p in self.profile_path.rglob('*') if p.is_file()]
        data={'schema_version':1,'id':'synthetic','version':'1.0.0',
              'repository':'https://example.invalid/product','subdirectory':'.',
              **{k:self.config[k] for k in ('engine','profiles','source_repository')},
              'inputs':[{'path':str(p.relative_to(self.root)),'bytes':p.stat().st_size,
                         'sha256':pub.digest(p.read_bytes())} for p in sorted(files)]}
        (self.root/'product.json').write_text(json.dumps(data))
        _,identity,_=product_lock.inspect(self.root,pub)
        self.config['product']=identity
        self.descriptor.write_text(json.dumps(self.config))

    def test_lock_and_selected_inputs_are_bound_in_preparation(self):
        self.lock();run=self.prepared()
        self.assertEqual(json.loads((run/'run.json').read_text())['identity']['source']['product']['version'],'1.0.0')
        self.assertEqual((run/'inputs/product.json').read_bytes(),(self.root/'product.json').read_bytes())

    def test_product_drift_after_load_is_rejected_before_output(self):
        self.lock();selected=self.selected()
        (self.profile_path/'template.tex').write_text('changed')
        with self.assertRaisesRegex(pub.PreparationError,'lock mismatch'):pub.prepare(selected)
        self.assertFalse(self.output.exists())

    def test_new_undeclared_input_is_rejected(self):
        self.lock();(self.profile_path/'undeclared.tex').write_text('new input')
        with self.assertRaisesRegex(pub.PreparationError,'undeclared'):self.prepared()
        self.assertFalse(list(self.output.glob('preview/*/*/result.json')))

    def test_lock_cannot_be_rewritten_under_old_descriptor(self):
        self.lock()
        raw=json.loads((self.root/'product.json').read_text());raw['version']='1.1.0'
        (self.root/'product.json').write_text(json.dumps(raw))
        with self.assertRaisesRegex(pub.PreparationError,'identity changed'):self.selected()

    def test_root_overlap_and_link_ancestors_are_rejected(self):
        selected=self.selected()
        for target in (self.root/'new.json',self.engine/'pyproject.toml',self.engine/'latex/new',self.base):
            with self.subTest(target=target),self.assertRaises(pub.PreparationError):
                boundaries.for_project(target,selected,pub)
        link=self.base/'alias';link.symlink_to(self.root,target_is_directory=True)
        with self.assertRaises(OSError):boundaries.for_project(link/'new',selected,pub)

    def test_derived_tool_cannot_adopt_relocated_or_unbound_attempt(self):
        selected=self.selected();run=self.prepared()
        record=json.loads((run/'run.json').read_text())
        with patch('evidence.verify',return_value=(record,)):
            self.assertEqual(boundaries.for_attempt(run,pub),run)
            with self.assertRaisesRegex(pub.PreparationError,'bound output'):
                boundaries.for_attempt(self.root/'fake',pub)
        with patch('evidence.verify',return_value=({'identity':{}},)):
            with self.assertRaisesRegex(pub.PreparationError,'root bindings'):
                boundaries.for_attempt(run,pub)

    def test_case_alias_cannot_bypass_root_boundary(self):
        alias=self.root.with_name(self.root.name.upper())
        if not alias.exists():
            self.skipTest('case-sensitive filesystem; inode-alias test not applicable')
        with self.assertRaisesRegex(pub.PreparationError,'aliases'):
            boundaries.for_project(alias/'new',self.selected(),pub)


if __name__=='__main__':unittest.main(verbosity=2)
