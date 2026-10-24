"""Engine-owned source -> adapter contract, independent of the adapter's oracle.

Conservative contract: printable character order, original inline-code bytes,
code-block bytes/languages, headers, list structure, table cells and links stay
unchanged. Only nonprinting anchors/comments, annotated literal conversions,
and paragraph-boundary/typographic whitespace adjustments are allowed.
This is a trusted-adapter error detector, not a sandbox for hostile Python.
"""
import copy
import hashlib
import json
import re


def sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def walk(value):
    if isinstance(value, dict):
        if 't' in value: yield value
        yield from walk(value.get('c'))
    elif isinstance(value, list):
        for v in value:
            yield from walk(v)


def plain(node):
    if isinstance(node, list): return ''.join(map(plain, node))
    if not isinstance(node, dict): return ''
    t, c = node.get('t'), node.get('c')
    if t in ('Str', 'MetaString'): return c
    if t in ('Code', 'CodeBlock', 'Math'): return c[-1]
    if t in ('Space', 'SoftBreak', 'LineBreak'): return ' '
    if t == 'Header': return plain(c[2])
    if t in ('Link', 'Image', 'Span', 'Cite'): return plain(c[1])
    if t in ('RawInline', 'RawBlock'):
        value = c[1]
        if re.fullmatch(r'(?:<a id="[^"<>]+"></a>\s*)+|<!--.*?-->\s*', value, re.S): return ''
        return value
    return plain(c)


def compact(value):
    return re.sub(r'\s+', '', plain(value))


def projection(ast):
    nodes = list(walk(ast['blocks']))
    tables = []
    for n in nodes:
        if n['t'] != 'Table': continue
        c = n['c']
        def rows(rs):
            return [[(cell[2], cell[3], compact(cell[4])) for cell in row[1]] for row in rs]
        tables.append({'caption': compact(c[1]), 'columns': len(c[2]),
                       'head': rows(c[3][1]),
                       'bodies': [(b[1], rows(b[2]), rows(b[3])) for b in c[4]],
                       'foot': rows(c[5][1])})
    return {'characters': compact(ast['blocks']),
            'headers': [(n['c'][0], n['c'][1][0], compact(n['c'][2])) for n in nodes if n['t']=='Header'],
            'code': [(n['c'][0][1], n['c'][1]) for n in nodes if n['t']=='CodeBlock'],
            'links': [(n['t'], compact(n['c'][1]), n['c'][2]) for n in nodes if n['t'] in ('Link','Image')],
            'tables': tables,
            'lists': [(n['t'], n['c'][0] if n['t']=='OrderedList' else None,
                       [compact(v) for v in (n['c'][1] if n['t']=='OrderedList' else n['c'])])
                      for n in nodes if n['t'] in ('OrderedList','BulletList','DefinitionList')]}


