"""Read-only audit of this fixed robotics reading candidate; prints JSON."""
_bootstrap = (__file__.rpartition('/')[0] or '.') + '/../../engine/source_runtime.py'
with open(_bootstrap, 'rb') as _source:
    exec(compile(_source.read(), _bootstrap, 'exec'), {'__name__': '_publication_source_runtime'})
import argparse, collections, hashlib, json, re
from pathlib import Path
from pypdf import PdfReader

p=argparse.ArgumentParser(); p.add_argument('attempt',type=Path); args=p.parse_args()
a=args.attempt; w=a/'work'; audit=json.loads((w/'preview-audit.json').read_text()); v=audit['views'][0]
pdf=w/v['pdf']; reader=PdfReader(pdf); names=reader.named_destinations
catalog=json.loads((w/'source-catalog.json').read_text())[0]
refs=json.loads((w/'typeset/ROBOTICS-HANDBOOK/reference-map.json').read_text())
targets={e['id']:catalog['anchors'][e['id']] for e in catalog['semantic'] if e['kind']=='source-target'}
assert len(targets)==54 and all(t in names for t in targets.values())
first=reader.get_destination_page_number(names[next(iter(catalog['anchors'].values()))])
expected=collections.Counter(r['target'].removeprefix('#') for r in refs if r['kind']=='SAME_VIEW_INTERNAL')
uris=collections.Counter(r['target'] for r in refs if r['kind']=='EXTERNAL_URI')
actual=collections.Counter(); observed_uris=collections.Counter(); annotations=[]
for page_no,page in enumerate(reader.pages):
 if page_no<first: continue
 for ref in page.get('/Annots',[]):
  n=ref.get_object()
  if n.get('/Subtype')!='/Link':continue
  action=n.get('/A',{}); target=n.get('/Dest') or action.get('/D'); uri=action.get('/URI')
  x0,y0,x1,y1=map(float,n['/Rect']); assert x1>x0 and y1>y0
  assert x0>=0 and y0>=0 and x1<=float(page.mediabox.width) and y1<=float(page.mediabox.height)
  if target: actual[str(target)]+=1; assert str(target) in names
  elif uri: observed_uris[str(uri)]+=1
  else: raise AssertionError('unrecognized annotation')
  annotations.append({'page':page_no+1,'target':str(target) if target else None,'uri':str(uri) if uri else None,'rect':[x0,y0,x1,y1]})
assert actual==expected,(actual-expected,expected-actual)
# A long external label may have multiple clickable rectangles; no missing URL.
assert set(observed_uris)==set(uris)
assert len(reader.pages)==28,'unexpected short-tail page'
texts=[re.sub(r'\s+','',page.extract_text()) for page in reader.pages]
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'engine'))
import preview
ast=json.loads((w/'source-ast/ROBOTICS-HANDBOOK.original.json').read_text())
entries=[]; blocks=ast['blocks']
for i,b in enumerate(blocks):
 if b['t']!='Para':continue
 raw=preview.text(b)
 # Select source title paragraphs by their printed [Snn] prefix.
 if not re.match(r'^\[S\d{2}\]',raw):continue
 description=preview.text(blocks[i+1]); identifier=re.match(r'^\[(S\d{2})\]',raw)[1]
 page=reader.get_destination_page_number(names[targets[identifier]])
 norm=lambda s:re.sub(r'\s+','',s)
 assert norm(raw) in texts[page] and norm(description) in texts[page],identifier
 entries.append({'id':identifier,'page':page+1,'title_and_description_same_page':True})
assert len(entries)==30,len(entries)
out={'status':'PASS','pdf_sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),'pages':len(reader.pages),
 'explicit_source_targets':len(targets),'source_internal_occurrences':sum(expected.values()),
 'actual_body_internal_annotations':sum(actual.values()),'external_source_urls':len(uris),
 'actual_body_uri_rectangles':sum(observed_uris.values()),'body_first_page':first+1,
 'targets':{k:{'destination':t,'page':reader.get_destination_page_number(names[t])+1} for k,t in targets.items()},
 'reference_entry_grouping':entries,'body_annotations':annotations,
 'limits':'PDF object/text audit, not interactive reader smoke, external URL validation or hardware evidence.'}
print(json.dumps(out,ensure_ascii=False,indent=2))
