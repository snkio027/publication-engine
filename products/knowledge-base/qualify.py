# Source-only policy must precede filesystem module imports.
_bootstrap = (__file__.rpartition('/')[0] or '.') + '/../../engine/source_runtime.py'
with open(_bootstrap, 'rb') as _source:
    exec(compile(_source.read(), _bootstrap, 'exec'), {'__name__': '_publication_source_runtime'})

"""Three real consumer builds; no publishing and no writes to historical artifacts."""
import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

PRODUCT=Path(__file__).absolute().parent
ENGINE=PRODUCT.parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--project',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();args.engine=ENGINE;args.output=args.output.absolute();args.project=args.project.absolute()
    descriptor=json.loads(args.project.read_text())
    ROOT=Path(descriptor['content_root'])
    output_root=args.project.parent/descriptor['output_root']
    args.output.mkdir(parents=True,exist_ok=False)
    bootstrap=args.engine/'engine/source_runtime.py'
    exec(compile(bootstrap.read_bytes(),str(bootstrap),'exec'),{'__name__':'_publication_source_runtime'})
    sys.path.insert(0,str(args.engine/'engine'))
    import evidence, candidate, pub, source_model
    from pypdf import PdfReader
    results=[]
    def command(name,argv):
        start=time.monotonic()
        process=subprocess.run(list(map(str,argv)),cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=600)
        (args.output/(name+'.stdout')).write_bytes(process.stdout)
        (args.output/(name+'.stderr')).write_bytes(process.stderr)
        record={'argv':list(map(str,argv)),'exit_code':process.returncode,'seconds':round(time.monotonic()-start,3)}
        if process.returncode:raise RuntimeError(name+' failed: '+process.stderr.decode(errors='replace'))
        return process.stdout,record
    for profile,view in [('cpp-handbook','G6'),('esd','ESD-REFERENCE-001'),('cpp-failure-model',None)]:
        invocation=[sys.executable,'-B',ENGINE/'engine/pub.py','--project',args.project,'preview','--profile',profile]
        if view:invocation+=['--view',view]
        output,executed=command(profile,invocation)
        built=json.loads(output)
        run=Path(built['audit']).parents[1]
        record,ready,audit,manifest,files,raw=evidence.verify(run)
        source_model.verify_live_inputs(run,ROOT,pub)
        relative=str(run.relative_to(output_root))
        frozen,freeze_command=command(profile+'-candidate',[sys.executable,'-B',ENGINE/'engine/pub.py','--project',args.project,
            'candidate','--profile',profile,'--from-preview',relative])
        item={'profile':profile,'attempt':str(run),'preview_command':executed,
              'candidate':json.loads(frozen),'candidate_command':freeze_command,'ready':ready,
              'pages':sum(v['pages'] for v in audit['views']),'artifact_files':len(manifest['files'])}
        results.append(item)
        (args.output/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
        reviewed,rc=command(profile+'-reading',[sys.executable,'-B',args.engine/'tools/reading-review.py',run,
            '--corpus',PRODUCT/'publication/tools/reading-corpus.json'])
        sheets,sc=command(profile+'-sheets',[sys.executable,'-B',args.engine/'tools/inspect-pages.py',run])
        item.update(reading=json.loads(reviewed),reading_command=rc,sheets_command=sc)
        old_record=json.loads((ROOT/'publication/reviews/runtime-evidence/builds'/f'{profile}.json').read_text())
        old=ROOT/old_record['trial']['attempt']
        old_ready=json.loads((old/'preview-result.json').read_text())
        old_manifest=json.loads((old/'work/artifact-manifest.json').read_text())
        if sha(old/'work/artifact-manifest.json')!=old_ready['artifact_manifest_sha256']:
            raise RuntimeError('comparison baseline manifest changed')
        for entry in old_manifest['files']:
            if sha(old/'work'/entry['path'])!=entry['sha256']:
                raise RuntimeError('comparison baseline evidence changed: '+entry['path'])
        compared=[]
        for path in files:
            if path.startswith('output/source/') or path.startswith('source-ast/') and path.endswith(('.original.json','.json')):
                if path.endswith('.fidelity.json'):continue
                if (old/'work'/path).read_bytes()!=files[path]:raise RuntimeError('source/AST comparison changed: '+path)
                compared.append(path)
        current_view=audit['views'][0]
        old_pdf=old/'work'/next(iter(old_ready['artifacts']))
        new_pdf=run/'work'/current_view['pdf']
        left,right=PdfReader(old_pdf),PdfReader(new_pdf)
        if len(left.pages)!=len(right.pages):raise RuntimeError('pagination drift requires review')
        def destinations(reader):
            return {key:[reader.get_destination_page_number(value),str(value.get('/Top')),str(value.get('/Left'))]
                    for key,value in reader.named_destinations.items()}
        if destinations(left)!=destinations(right):raise RuntimeError('destination position drift')
        old_source=json.loads((old/'run.json').read_text())
        substitutions=[(old_source['build_id'][:24],record['build_id'][:24])]
        substitutions += [(s['commit'],n['commit']) for s,n in zip(old_source['identity']['publication']['sources'],record['identity']['publication']['sources'])]
        changed_text=[]
        for page,(a,b) in enumerate(zip(left.pages,right.pages),1):
            text=a.extract_text()
            for before,after in substitutions:text=text.replace(before,after)
            if text!=b.extract_text():changed_text.append(page)
        if changed_text:raise RuntimeError('text changed beyond generated identity: '+str(changed_text))
        old_renders={e['render']['page']:e for e in old_manifest['files'] if e.get('render')}
        changed_images=[]
        for entry in manifest['files']:
            if entry.get('render'):
                page=entry['render']['page']
                if entry['sha256']!=old_renders[page]['sha256']:changed_images.append(page)
        item['comparison']={'baseline_attempt':str(old.relative_to(ROOT)),'source_ast_files_identical':len(compared),
            'page_count_identical':len(right.pages),'destination_positions_identical':len(right.named_destinations),
            'text_identical_except_generated_identity':True,'png_changed_pages':changed_images,
            'png_unchanged_pages':len(right.pages)-len(changed_images),
            'meaning':'Image changes are review signals, not automatic failures or visual approval.'}
        # Inspectors may only add derived files, never rewrite committed evidence.
        if evidence.verify(run)[3]!=manifest:raise RuntimeError('evidence changed after review tools')
        (args.output/'results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(item,ensure_ascii=False),flush=True)


if __name__=='__main__':main()
