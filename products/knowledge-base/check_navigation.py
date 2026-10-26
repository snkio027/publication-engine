# Source-only policy must precede filesystem module imports.
_bootstrap = (__file__.rpartition('/')[0] or '.') + '/../../engine/source_runtime.py'
with open(_bootstrap, 'rb') as _source:
    exec(compile(_source.read(), _bootstrap, 'exec'), {'__name__': '_publication_source_runtime'})

"""Explicit historical comparison; never search a content checkout for baselines."""
import argparse
import json
from pathlib import Path
from pypdf import PdfReader
from configure import ENGINE, PRODUCT, pub, project, boundaries
import evidence




def shape(reader, substitutions):
    page_ids={p.indirect_reference.idnum:i+1 for i,p in enumerate(reader.pages)}
    def string(value):
        result=str(value)
        for before,after in substitutions:result=result.replace(before,after)
        return result
    def destination(value):
        if isinstance(value,list):
            first=value[0]
            page=page_ids[first.idnum] if hasattr(first,'idnum') else int(first)+1
            return [page,*[string(v) for v in value[1:]]]
        return string(value)
    def outline(values):
        return [outline(v) if isinstance(v,list) else
                [string(v['/Title']),reader.get_destination_page_number(v)+1,
                 string(v.get('/Top')),string(v.get('/Left'))] for v in values]
    links=[]
    for number,page in enumerate(reader.pages,1):
        for reference in page.get('/Annots',[]):
            a=reference.get_object()
            if a.get('/Subtype')!='/Link':continue
            action=a.get('/A',{}).get_object() if '/A' in a else {}
            if '/Dest' in a:target=['GoTo',destination(a['/Dest'])]
            elif action.get('/S')=='/GoTo':target=['GoTo',destination(action['/D'])]
            elif action.get('/S')=='/URI':target=['URI',string(action['/URI'])]
            else:raise RuntimeError('unexpected link action')
            links.append([number,[str(v) for v in a['/Rect']],target])
    return {'outline':outline(reader.outline),'links':links}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--project',type=Path,required=True)
    parser.add_argument('--baseline',type=Path,required=True,
                        help='JSON: profile -> {attempt: absolute path, artifact_manifest_sha256: digest}')
    parser.add_argument('--results',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();reports=[]
    entries=json.loads(args.results.read_text())
    baselines=json.loads(args.baseline.read_text())
    if not entries or len({e['profile'] for e in entries})!=len(entries):
        raise RuntimeError('empty/duplicate comparison profiles')
    projects=[project.load(ENGINE,args.project,e['profile'],pub) for e in entries]
    output=boundaries.for_project(args.output,projects[0],pub)
    for entry,selected in zip(entries,projects):
        spec=baselines[entry['profile']]
        old=Path(spec['attempt']);new=Path(entry['attempt'])
        if not old.is_absolute():raise RuntimeError('baseline attempt must be explicit and absolute')
        before,old_ready,old_audit,old_manifest,old_files,_=evidence.verify(old)
        after,new_ready,new_audit,new_manifest,new_files,_=evidence.verify(new)
        if old_ready['artifact_manifest_sha256']!=spec['artifact_manifest_sha256']:
            raise RuntimeError('baseline manifest differs from explicit binding')
        if (after['identity']['source']['project_sha256']!=pub.digest(selected.raw)
                or after['identity']['publication']['profile']!=entry['profile']
                or before['identity']['publication']['profile']!=entry['profile']):
            raise RuntimeError('comparison project/profile mismatch')
        if len(old_audit['views'])!=1 or len(new_audit['views'])!=1:
            raise RuntimeError('this product comparison supports one selected view per trial')
        source_paths={p for p in new_files if p.startswith(('output/source/','source-ast/')) and not p.endswith('.fidelity.json')}
        old_paths={p for p in old_files if p.startswith(('output/source/','source-ast/')) and not p.endswith('.fidelity.json')}
        if source_paths!=old_paths or any(old_files[p]!=new_files[p] for p in source_paths):
            raise RuntimeError('source/AST drift')
        replacements=[(s['commit'],n['commit']) for s,n in zip(before['identity']['publication']['sources'],after['identity']['publication']['sources'])]
        artifact=next(iter(new_ready['artifacts']))
        old_reader=PdfReader(old/'work'/artifact);new_reader=PdfReader(new/'work'/artifact)
        left=shape(old_reader,replacements);right=shape(new_reader,[])
        if left!=right:raise RuntimeError('link/outline drift: '+entry['profile'])
        def destinations(reader):
            return {key:[reader.get_destination_page_number(value),str(value.get('/Top')),str(value.get('/Left'))]
                    for key,value in reader.named_destinations.items()}
        if len(old_reader.pages)!=len(new_reader.pages) or destinations(old_reader)!=destinations(new_reader):
            raise RuntimeError('page/destination drift')
        text_replacements=[(before['build_id'][:24],after['build_id'][:24]),*replacements]
        changed_text=[]
        for page,(a,b) in enumerate(zip(old_reader.pages,new_reader.pages),1):
            text=a.extract_text()
            for x,y in text_replacements:text=text.replace(x,y)
            if text!=b.extract_text():changed_text.append(page)
        if changed_text:raise RuntimeError('text drift beyond generated identity: '+str(changed_text))
        old_png={e['render']['page']:e['sha256'] for e in old_manifest['files'] if e.get('render')}
        changed_png=[e['render']['page'] for e in new_manifest['files'] if e.get('render') and e['sha256']!=old_png[e['render']['page']]]
        reports.append({'profile':entry['profile'],'status':'PASS','link_annotations':len(right['links']),
                        'baseline':spec,'attempt':str(new),'source_ast_files_identical':len(source_paths),
                        'pages':len(new_reader.pages),'destinations_identical':len(new_reader.named_destinations),
                        'png_changed_pages':changed_png,'png_unchanged_pages':len(new_reader.pages)-len(changed_png),
                        'text_identical_except_generated_identity':True,
                        'visual_acceptance':'NOT_IMPLIED_BY_COMPARISON',
                        'normalized_source_commits':sorted(set(replacements)),
                        'outline_and_page_rect_targets':right})
    with pub.absolute_directory(output.parent,create=True) as out:pub.write_json(out,output.name,reports)
    print(json.dumps({'status':'PASS','links':sum(r['link_annotations'] for r in reports)}))


if __name__=='__main__':main()