def check(original, adapted, aliases, semantic):
    original_sha = sha(original)
    original = copy.deepcopy(original)
    # Pandoc can parse one empty HTML anchor as two RawInline tags in a Para.
    # Collapse only all-anchor paragraphs, never arbitrary mixed HTML/prose.
    for block in original['blocks']:
        if block['t']=='Para' and all(n['t'] in ('RawInline','Space','SoftBreak') for n in block['c']):
            value=''.join(n['c'][1] if n['t']=='RawInline' and n['c'][0]=='html' else '\n' for n in block['c'])
            if re.fullmatch(r'(?:<a id="[^"<>]+"></a>\s*)+',value):
                block.update(t='RawBlock',c=['html',value])
    before, after = projection(original), projection(adapted)
    for field in before:
        if before[field] != after[field]:
            raise RuntimeError('source fidelity mismatch: ' + field)
    if original.get('meta') != adapted.get('meta'):
        raise RuntimeError('source metadata changed instead of extracted')
    for kind, position in (('Header',1),('CodeBlock',0)):
        left=[n['c'][position] for n in walk(original['blocks']) if n['t']==kind]
        right=[n['c'][position] for n in walk(adapted['blocks']) if n['t']==kind]
        for a,b in zip(left,right):
            if a[0]!=b[0] or not set(a[1])<=set(b[1]) or any(pair not in b[2] for pair in a[2]):
                raise RuntimeError('original source attributes lost')
    # Existing inline code cannot be removed/replaced even when prose characters match.
    old_code = [n['c'][-1] for n in walk(original['blocks']) if n['t']=='Code']
    new_code = [n['c'][-1] for n in walk(adapted['blocks']) if n['t']=='Code']
    extra = [s['value'] for s in semantic if s.get('kind')=='inline-identifier']
    remaining = iter(new_code)
    skipped = []
    for value in old_code:
        for observed in remaining:
            if observed == value: break
            skipped.append(observed)
        else: raise RuntimeError('source fidelity mismatch: inline code')
    skipped.extend(remaining)
    if sorted(skipped) != sorted(extra):
        raise RuntimeError('undeclared inline code conversion')
    transforms = []
    anchors = []
    for node in walk(original['blocks']):
        if node['t'] not in ('RawBlock','RawInline','Cite'): continue
        if node['t']=='Cite':
            value = plain(node)
            if not any(s.get('kind')=='loader-literal' and s.get('value')==value for s in semantic):
                raise RuntimeError('undeclared citation conversion')
            transforms.append({'kind':'literal-citation', 'value':value}); continue
        fmt, value = node['c']
        if fmt != 'html': raise RuntimeError('unsupported raw source format')
        if re.fullmatch(r'(?:<a id="[^"<>]+"></a>\s*)+', value):
            anchors.extend(re.findall(r'<a id="([^"<>]+)"></a>', value))
            continue
        marker = re.fullmatch(r'<!-- ([ghns]-(?:lab|file)|fm-test) (.*?) -->\s*', value, re.S)
        if marker:
            payload = json.loads(marker[2])
            kind = 'test' if marker[1]=='fm-test' else marker[1].split('-')[1]
            if not any(s.get('kind')==kind and s.get('payload')==payload for s in semantic):
                raise RuntimeError('lost nonprinting metadata')
            transforms.append({'kind':'nonprinting-metadata', 'source':value, 'payload':payload})
        elif node['t']=='RawInline' and any(s.get('kind')=='literal' and s.get('value')==value for s in semantic):
            transforms.append({'kind':'printed-raw-literal', 'source':value})
        else: raise RuntimeError('undeclared raw source removal/conversion')
    targets = [n['c'][0][0] for n in walk(adapted['blocks'])
               if n['t']=='Span' and 'source-target' in n['c'][0][1]]
    if len(anchors) != len(set(anchors)) or set(anchors) != set(aliases) | set(targets) or set(aliases) & set(targets):
        raise RuntimeError('source anchor inventory mismatch')
    # Validate owning source location, not just the set of destination IDs.
    current=None
    for index, block in enumerate(original['blocks']):
        if block['t']=='Header': current=block['c'][1][0]
        if block['t']!='RawBlock': continue
        ids=re.findall(r'<a id="([^"<>]+)"></a>',block['c'][1])
        if not ids: continue
        following=next((b for b in original['blocks'][index+1:] if b['t']!='RawBlock'),None)
        for identifier in ids:
            if identifier in aliases:
                expected=following['c'][1][0] if following and following['t']=='Header' else current
                if aliases[identifier]!=expected: raise RuntimeError('source alias owner changed')
            else:
                owners=[b for b in adapted['blocks'] if any(n['t']=='Span' and n['c'][0][0]==identifier for n in walk(b))]
                if len(owners)!=1 or not following or owners[0]['t']!=following['t'] or compact(owners[0])!=compact(following):
                    raise RuntimeError('source block target moved')
    if any(n['t'] in ('RawBlock','RawInline','Cite') for n in walk(adapted['blocks'])):
        raise RuntimeError('unconverted raw printing input')
    transforms.extend({'kind':'anchor', 'source_id':a, 'destination':aliases.get(a,a)} for a in anchors)
    return {'schema_version':1, 'status':'SOURCE_FIDELITY_PASS',
            'original_ast_sha256':original_sha, 'adapted_ast_sha256':sha(adapted),
            'projection_sha256':sha(before), 'checks':list(before)+['inline_code','raw_dispositions','anchors'],
            'whitespace_policy':'Prose whitespace and paragraph boundaries may change; code bytes may not.',
            'transformations':transforms, 'adapter_declarations':copy.deepcopy(semantic)}


def adapt_checked(ast, adapter, definition, text):
    # Serialize before calling adapter; it never receives the oracle object.
    original_bytes = json.dumps(ast, ensure_ascii=False, sort_keys=True).encode()
    printing = copy.deepcopy(ast)
    meta, aliases, semantic = adapter.adapt(printing, definition, text)
    original = json.loads(original_bytes)
    audit = check(original, printing, aliases, semantic)
    return printing, meta, aliases, semantic, original, audit
