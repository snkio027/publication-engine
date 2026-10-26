#!/usr/bin/env python3
"""Product-specific source fidelity and rejection tests; no hardware claims."""
_bootstrap = (__file__.rpartition('/')[0] or '.') + '/../../engine/source_runtime.py'
with open(_bootstrap, 'rb') as _source:
    exec(compile(_source.read(), _bootstrap, 'exec'), {'__name__': '_publication_source_runtime'})
import argparse
import copy
import importlib.util
import json
import hashlib
import re
from pathlib import Path
import subprocess
import sys
import unittest

HERE = Path(__file__).absolute().parent
sys.path.insert(0, str(HERE.parents[1] / 'engine'))
import fidelity
import preview
import source_model
import pub

parser = argparse.ArgumentParser()
parser.add_argument('--content', type=Path, required=True)
args = parser.parse_args()
profile = HERE / 'publication/profiles/robotics-handbook'
config = json.loads((profile/'profile.json').read_text())
source = config['sources'][0]
raw = source_model.blob(args.content, source['revision'], source['path'], pub)
original = json.loads(subprocess.check_output(['pandoc', '-f', config['source_format'], '-t', 'json'], input=raw))
spec = importlib.util.spec_from_file_location('robotics_adapter', profile/'adapter.py')
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


class RoboticsAdapterTests(unittest.TestCase):
    def adapted(self):
        return fidelity.adapt_checked(original, adapter, source, preview.text)

    def test_fixed_source_bytes(self):
        self.assertEqual(pub.digest(raw), 'bb7e3b010fce93a9eb338271264467bc177c70a21cdeb3bb0123d9e5d781663b')
        self.assertEqual(len(raw), 64208)

    def test_identity_not_promoted(self):
        ast, meta, aliases, semantic, saved, report = self.adapted()
        self.assertEqual(meta['status'], 'proposed-learning-baseline')
        self.assertEqual(meta['version'], '1.0.0')
        self.assertEqual(ast['meta'], original['meta'])
        self.assertEqual(report['status'], 'SOURCE_FIDELITY_PASS')

    def test_all_explicit_targets_retained(self):
        semantic = self.adapted()[3]
        identifiers = {item['id'] for item in semantic if item['kind']=='source-target'}
        self.assertEqual(identifiers, {f'sec{n:02}' for n in range(1,24)} |
                         {f'S{n:02}' for n in range(1,31)} | {'references'})

    def test_all_code_and_relations_preserved(self):
        ast, meta, aliases, semantic, saved, report = self.adapted()
        before, after = fidelity.projection(original), fidelity.projection(ast)
        # Character comparison also needs the engine's split-HTML-anchor
        # normalization; never compare raw <a> tag text as printable prose.
        for field in ('headers', 'code', 'links', 'tables', 'lists'):
            self.assertEqual(before[field], after[field])
        self.assertEqual(fidelity.check(original, ast, aliases, semantic)['status'], 'SOURCE_FIDELITY_PASS')
        self.assertEqual(len(fidelity.projection(ast)['code']), 4)

    def test_false_acceptance_rejected(self):
        changed = copy.deepcopy(original)
        changed['meta']['status'] = {'t':'MetaString', 'c':'ACCEPTED'}
        with self.assertRaisesRegex(RuntimeError, 'identity drift'):
            adapter.adapt(changed, source, preview.text)

    def test_reference_keep_targets_exact(self):
        theme = (profile/'theme.sty').read_text()
        targets = re.findall(r'\\RoboticsReferenceKeep\{([^}]+)\}', theme)
        expected = ['ROBOTICS-HANDBOOK-' + hashlib.sha256(f'S{i:02}'.encode()).hexdigest()[:16]
                    for i in range(1, 31)]
        self.assertEqual(targets, expected)
        self.assertIn(r'\Needspace{2.4\baselineskip}', theme)

    def test_unknown_markup_rejected(self):
        changed = copy.deepcopy(original)
        changed['blocks'].append({'t':'RawBlock','c':['html','<script>unsafe()</script>']})
        with self.assertRaisesRegex(RuntimeError, 'unsupported robotics markup'):
            adapter.adapt(changed, source, preview.text)

    def test_code_mutation_rejected(self):
        ast, meta, aliases, semantic, saved, report = self.adapted()
        code = next(n for n in fidelity.walk(ast['blocks']) if n['t']=='CodeBlock')
        code['c'][1] += '\nchanged'
        with self.assertRaisesRegex(RuntimeError, 'source fidelity mismatch'):
            fidelity.check(original, ast, aliases, semantic)

    def test_anchor_moved_to_wrong_paragraph_rejected(self):
        ast, meta, aliases, semantic, saved, report = self.adapted()
        owner = next(n for n in ast['blocks'] if n['t']=='Para' and any(
            x['t']=='Span' and x['c'][0][0]=='S01' for x in n['c']))
        target = next(n for n in ast['blocks'] if n['t']=='Para' and any(
            x['t']=='Span' and x['c'][0][0]=='S02' for x in n['c']))
        span = next(x for x in owner['c'] if x['t']=='Span' and x['c'][0][0]=='S01')
        owner['c'].remove(span)
        target['c'].insert(0, span)
        with self.assertRaisesRegex(RuntimeError, 'source block target moved'):
            fidelity.check(original, ast, aliases, semantic)


if __name__ == '__main__':
    unittest.main(argv=[sys.argv[0]], verbosity=2)
