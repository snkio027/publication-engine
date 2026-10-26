"""Preserve the learning manuscript; bind its explicit targets to source blocks."""
import re


def adapt(ast, source, text):
    original_meta = {key: text(value) for key, value in ast['meta'].items()}
    expected = {'id': 'robotics-learning-handbook', 'version': '1.0.0',
                'status': 'proposed-learning-baseline', 'source_of_truth': 'Markdown'}
    if any(original_meta.get(k) != v for k, v in expected.items()):
        raise RuntimeError('robotics source identity drift')
    blocks, pending, semantic = [], [], []
    section = ''
    for block in ast['blocks']:
        markup = None
        if block['t'] == 'RawBlock' and block['c'][0] == 'html':
            markup = block['c'][1]
        elif block['t'] == 'Para' and all(n['t'] in ('RawInline', 'Space', 'SoftBreak') for n in block['c']):
            markup = ''.join(n['c'][1] if n['t'] == 'RawInline' and n['c'][0] == 'html' else '\n' for n in block['c'])
        if markup is not None:
            if not re.fullmatch(r'(?:<a id="[^"<>]+"></a>\s*)+', markup):
                raise RuntimeError('unsupported robotics markup')
            pending.extend(re.findall(r'<a id="([^"]+)"></a>', markup))
            continue
        if pending:
            if block['t'] not in ('Header', 'Para', 'Plain'):
                raise RuntimeError('unsupported anchor owner')
            inlines = block['c'][2] if block['t'] == 'Header' else block['c']
            semantic.extend({'kind': 'source-target', 'id': identifier,
                             'target_type': block['t'], 'target_text': text(block)} for identifier in pending)
            for identifier in reversed(pending):
                inlines.insert(0, {'t': 'Span', 'c': [[identifier, ['source-target'], []], []]})
            pending = []
        if block['t'] == 'Header':
            section = text(block)
        if block['t'] == 'CodeBlock':
            block['c'][0][2].append(['reading-caption', section])
        blocks.append(block)
    if pending or not blocks or blocks[0]['t'] != 'Header' or blocks[0]['c'][0] != 1:
        raise RuntimeError('incomplete source structure')
    ast['blocks'] = blocks
    # Extract metadata without replacing the original AST metadata or source status.
    meta = {key: original_meta[key] for key in ('title', 'subtitle', 'version', 'status')}
    meta.update(document_id=source['id'], owner='')
    return meta, {}, semantic
