#!/usr/bin/env python3
"""Read-only artifact verification + derived contact sheets in the attempt work dir.

Does not approve visuals. Human inspection scope must be recorded separately.
"""
import argparse
import hashlib
import json
import io
import sys
from pathlib import Path
_bootstrap = Path(__file__).resolve().parents[1] / 'engine/source_runtime.py'
exec(compile(_bootstrap.read_bytes(), str(_bootstrap), 'exec'), {'__name__': '_publication_source_runtime'})
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'engine'))
from evidence import verify

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('attempt',type=Path)
args=parser.parse_args()
work=args.attempt/'work'
_,ready,report,manifest,files,_=verify(args.attempt)
out=work/'visual-inputs'
out.mkdir(exist_ok=False)
inventory=[]
for view in report['views']:
    pdf=work/view['pdf']
    pages=sorted((e for e in manifest['files'] if e.get('render',{}).get('view')==view['view']),key=lambda e:e['render']['page'])
    for start in range(0,len(pages),20):
        sheet=Image.new('RGB',(800,1460),'#D9DDE1')
        draw=ImageDraw.Draw(sheet)
        for offset,entry in enumerate(pages[start:start+20]):
            with Image.open(io.BytesIO(files[entry['path']])) as image:
                image.thumbnail((188,266))
                x=(offset%4)*200+6; y=(offset//4)*292+20
                sheet.paste(image,(x,y))
                draw.text((x,y-16),f'{view["view"]} p{start+offset+1}',fill='black')
        target=out/f'{view["view"]}-{start+1:03d}.png'
        sheet.save(target)
        inventory.append({'view':view['view'],'pages':[start+1,min(start+20,len(pages))],'sheet':str(target),
                          'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
                          'inputs':[e['path'] for e in pages[start:start+20]]})
if verify(args.attempt)[3]!=manifest: raise RuntimeError('preview changed during contact-sheet generation')
(out/'contact-sheets.json').write_text(json.dumps({'status':'DERIVED_NOT_VISUALLY_REVIEWED',
    'artifact_manifest_sha256':ready['artifact_manifest_sha256'],'sheets':inventory},ensure_ascii=False,indent=2)+'\n')
print(json.dumps(inventory,ensure_ascii=False,indent=2))
