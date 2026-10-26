#!/usr/bin/env python3
"""Configure the knowledge-base product outside the content repository."""
_bootstrap = (__file__.rpartition('/')[0] or '.') + '/../../engine/source_runtime.py'
with open(_bootstrap, 'rb') as _source:
    exec(compile(_source.read(), _bootstrap, 'exec'), {'__name__': '_publication_source_runtime'})

import argparse
import json
import os
import sys
from pathlib import Path

PRODUCT = Path(__file__).absolute().parent
ENGINE = PRODUCT.parents[1]
sys.path.insert(0, str(ENGINE / 'engine'))
import pub
import project

PIN = 'df3fcc238f03a3832de55bc128049adebe323969'
SOURCE_BASE = 'a022de309c0ce5c3af0d306e57691f036d869698'
PROFILES = ('esd', 'cpp-handbook', 'cpp-handbook-full', 'cpp-handbook-rc1',
            'cpp-handbook-v1', 'cpp-failure-model')


def configure(content, workspace):
    content = Path(os.path.abspath(content))
    workspace = Path(os.path.abspath(workspace))
    if content == ENGINE:
        raise pub.PreparationError('content must be an independent checkout')
    # Never initialize over source, engine, historical publication, or evidence.
    if workspace == Path('/') or any(
        workspace == root or workspace.is_relative_to(root) or root.is_relative_to(workspace)
        for root in (content, PRODUCT, ENGINE / 'engine', ENGINE / 'latex', ENGINE / 'tools')
    ) or workspace == ENGINE or ENGINE.is_relative_to(workspace):
        raise pub.PreparationError('workspace must be outside content/product/implementation roots')
    if any(p.startswith('.') for p in workspace.parts[1:]):
        raise pub.PreparationError('workspace may not use hidden administrative directories')
    with pub.absolute_directory(content):
        pass
    pub.git_context(content)
    lock = json.loads((PRODUCT / 'migration.json').read_text())
    if lock['source_commit'] != SOURCE_BASE or lock['engine_pin'] != PIN:
        raise pub.PreparationError('product provenance mismatch')
    with pub.absolute_directory(PRODUCT) as fd:
        for entry in lock['byte_preserved_transfers']:
            relative = entry['destination'].removeprefix('products/knowledge-base/')
            raw = pub.regular_bytes(fd, relative) if '/' not in relative else None
            if raw is None:
                with pub.directory(fd, str(Path(relative).parent)) as parent:
                    raw = pub.regular_bytes(parent, Path(relative).name)
            if len(raw) != entry['bytes'] or pub.digest(raw) != entry['sha256']:
                raise pub.PreparationError('product migration bytes changed: ' + relative)
    config = {
        'schema_version': 1,
        'engine': {'repository': 'https://github.com/snkio027/publication-engine', 'commit': PIN},
        # Historical profiles retain their exact repository identity. GitHub
        # redirects the old name; this is not a second content repository.
        'source_repository': 'https://github.com/snkio027/kb',
        'content_root': str(content), 'product_root': str(PRODUCT), 'output_root': 'output',
        'profiles': {name: 'publication/profiles/' + name + '/profile.json' for name in PROFILES},
    }
    raw = pub.canonical(config) + b'\n'
    selected = project.Project(engine=ENGINE, content=content, product=PRODUCT,
        output=workspace/'output', descriptor=workspace/'project.json', raw=raw,
        config=config, profile='cpp-handbook', profile_path=config['profiles']['cpp-handbook'])
    project.engine_snapshot(selected, pub)
    with pub.absolute_directory(workspace, create=True) as fd:
        if os.listdir(fd):
            raise pub.PreparationError('workspace must be new or empty; existing files are never adopted')
        pub.write_bytes(fd, 'project.json', raw)
    return workspace / 'project.json'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--content', type=Path, required=True)
    parser.add_argument('--workspace', type=Path, required=True)
    args = parser.parse_args()
    try:
        path = configure(args.content, args.workspace)
        print(json.dumps({'status': 'CONFIGURED_NOT_BUILT', 'project': str(path), 'engine_pin': PIN}))
        return 0
    except (OSError, ValueError, pub.PreparationError) as error:
        print('FAILED: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
