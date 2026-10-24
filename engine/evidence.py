"""Committed full-preview evidence. No legacy inference or in-place upgrades."""
import hashlib
import json
import re
from pathlib import Path

SCHEMA = 1
TREES = ('output', 'source-ast', 'typeset', 'renders')
FILES = ('preview-audit.json', 'source-catalog.json', 'worker.log')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_at(fd, path, pub):
    names = pub.parts(path)
    if path != '/'.join(names):
        raise pub.PreparationError('noncanonical evidence path')
    if len(names) == 1:
        return pub.regular_bytes(fd, names[0])
    with pub.directory(fd, '/'.join(names[:-1])) as parent:
        return pub.regular_bytes(parent, names[-1])


def inventory(fd, pub):
    import os
    import stat
    result = {name: read_at(fd, name, pub) for name in FILES}
    def collect(folder, prefix):
        for name in sorted(os.listdir(folder)):
            path = prefix + '/' + name
            mode = os.stat(name, dir_fd=folder, follow_symlinks=False).st_mode
            if stat.S_ISDIR(mode):
                with pub.directory(folder, name) as child:
                    collect(child, path)
            elif stat.S_ISREG(mode):
                result[path] = pub.regular_bytes(folder, name)
            else:
                raise pub.PreparationError('linked/nonregular evidence: ' + path)
    for prefix in TREES:
        with pub.directory(fd, prefix) as folder:
            collect(folder, prefix)
    return result


def check_report(source, report, pub):
    planned = source['identity']['publication']['views']
    views = report['views']
    actual = [v['view'] for v in views]
    if (not planned or len(planned) != len(set(planned)) or
            len(actual) != len(set(actual)) or set(actual) != set(planned)):
        raise pub.PreparationError('planned/completed view set mismatch')
    if report['status'] != 'BUILT_FOR_REVIEW' or report['source_build_id'] != source['build_id']:
        raise pub.PreparationError('preview source/status mismatch')
    execution = json.dumps(report['execution_identity'], sort_keys=True, separators=(',', ':')).encode()
    if digest(execution) != report['execution_id']:
        raise pub.PreparationError('execution identity mismatch')
    if report['execution_identity']['preparation_id'] != source['build_id']:
        raise pub.PreparationError('execution/preparation mismatch')
    pdfs = [v['pdf'] for v in views]
    if len(set(pdfs)) != len(views):
        raise pub.PreparationError('duplicate view PDF')
    required = ('missing_text_blocks', 'missing_table_row_relations', 'section_errors',
                'inline_literal_errors', 'orphan_headings', 'navigation_errors')
    for view in views:
        if (not isinstance(view['pages'], int) or view['pages'] < 1 or
                view['pages'] != view['rendered_pages'] or
                any(view.get(k) != [] for k in required) or
                any(w > 2 for w in view['overfull_hbox_pt'])):
            raise pub.PreparationError('missing/failed full preview checks')
    return planned


