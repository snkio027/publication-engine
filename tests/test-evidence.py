"""Adversarial protocol fixtures use actual evidence/candidate/review entry points."""
import copy
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'engine'))
import pub, evidence, fidelity, preview, source_model
spec=importlib.util.spec_from_file_location('isolation',HERE/'test-publication-isolation.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='kb-evidence-');self.addCleanup(self.tmp.cleanup)
        self.run=Path(self.tmp.name)
        self.identity={'publication':{'views':['TEST-A'], 'sources':[{'id':'DOC-A','path':'a.md'}]}}
        self.source={'build_id':pub.digest(pub.canonical(self.identity)), 'identity':self.identity}
        execution={'preparation_id':self.source['build_id'],'tools':{'pdftoppm':{'version':'fixture','sha256':'fixture'}}}
        self.report={'status':'BUILT_FOR_REVIEW','source_build_id':self.source['build_id'],
                     'execution_identity':execution,'execution_id':pub.digest(json.dumps(execution,sort_keys=True,separators=(',',':')).encode()),
                     'views':[{'view':'TEST-A','pdf':'output/pdf/a.pdf','sha256':pub.digest(b'PDF'),
                               'pages':1,'rendered_pages':1,'overfull_hbox_pt':[],**{k:[] for k in (
                                   'missing_text_blocks','missing_table_row_relations','section_errors','inline_literal_errors','orphan_headings','navigation_errors')}}]}
        self.write('run.json',self.source);self.write('result.json',{'status':'PREPARED'})
        for name,data in {'output/pdf/a.pdf':b'PDF','output/source/a.md':b'source','output/README.md':b'index',
                          'renders/TEST-A/page-1.png':b'PNG','source-catalog.json':b'[]','worker.log':b'closed worker',
                          **{'source-ast/DOC-A'+s:b'{}' for s in ('.json','.original.json','.fidelity.json')},
                          **{'typeset/TEST-A/'+n:b'{}' for n in ('composed.json','document.tex','document.log','document.fls',
                              'reference-map.json','table-map.json','section-audit.json','reading-components.json','audit.json')}}.items():
            self.write('work/'+name,data)
        self.write('work/preview-audit.json',self.report)
        self.write('work/source-ast/DOC-A.fidelity.json',{'status':'SOURCE_FIDELITY_PASS',
            'original_ast_sha256':fidelity.sha({}), 'adapted_ast_sha256':fidelity.sha({})})
        self.ready={'status':'PREVIEW_READY','mode':'FULL_PREVIEW','evidence_schema':1,
                    'execution_id':self.report['execution_id'],'audit_sha256':pub.digest((self.run/'work/preview-audit.json').read_bytes()),
                    'artifacts':{'output/pdf/a.pdf':pub.digest(b'PDF')},'artifact_manifest_sha256':evidence.seal(self.run,pub)}
        self.write('preview-result.json',self.ready)

    def write(self,path,value):
        p=self.run/path;p.parent.mkdir(parents=True,exist_ok=True)
        p.write_bytes(value if isinstance(value,bytes) else pub.canonical(value)+b'\n')

    def test_complete_manifest_passes(self):
        self.assertEqual(evidence.verify(self.run)[3]['views'],['TEST-A'])

    def test_mutated_machine_evidence_and_png_refused(self):
        for path in ('source-ast/DOC-A.json','source-ast/DOC-A.original.json','source-catalog.json','worker.log',
                     'typeset/TEST-A/reference-map.json','typeset/TEST-A/document.tex','renders/TEST-A/page-1.png'):
            with self.subTest(path=path):
                p=self.run/'work'/path;old=p.read_bytes();p.chmod(0o600);p.write_bytes(old+b'changed')
                with self.assertRaises(pub.PreparationError): evidence.verify(self.run)
                p.write_bytes(old)

    def test_candidate_calls_binding_before_copy(self):
        import candidate
        self.write('work/source-ast/DOC-A.json',b'changed')
        with pub.root_handle(self.run) as fd, self.assertRaisesRegex(pub.PreparationError,'artifact digest changed'):
            candidate.payload(fd,pub)

    def test_missing_planned_view_fails_before_success_commit(self):
        self.source['identity']['publication']['views'].append('TEST-B')
        self.write('run.json',self.source)
        (self.run/'preview-result.json').unlink()
        with self.assertRaisesRegex(pub.PreparationError,'view set'): evidence.seal(self.run,pub)
        self.assertFalse((self.run/'preview-result.json').exists())

    def test_empty_and_duplicate_views_rejected(self):
        for views in ([],self.report['views']*2):
            report={**self.report,'views':views}
            with self.assertRaises(pub.PreparationError): evidence.check_report(self.source,report,pub)

    def test_extra_or_missing_evidence_rejected(self):
        p=self.run/'work/typeset/TEST-A/unlisted.txt';p.write_text('extra')
        with self.assertRaises(pub.PreparationError): evidence.verify(self.run)
        p.unlink();(self.run/'work/source-ast/DOC-A.original.json').unlink()
        with self.assertRaises(pub.PreparationError): evidence.verify(self.run)

    def test_manifest_symlink_rejected(self):
        p=self.run/'work/artifact-manifest.json';data=p.read_bytes();p.unlink()
        self.write('other.json',data);p.symlink_to(self.run/'other.json')
        with self.assertRaises(OSError): evidence.verify(self.run)

    def test_fast_and_legacy_results_cannot_freeze(self):
        for change in ({'mode':'QUICK_CHECK'},{'evidence_schema':0}):
            self.write('preview-result.json',{**self.ready,**change})
            with self.assertRaises(pub.PreparationError): evidence.verify(self.run)

    def test_optimized_review_entrypoints_fail_closed(self):
        for tool in ('reading-review.py','inspect-pages.py'):
            for optimize in ('0','1','2'):
                for case in ('failed','digest','empty','png'):
                    self.write('preview-result.json',self.ready)
                    self.write('work/preview-audit.json',self.report)
                    self.write('work/renders/TEST-A/page-1.png',b'PNG')
                    if case=='failed': self.write('preview-result.json',{**self.ready,'status':'FAILED'})
                    elif case=='digest': self.write('preview-result.json',{**self.ready,'audit_sha256':'wrong'})
                    elif case=='empty': self.write('work/preview-audit.json',{**self.report,'views':[]})
                    else:self.write('work/renders/TEST-A/page-1.png',b'other PNG')
                    with self.subTest(tool=tool,optimize=optimize,case=case):
                        proc=subprocess.run([sys.executable,'-B',str(HERE.parent/'tools'/tool),str(self.run)],
                            capture_output=True,text=True,env={**os.environ,'PYTHONOPTIMIZE':optimize},timeout=30)
                        self.assertNotEqual(proc.returncode,0)
                        self.assertNotIn('STRUCTURAL_PASS',proc.stdout)
                        expected={'failed':'unfinished/failed preview', 'digest':'preview terminal binding mismatch',
                                  'empty':'artifact digest changed', 'png':'artifact digest changed'}[case]
                        self.assertIn(expected,proc.stderr)


class FidelityTests(unittest.TestCase):
    def parse(self,text):
        return json.loads(subprocess.check_output(['pandoc','-f','gfm','-t','json'],input=text.encode()))

    def test_paragraph_delete_reorder_and_table_transposition_rejected(self):
        ast=self.parse('# Title\n\nFirst condition.\n\nSecond condition.\n\n|Key|Value|\n|---|---|\n|one|two|\n')
        for mutation in ('delete','reorder','table','link'):
            changed=copy.deepcopy(ast)
            if mutation=='delete':changed['blocks'].pop(1)
            elif mutation=='reorder':changed['blocks'][1:3]=reversed(changed['blocks'][1:3])
            elif mutation=='table':
                row=changed['blocks'][-1]['c'][4][0][3][0];row[1].reverse()
            else:
                changed=self.parse('# Title\n\n[First condition.](wrong)\n\nSecond condition.\n\n|Key|Value|\n|---|---|\n|one|two|\n')
            with self.assertRaisesRegex(RuntimeError,'fidelity'):fidelity.check(ast,changed,{},[])

    def test_code_bytes_and_language_preserved(self):
        ast=self.parse('```cpp\nx  y\n```')
        changed=copy.deepcopy(ast);changed['blocks'][0]['c'][1]='x y'
        with self.assertRaises(RuntimeError):fidelity.check(ast,changed,{},[])

    def test_adapter_cannot_rewrite_oracle(self):
        ast=self.parse('# T\n\nMust remain.\n');before=copy.deepcopy(ast)
        def bad(value,*_):value['blocks'].pop();return {},{},[]
        with self.assertRaises(RuntimeError):fidelity.adapt_checked(ast,SimpleNamespace(adapt=bad),{},preview.text)
        self.assertEqual(ast,before)

    def test_anchor_cannot_move_to_another_heading(self):
        ast=self.parse('# First\n\n<a id="old"></a>\n\n## Second\n\nText\n')
        adapted=self.parse('# First\n\n## Second\n\nText\n')
        with self.assertRaisesRegex(RuntimeError,'alias owner'):
            fidelity.check(ast,adapted,{'old':'first'},[])

    def test_removed_inline_spaces_rejected_even_if_printed_projection_matches(self):
        ast=self.parse('# T\n\n`x  y`\n')
        adapted=copy.deepcopy(ast);adapted['blocks'][1]['c'][0]['c'][1]='x y'
        with self.assertRaises(RuntimeError):fidelity.check(ast,adapted,{},[])

class GitReplacementTests(base.Fixture, unittest.TestCase):
    setUp=base.IsolationTests.setUp
    tearDown=base.IsolationTests.tearDown
    git=base.IsolationTests.git

    def test_replace_ref_cannot_change_frozen_bytes(self):
        old=self.git('rev-parse','HEAD').decode().strip();raw=(self.root/'00-fixture.md').read_bytes()
        (self.root/'00-fixture.md').write_text('replacement')
        self.git('add','.');self.git('-c','user.name=Test','-c','user.email=test@example.invalid','-c','commit.gpgsign=false','-c','core.hooksPath=/dev/null','commit','-qm','replacement')
        new=self.git('rev-parse','HEAD').decode().strip();self.git('replace',old,new)
        self.assertNotEqual(self.git('show',old+':00-fixture.md'),raw)
        self.assertEqual(source_model.blob(self.root,old,'00-fixture.md',pub),raw)


class EnvironmentTests(unittest.TestCase):
    def test_lock_mismatch_rejected(self):
        import environment
        with mock.patch.object(environment.importlib.metadata,'version',return_value='wrong'):
            with self.assertRaisesRegex(RuntimeError,'uv.lock'):
                environment.require_managed(HERE.parent)

    def test_system_or_wrong_python_rejected(self):
        import environment
        with mock.patch.object(environment.platform,'python_version',return_value='0.0.0'):
            with self.assertRaisesRegex(RuntimeError,'pinned project venv'):
                environment.require_managed(HERE.parent)


if __name__=='__main__':unittest.main(verbosity=2)
