#!/usr/bin/env python3
"""Current product adapter fidelity; no implicit historical engine/build lookup."""
_bootstrap = (__file__.rpartition('/')[0] or '.') + '/../../engine/source_runtime.py'
with open(_bootstrap, 'rb') as _source:
    exec(compile(_source.read(), _bootstrap, 'exec'), {'__name__': '_publication_source_runtime'})

import argparse
import importlib.util
import json
import subprocess
from pathlib import Path
import configure
from configure import pub, product_lock, boundaries, PRODUCT
import fidelity
import preview
import source_model


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--content', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    selected, lock = configure.definition(args.content, args.output.parent / 'instance-check')
    output = boundaries.for_project(args.output, selected, pub)
    reports = []
    for profile, relative in lock['profiles'].items():
        path = PRODUCT / relative
        config = json.loads(path.read_text())
        spec = importlib.util.spec_from_file_location('product_adapter', path.with_name('adapter.py'))
        adapter = importlib.util.module_from_spec(spec); spec.loader.exec_module(adapter)
        for src in config['sources']:
            with pub.absolute_directory(selected.content) as fd:
                raw = (source_model.read(fd, src['path'], pub) if src['revision'] == 'WORKTREE'
                       else source_model.blob(selected.content, src['revision'], src['path'], pub))
            parsed = json.loads(subprocess.check_output(
                ['pandoc', '-f', config.get('source_format', 'markdown-smart'), '-t', 'json'], input=raw))
            audit = fidelity.adapt_checked(parsed, adapter, src, preview.text)[-1]
            reports.append({'profile': profile, 'source': src['id'], 'source_sha256': pub.digest(raw),
                            'revision': src['revision'], 'status': audit['status']})
    product_lock.verify(selected, pub)
    report = {'status': 'PASS', 'product': selected.config['product'], 'engine_pin': lock['engine'],
              'source_adapter_checks': reports, 'migration_comparison': 'NOT_RUN',
              'boundary': 'Local adapter checks; not PDF, C++ or technical qualification'}
    with pub.absolute_directory(output.parent, create=True) as fd:
        pub.write_json(fd, output.name, report)
    print(json.dumps({'status': 'PASS', 'source_adapter_checks': len(reports)}))


if __name__ == '__main__':
    main()