def build_manifest(source, report, files, pub):
    planned = check_report(source, report, pub)
    required = set(FILES) | {'output/README.md'}
    renders = {}
    pdfs = {v['pdf']: v for v in report['views']}
    if {n for n in files if n.startswith('output/pdf/')} != set(pdfs):
        raise pub.PreparationError('PDF collection mismatch')
    for view in report['views']:
        name = view['view']
        if not re.fullmatch(r'[A-Z][A-Z0-9-]+', name):
            raise pub.PreparationError('unsafe view')
        required.update('typeset/' + name + '/' + n for n in (
            'composed.json', 'document.tex', 'document.log', 'document.fls',
            'reference-map.json', 'table-map.json', 'section-audit.json',
            'reading-components.json', 'audit.json'))
        if digest(files.get(view['pdf'], b'')) != view['sha256']:
            raise pub.PreparationError('PDF digest changed: ' + view['pdf'])
        pages = {}
        for path in files:
            if not path.startswith('renders/' + name + '/'):
                continue
            match = re.fullmatch(r'renders/' + name + r'/page-([0-9]+)\.png', path)
            if not match or int(match[1]) in pages:
                raise pub.PreparationError('invalid/duplicate rendered page')
            page = int(match[1]); pages[page] = path
            renders[path] = {'view': name, 'pdf': view['pdf'], 'pdf_sha256': view['sha256'],
                             'page': page, 'dpi': 72,
                             'renderer': report['execution_identity']['tools']['pdftoppm']}
        if set(pages) != set(range(1, view['pages'] + 1)):
            raise pub.PreparationError('rendered page coverage mismatch')
    if {p for p in files if p.startswith('renders/')} != set(renders):
        raise pub.PreparationError('unexpected render view')
    for src in source['identity']['publication']['sources']:
        required.add('output/source/' + src['path'])
        required.update('source-ast/' + src['id'] + suffix for suffix in ('.json', '.original.json', '.fidelity.json'))
    if not required <= files.keys():
        raise pub.PreparationError('missing machine evidence: ' + str(sorted(required - files.keys())))
    from fidelity import sha as ast_sha
    for src in source['identity']['publication']['sources']:
        prefix='source-ast/'+src['id']
        fidelity=json.loads(files[prefix+'.fidelity.json'])
        if (fidelity.get('status')!='SOURCE_FIDELITY_PASS' or
                fidelity.get('original_ast_sha256')!=ast_sha(json.loads(files[prefix+'.original.json'])) or
                fidelity.get('adapted_ast_sha256')!=ast_sha(json.loads(files[prefix+'.json']))):
            raise pub.PreparationError('source fidelity evidence binding mismatch')
    entries = []
    for name, data in sorted(files.items()):
        role = ('render' if name in renders else 'pdf' if name in pdfs else
                'source' if name.startswith('output/source/') else
                'diagnostic' if name.endswith(('.log', '.txt')) else 'machine-evidence')
        entry = {'path': name, 'role': role, 'size_bytes': len(data), 'sha256': digest(data)}
        if name in renders:
            entry['render'] = renders[name]
        entries.append(entry)
    return {'schema_version': SCHEMA, 'mode': 'FULL_PREVIEW', 'views': planned,
            'preparation_id': source['build_id'], 'execution_id': report['execution_id'], 'files': entries}


def seal(run, pub):
    """Parent calls only after worker exit AND log close, before terminal commit."""
    with pub.root_handle(run) as fd, pub.directory(fd, 'work') as work:
        source = json.loads(read_at(fd, 'run.json', pub))
        report = json.loads(read_at(work, 'preview-audit.json', pub))
        files = inventory(work, pub)
        manifest = build_manifest(source, report, files, pub)
        pub.write_json(work, 'artifact-manifest.json', manifest)
        if inventory(work, pub) != files:
            raise pub.PreparationError('evidence changed during seal')
        return digest(read_at(work, 'artifact-manifest.json', pub))


def verify_fd(fd, pub):
    source = json.loads(read_at(fd, 'run.json', pub))
    ready = json.loads(read_at(fd, 'preview-result.json', pub))
    prepared = json.loads(read_at(fd, 'result.json', pub))
    if prepared['status'] != 'PREPARED' or ready['status'] != 'PREVIEW_READY':
        raise pub.PreparationError('unfinished/failed preview is not reviewable')
    if ready.get('evidence_schema') != SCHEMA or ready.get('mode') != 'FULL_PREVIEW':
        raise pub.PreparationError('full evidence manifest required; historical previews are not upgraded')
    if source['build_id'] != digest(pub.canonical(source['identity'])):
        raise pub.PreparationError('preparation identity mismatch')
    if 'mounts' in source and (source['mounts'] != source['identity'].get('mounts') or
            source['descriptor_path'] != source['identity'].get('descriptor_path')):
        raise pub.PreparationError('root binding mismatch')
    with pub.directory(fd, 'work') as work:
        raw = read_at(work, 'artifact-manifest.json', pub)
        if digest(raw) != ready.get('artifact_manifest_sha256'):
            raise pub.PreparationError('artifact manifest digest changed')
        files = inventory(work, pub)
        declared=json.loads(raw)
        entries=declared['files']
        if len(entries)!=len(files) or {e['path'] for e in entries}!=set(files):
            raise pub.PreparationError('artifact file collection mismatch')
        for entry in entries:
            data=files[entry['path']]
            if len(data)!=entry['size_bytes'] or digest(data)!=entry['sha256']:
                raise pub.PreparationError('artifact digest changed: '+entry['path'])
        report = json.loads(files['preview-audit.json'])
        expected = build_manifest(source, report, files, pub)
        if declared != expected:
            raise pub.PreparationError('artifact evidence digest changed or file collection mismatch')
        if (digest(files['preview-audit.json']) != ready['audit_sha256'] or
                report['execution_id'] != ready['execution_id'] or
                {v['pdf']: v['sha256'] for v in report['views']} != ready['artifacts']):
            raise pub.PreparationError('preview terminal binding mismatch')
        return source, ready, report, expected, files, raw


def verify(run):
    import pub
    with pub.root_handle(Path(run)) as fd:
        return verify_fd(fd, pub)
