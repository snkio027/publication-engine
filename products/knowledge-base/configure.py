#!/usr/bin/env python3
"""Configure from the current product lock, never from migration facts."""
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
import product_lock
import boundaries


def definition(content, workspace):
    content, workspace = map(boundaries.absolute, (content, workspace))
    if content == ENGINE:
        raise pub.PreparationError('content must be an independent checkout')
    boundaries.check(workspace, engine=ENGINE, content=content, product=PRODUCT, pub=pub)
    with pub.absolute_directory(content):
        pass
    pub.git_context(content)
    lock, identity, _ = product_lock.inspect(PRODUCT, pub)
    config = {'schema_version': 1, 'product': identity,
              **{key: lock[key] for key in ('engine', 'source_repository', 'profiles')},
              'content_root': str(content), 'product_root': str(PRODUCT), 'output_root': 'output'}
    raw = pub.canonical(config) + b'\n'
    first = next(iter(config['profiles']))
    selected = project.Project(engine=ENGINE, content=content, product=PRODUCT,
        output=workspace/'output', descriptor=workspace/'project.json', raw=raw,
        config=config, profile=first, profile_path=config['profiles'][first])
    project.engine_snapshot(selected, pub)
    return selected, lock


def configure(content, workspace):
    selected, _ = definition(content, workspace)
    with pub.absolute_directory(selected.descriptor.parent, create=True) as fd:
        if os.listdir(fd):
            raise pub.PreparationError('workspace must be new or empty; existing files are never adopted')
        pub.write_bytes(fd, 'project.json', selected.raw)
    return selected.descriptor


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--content', type=Path, required=True)
    parser.add_argument('--workspace', type=Path, required=True)
    args = parser.parse_args()
    try:
        path = configure(args.content, args.workspace)
        config = json.loads(path.read_text())
        print(json.dumps({'status': 'CONFIGURED_NOT_BUILT', 'project': str(path),
                          'engine_pin': config['engine'], 'product': config['product']}))
        return 0
    except (OSError, ValueError, pub.PreparationError) as error:
        print('FAILED: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
