# Source-only policy must precede filesystem module imports.
_bootstrap = (__file__.rpartition('/')[0] or '.') + '/../../engine/source_runtime.py'
with open(_bootstrap, 'rb') as _source:
    exec(compile(_source.read(), _bootstrap, 'exec'), {'__name__': '_publication_source_runtime'})

"""Compare complete link annotations and outline against the prior local artifacts."""
import argparse
import json
from pathlib import Path
from pypdf import PdfReader




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
    parser.add_argument('--content',type=Path,required=True)
    parser.add_argument('--results',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();reports=[];ROOT=args.content.absolute()
    for entry in json.loads(args.results.read_text()):
        old=ROOT/entry['comparison']['baseline_attempt'];new=ROOT/entry['attempt']
        before=json.loads((old/'run.json').read_text());after=json.loads((new/'run.json').read_text())
        replacements=[(s['commit'],n['commit']) for s,n in zip(before['identity']['publication']['sources'],after['identity']['publication']['sources'])]
        artifact=next(iter(entry['ready']['artifacts']))
        old_reader=PdfReader(old/'work'/artifact);new_reader=PdfReader(new/'work'/artifact)
        left=shape(old_reader,replacements);right=shape(new_reader,[])
        if left!=right:raise RuntimeError('link/outline drift: '+entry['profile'])
        reports.append({'profile':entry['profile'],'status':'PASS','link_annotations':len(right['links']),
                        'normalized_source_commits':sorted(set(replacements)),
                        'outline_and_page_rect_targets':right})
    with args.output.open('x') as out:json.dump(reports,out,ensure_ascii=False,indent=2);out.write('\n')
    print(json.dumps({'status':'PASS','links':sum(r['link_annotations'] for r in reports)}))


if __name__=='__main__':main()
