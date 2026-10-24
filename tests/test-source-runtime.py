"""Real subprocess counterexamples: executable caches cannot bypass the source pin."""
import importlib.util
import json
import py_compile
import struct
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
_bootstrap = HERE.parent / 'engine/source_runtime.py'
exec(compile(_bootstrap.read_bytes(), str(_bootstrap), 'exec'), {'__name__': '_publication_source_runtime'})
spec = importlib.util.spec_from_file_location('isolation', HERE / 'test-publication-isolation.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)


class SourceRuntimeTests(base.Fixture, unittest.TestCase):
    def poison(self, module, marker, timestamp=False, legacy=False):
        source = self.engine / 'engine' / (module + '.py')
        original = source.read_bytes()
        mutant = self.base / 'cache-mutant.py'
        mutant.write_bytes(('from pathlib import Path\nPath(' + repr(str(self.dist / 'history.bin')) +
                            ').write_text(' + repr(marker) + ')\n').encode() + original)
        target = source.with_suffix('.pyc') if legacy else Path(importlib.util.cache_from_source(str(source)))
        mode = py_compile.PycInvalidationMode.TIMESTAMP if timestamp else py_compile.PycInvalidationMode.UNCHECKED_HASH
        py_compile.compile(str(mutant), cfile=str(target), dfile=str(source), doraise=True, invalidation_mode=mode)
        if timestamp:
            raw = target.read_bytes()
            target.write_bytes(raw[:8] + struct.pack('<II', int(source.stat().st_mtime) & 0xffffffff, len(original)) + raw[16:])
        self.assertEqual(source.read_bytes(), original)
        return source, target

    def prepare(self):
        result = self.cli('preview', '--prepare-only')
        self.assertEqual(result.returncode, 0, result.stderr)
        record = json.loads(result.stdout)
        self.assertEqual(record['status'], 'PREPARED')
        self.assertEqual(base.tree_bytes(self.dist), self.dist_before)
        return record

    def test_unchecked_caches_cannot_change_behavior_or_identity(self):
        self.prepare()
        baseline = None
        for marker in ('FIRST_CACHE', 'SECOND_CACHE'):
            for module in ('environment', 'project', 'source_model', 'source_runtime'):
                self.poison(module, marker)
            record = self.prepare()
            if baseline is not None:
                self.assertEqual(record['build_id'], baseline['build_id'])
            baseline = record  # Fixture Git also records the untracked cache names.

    def test_timestamp_cache_ignored_even_with_matching_source_stat(self):
        self.poison('environment', 'TIMESTAMP_CACHE', timestamp=True)
        self.prepare()

    def test_counterexample_cache_is_executable_without_policy(self):
        # Positive control: -B alone really does load these bytes on this runtime.
        self.poison('source_runtime', 'CONTROL_EXECUTED')
        process = subprocess.run([sys.executable, '-B', '-c',
            'import sys; sys.path.insert(0, ' + repr(str(self.engine / 'engine')) + '); import source_runtime'],
            cwd=self.base, capture_output=True, text=True)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual((self.dist / 'history.bin').read_text(), 'CONTROL_EXECUTED')
        (self.dist / 'history.bin').write_bytes(self.dist_before['history.bin'])
        self.prepare()  # The policy itself is bootstrapped from source, not its cache.

    def test_sourceless_cache_fails_without_executing(self):
        source, _ = self.poison('environment', 'SOURCELESS', legacy=True)
        source.unlink()  # Disposable fixture only; unsupported context must fail closed.
        result = self.cli('preview', '--prepare-only')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('rejects bytecode-only module', result.stderr)
        self.assertNotIn('PREPARED', result.stdout)
        self.assertFalse(self.output.exists())

    def test_explicit_source_loader_ignores_unchecked_cache(self):
        source, _ = self.poison('source_runtime', 'EXPLICIT_LOADER')
        script = ('from pathlib import Path\nimport importlib.util\n'
                  'p=Path(' + repr(str(source)) + ')\n'
                  'exec(compile(p.read_bytes(), str(p), "exec"), {})\n'
                  's=importlib.util.spec_from_file_location("policy_test", p)\n'
                  's.loader.exec_module(importlib.util.module_from_spec(s))\n')
        result = subprocess.run([sys.executable, '-B', '-c', script], cwd=self.base, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_review_entrypoints_ignore_poisoned_evidence_cache(self):
        self.poison('evidence', 'REVIEW_CACHE')
        for name in ('reading-review.py', 'inspect-pages.py'):
            with self.subTest(tool=name):
                result = subprocess.run([sys.executable, '-B', str(self.engine / 'tools' / name),
                    str(self.base / 'missing-attempt')], cwd=self.base, capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('missing-attempt', result.stderr)
                self.assertEqual(base.tree_bytes(self.dist), self.dist_before)


if __name__ == '__main__':
    unittest.main(verbosity=2)
