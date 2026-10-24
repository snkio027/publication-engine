"""Independent project fixtures and root/pin/terminal safety regressions."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE=Path(__file__).resolve().parent
SCRIPTS=HERE.parent/'engine'
sys.path.insert(0,str(SCRIPTS))
import pub, project, source_model


def tree_bytes(root):
    return {str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}


class Fixture:
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='publication-independent-')
        self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name).resolve()
        self.root=self.base/'content with spaces';self.root.mkdir();self.repo=self.root
        self.engine=self.base/'tool checkout';self.engine.mkdir()
        for name in ('engine','latex','tools'):
            shutil.copytree(HERE.parent/name,self.engine/name,ignore=shutil.ignore_patterns('__pycache__'))
        for name in ('pyproject.toml','uv.lock','.python-version'):
            shutil.copyfile(HERE.parent/name,self.engine/name)
        self.engine_git('init','-q')
        self.profile_path=self.root/'publication/profiles/fixture'
        shutil.copytree(HERE/'fixtures',self.profile_path)
        config={'schema_version':2,'id':'fixture','repository':'https://example.invalid/content',
                'sources':[{'id':f'TEST-{n}','path':f'{n:02d}-fixture.md','revision':'WORKTREE'} for n in range(6)],
                'views':[{'id':f'TEST-{n}','documents':[f'TEST-{n}']} for n in range(6)]+
                    [{'id':'ESD-HANDBOOK','documents':[f'TEST-{n}' for n in range(6)],
                      'title':'Integration Fixture','subtitle':'Disposable sources','version':'0.1','status':'DRAFT'}],
                'toc_depth':0,'combined_toc_depth':0,'required_headings':[],
                'navigation':{'preface_title':'阅读与版本说明','preface_id':'generated-preface'},
                'reading':{'heading_roles':{'1':'section','2':'subsection','3':'subsubsection'}},
                'index':{'id':'generated-requirement-index','title':'Fixture Index','heading_pattern':'-REQ-'}}
        (self.profile_path/'profile.json').write_text(json.dumps(config))
        for n in range(6):
            (self.root/f'{n:02d}-fixture.md').write_text(f'---\ndocument_id: TEST-{n}\ntitle: Fixture {n}\nversion: "1"\nstatus: DRAFT\n---\n# Fixture {n}\n\nMust remain.\n')
        (self.root/'.gitignore').write_text('/publication/build/\n')
        self.dist=self.root/'dist';self.dist.mkdir()
        (self.dist/'history.bin').write_bytes(b'protected historical bytes\x00')
        self.dist_before=tree_bytes(self.dist)
        self.output=self.root/'publication/build'
        self.descriptor=self.root/'project.json'
        self.config={'schema_version':1,'engine':{'repository':'https://example.invalid/engine','commit':'0'*40},
                     'source_repository':config['repository'],'content_root':'.','product_root':'.',
                     'output_root':'publication/build','profiles':{'fixture':'publication/profiles/fixture/profile.json'}}
        self.repin()
        self.git('init','-q');self.git('add','.')
        self.commit(self.git)

    @staticmethod
    def commit(git):
        git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','-c','commit.gpgsign=false',
            '-c','core.hooksPath=/dev/null','commit','--allow-empty','-qm','fixture')

    def engine_git(self,*args):
        return subprocess.check_output(['git','-C',str(self.engine),*args],stderr=subprocess.PIPE)

    def git(self,*args):
        return subprocess.check_output(['git','-C',str(self.repo),*args],stderr=subprocess.PIPE)

    def repin(self):
        self.engine_git('add','.');self.commit(self.engine_git)
        self.config['engine']['commit']=self.engine_git('rev-parse','HEAD').decode().strip()
        self.descriptor.write_text(json.dumps(self.config))

    def selected(self):
        return project.load(self.engine,self.descriptor,'fixture',pub)

    def cli(self,*args,env=None):
        return subprocess.run([sys.executable,'-B',str(self.engine/'engine/pub.py'),
            '--project',str(self.descriptor),'--profile','fixture',*args],cwd=self.base,capture_output=True,text=True,env=env)

    def prepared(self):
        result=pub.prepare(self.selected());path=Path(result['path'])
        self.assertEqual(json.loads((path/'result.json').read_text())['status'],'PREPARED')
        return path

    def tearDown(self):
        self.assertEqual(tree_bytes(self.dist),self.dist_before)


class IsolationTests(Fixture, unittest.TestCase):
    def test_separate_roots_and_unrelated_working_directory(self):
        result=self.cli('preview','--prepare-only')
        self.assertEqual(result.returncode,0,result.stderr)
        run=json.loads((Path(json.loads(result.stdout)['path'])/'run.json').read_text())
        self.assertNotEqual(run['mounts']['engine'],run['mounts']['content'])
        self.assertEqual(run['identity']['source']['engine_pin'],self.config['engine'])

    def test_three_separate_input_roots(self):
        product=self.base/'products';shutil.copytree(self.root/'publication/profiles',product/'catalog')
        self.config.update(product_root='../products',profiles={'fixture':'catalog/fixture/profile.json'})
        self.descriptor.write_text(json.dumps(self.config))
        run=self.prepared()
        record=json.loads((run/'run.json').read_text())
        self.assertEqual(record['mounts']['product'],str(product))
        self.assertTrue((run/'inputs/catalog/fixture/adapter.py').is_file())

    def test_engine_pin_mismatch_rejected(self):
        (self.engine/'engine/fidelity.py').write_text('# changed')
        with self.assertRaisesRegex(pub.PreparationError,'engine pin mismatch'):self.prepared()

    def test_untracked_engine_input_rejected(self):
        (self.engine/'engine/extra.py').write_text('# unexpected')
        with self.assertRaisesRegex(pub.PreparationError,'collection differs'):self.prepared()

    def test_engine_and_content_commits_are_not_interchangeable(self):
        config=json.loads((self.profile_path/'profile.json').read_text())
        config['sources'][0]['revision']=self.config['engine']['commit']
        (self.profile_path/'profile.json').write_text(json.dumps(config))
        with self.assertRaises(subprocess.CalledProcessError):self.prepared()

    def test_nonempty_output_not_adopted(self):
        self.config['output_root']='dist';self.descriptor.write_text(json.dumps(self.config))
        with self.assertRaisesRegex(pub.PreparationError,'initialized'):self.prepared()

    def test_output_root_and_ancestor_rejected(self):
        for name in ('.','..','/','../tool checkout'):
            self.config['output_root']=name;self.descriptor.write_text(json.dumps(self.config))
            with self.subTest(name=name),self.assertRaises(pub.PreparationError):self.selected()

    def test_output_parent_symlink_rejected(self):
        (self.root/'redirect').symlink_to(self.dist,target_is_directory=True)
        self.config['output_root']='redirect/output';self.descriptor.write_text(json.dumps(self.config))
        with self.assertRaises(OSError):self.prepared()

    def test_profile_and_dependency_traversal_rejected(self):
        self.config['profiles']['fixture']='../escape/profile.json';self.descriptor.write_text(json.dumps(self.config))
        with self.assertRaises(pub.PreparationError):self.selected()

    def test_git_filter_never_runs(self):
        target=self.dist/'filter-ran'
        self.git('config','filter.evil.clean',f'touch "{target}"; cat')
        with self.assertRaisesRegex(pub.PreparationError,'filter'):self.prepared()
        self.assertFalse(target.exists())

    def test_missing_view_and_namespace_collision_rejected(self):
        with self.assertRaisesRegex(pub.PreparationError,'view'):pub.prepare(self.selected(),['MISSING'])
        cfg=json.loads((self.profile_path/'profile.json').read_text());cfg['dependencies']=['publication/engine/pub.py']
        (self.root/'publication/engine').mkdir();(self.root/'publication/engine/pub.py').write_text('evil')
        (self.profile_path/'profile.json').write_text(json.dumps(cfg))
        with self.assertRaisesRegex(pub.PreparationError,'collision'):self.prepared()

    def test_live_roots_and_descriptor_drift(self):
        run=self.prepared()
        source_model.verify_live_inputs(run,self.root,pub)
        self.descriptor.write_text(self.descriptor.read_text()+' ')
        with self.assertRaisesRegex(pub.PreparationError,'descriptor drift'):source_model.verify_live_inputs(run,self.root,pub)

    def test_prepare_fsync_failure_has_no_success(self):
        write=pub.write_json
        def fail(fd,name,value):
            if name.endswith('.pending') and value.get('status')=='PREPARED':
                with mock.patch.object(pub.os,'fsync',side_effect=OSError('injected')):return write(fd,name,value)
            return write(fd,name,value)
        with mock.patch.object(pub,'write_json',side_effect=fail),self.assertRaises(OSError):self.prepared()
        records=list(self.output.glob('preview/*/*/result.json'))
        self.assertEqual(len(records),1)
        self.assertEqual(json.loads(records[0].read_text())['status'],'FAILED')

    def test_cancel_during_snapshot_copy(self):
        write=pub.write_bytes
        def fail(fd,name,value):
            if name.startswith('inputs/'):raise pub.Cancelled(15)
            return write(fd,name,value)
        with mock.patch.object(pub,'write_bytes',side_effect=fail),self.assertRaises(pub.Cancelled):self.prepared()
        record=next(self.output.glob('preview/*/*/result.json'))
        self.assertEqual(json.loads(record.read_text())['status'],'CANCELLED')

    def test_error_after_prepare_commit_retains_fact(self):
        link=pub.os.link
        def fail(*a,**kw):link(*a,**kw);raise OSError('after commit')
        with mock.patch.object(pub.os,'link',side_effect=fail):self.prepared()


if __name__=='__main__':unittest.main(verbosity=2)
