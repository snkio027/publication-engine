"""Repository-relative, no-follow inputs; explicit immutable Git source revisions."""
import json
import os
import re
import subprocess
import stat
from pathlib import Path


def git(root, *args):
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(('GIT_', 'XCRUN_')) and k not in ('TMPDIR', 'TMP', 'TEMP')}
    env['GIT_OPTIONAL_LOCKS'] = '0'
    return subprocess.check_output(['git', '--no-replace-objects', '--no-pager', '-c', 'core.fsmonitor=false',
                                    '-C', str(root), *args], env=env, stderr=subprocess.PIPE)


def path_parts(path, pub):
    if not isinstance(path, str) or not path or path != '/'.join(pub.parts(path)):
        raise pub.PreparationError('noncanonical input path')
    return pub.parts(path)


def read(root_fd, path, pub):
    names = path_parts(path, pub)
    if len(names) == 1:
        return pub.regular_bytes(root_fd, names[0])
    with pub.directory(root_fd, '/'.join(names[:-1])) as parent:
        return pub.regular_bytes(parent, names[-1])


def blob(root, revision, path, pub):
    path_parts(path, pub)
    if not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise pub.PreparationError('source revision must be a full immutable commit SHA')
    if git(root, 'cat-file', '-t', revision).strip() != b'commit':
        raise pub.PreparationError('source revision is not a commit')
    entry = git(root, 'ls-tree', '-z', revision, '--', path).split(b'\0')
    if len(entry) != 2 or not entry[0].startswith((b'100644 blob ', b'100755 blob ')):
        raise pub.PreparationError('source must be a regular Git blob: ' + path)
    return git(root, 'cat-file', 'blob', revision + ':' + path)


def snapshot(project, views, pub):
    from product_lock import verify
    verify(project, pub)
    profile = project.profile
    if not re.fullmatch(r'[a-z][a-z0-9-]*', profile):
        raise pub.PreparationError('invalid profile name')
    root = project.content
    prefix = str(Path(project.profile_path).parent)
    with pub.root_handle(project.product) as root_fd:
        config = json.loads(read(root_fd, project.profile_path, pub))
    if config['repository'] != project.config['source_repository']:
        raise pub.PreparationError('profile source repository differs from project')
    if config.get('schema_version') != 2 or config.get('id') != profile:
        raise pub.PreparationError('unsupported profile identity/schema')
    if not config.get('sources') or not config.get('views'):
        raise pub.PreparationError('profile requires sources and views')
    if config.get('source_format', 'markdown-smart') not in ('markdown-smart', 'gfm'):
        raise pub.PreparationError('unsupported source parser')
    # PUBLICATION is a typeset identity, not a publish operation or approval.
    if config.get('artifact_channel', 'PREVIEW') not in ('PREVIEW', 'RELEASE_CANDIDATE', 'PUBLICATION'):
        raise pub.PreparationError('unsupported artifact channel; formal publication stays closed')
    filenames = [v.get('filename', v['id'] + '-draft.pdf') for v in config['views']]
    if (any(not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*\.pdf', name) for name in filenames)
            or len({name.casefold() for name in filenames}) != len(filenames)):
        raise pub.PreparationError('unsafe or duplicate artifact filename')
    selected = views or [v['id'] for v in config['views']]
    known_views = [v['id'] for v in config['views']]
    if len(set(known_views)) != len(known_views) or len(set(selected)) != len(selected) or not set(selected) <= set(known_views):
        raise pub.PreparationError('unknown or repeated view')
    for view in config['views']:
        if not re.fullmatch(r'[A-Z][A-Z0-9-]+', view['id']):
            raise pub.PreparationError('unsafe view identity')
        if not view['documents'] or len(set(view['documents'])) != len(view['documents']):
            raise pub.PreparationError('empty/repeated view source')
    from project import engine_snapshot
    snapshot = engine_snapshot(project, pub)
    bindings = {p: {'root': 'engine', 'path': p.removeprefix('publication/')} for p in snapshot}
    def put(path, data, binding):
        if path in snapshot:
            raise pub.PreparationError('snapshot namespace collision: ' + path)
        snapshot[path] = data
        bindings[path] = binding
    def collect(fd, relative):
        for name in sorted(os.listdir(fd)):
            if name == '__pycache__':
                continue
            mode = os.stat(name, dir_fd=fd, follow_symlinks=False).st_mode
            path = relative + '/' + name
            if stat.S_ISDIR(mode):
                with pub.directory(fd, name) as child:
                    collect(child, path)
            elif stat.S_ISREG(mode):
                put(path, pub.regular_bytes(fd, name), {'root': 'product', 'path': path})
            else:
                raise pub.PreparationError('linked/nonregular publication input: ' + path)
    with pub.root_handle(project.product) as root_fd:
        with pub.directory(root_fd, prefix) as fd:
            collect(fd, prefix)
        for name in config.get('dependencies', []):
            path_parts(name, pub)
            put(name, read(root_fd, name, pub), {'root': 'product', 'path': name})
        if project.config.get('product'):
            lock = json.loads(read(root_fd, 'product.json', pub))
            locked = {e['path']: e for e in lock['inputs']}
            for path, binding in bindings.items():
                if binding['root'] == 'product' and (path not in locked or
                        pub.digest(snapshot[path]) != locked[path]['sha256']):
                    raise pub.PreparationError('undeclared/drifted product input: ' + path)
            put('product.json', read(root_fd, 'product.json', pub), {'root': 'product', 'path': 'product.json'})
    for name in (prefix + '/adapter.py', prefix + '/template.tex', prefix + '/theme.sty',
                 'publication/engine/pub.py', 'publication/engine/preview.py'):
        if name not in snapshot:
            raise pub.PreparationError('missing required publication input: ' + name)
    head = git(root, 'rev-parse', 'HEAD').decode().strip()
    sources = []
    ids, paths = set(), set()
    for definition in config['sources']:
        path = definition['path']
        path_parts(path, pub)
        if not path.endswith('.md') or path in paths or definition['id'] in ids:
            raise pub.PreparationError('invalid or duplicate source')
        if not re.fullmatch(r'[A-Z][A-Z0-9-]+', definition['id']):
            raise pub.PreparationError('unsafe document ID')
        paths.add(path)
        ids.add(definition['id'])
        revision = definition['revision']
        with pub.root_handle(root) as content_fd:
            raw = read(content_fd, path, pub) if revision == 'WORKTREE' else blob(root, revision, path, pub)
        commit = head if revision == 'WORKTREE' else revision
        try:
            matches = raw == blob(root, commit, path, pub)
        except (subprocess.CalledProcessError, pub.PreparationError):
            matches = False
        target = 'sources/' + path
        put(target, raw, {'root': 'content', 'path': path, 'revision': revision})
        sources.append({**definition, 'commit': commit, 'snapshot_path': target,
                        'sha256': pub.digest(raw), 'bytes': len(raw), 'matches_commit': matches})
    if any(not set(v['documents']) <= ids for v in config['views']):
        raise pub.PreparationError('view refers to unknown document')
    model = {'schema_version': 3, 'profile': profile, 'profile_path': prefix,
             'repository': config['repository'], 'sources': sources, 'views': selected}
    snapshot['source-set.json'] = pub.canonical(model) + b'\n'
    snapshot['project.json'] = project.raw
    snapshot['input-bindings.json'] = pub.canonical(bindings) + b'\n'
    return snapshot


def verify_live_inputs(run, origin, pub):
    """Refuse changed renderer/profile or worktree input; fixed Git sources stay fixed."""
    record = json.loads((run / 'run.json').read_text())
    mounts = record['mounts']
    if mounts != record['identity'].get('mounts') or record['descriptor_path'] != record['identity'].get('descriptor_path'):
        raise pub.PreparationError('root binding mismatch')
    if str(origin) != mounts['content']:
        raise pub.PreparationError('content origin differs from prepared root')
    bindings = json.loads((run/'inputs/input-bindings.json').read_text())
    expected = {i['path']: i['sha256'] for i in record['identity']['inputs']}
    for logical, binding in bindings.items():
        if binding.get('revision', 'WORKTREE') != 'WORKTREE':
            continue
        with pub.root_handle(Path(mounts[binding['root']])) as fd:
            if pub.digest(read(fd, binding['path'], pub)) != expected[logical]:
                raise pub.PreparationError('publication input drift: ' + logical)
    with pub.root_handle(Path('/')) as fd:
        if read(fd, record['descriptor_path'].lstrip('/'), pub) != (run/'inputs/project.json').read_bytes():
            raise pub.PreparationError('project descriptor drift')
