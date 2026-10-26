#!/usr/bin/env python3
"""Current product qualification; historical comparison is a separate command."""
_bootstrap = (__file__.rpartition('/')[0] or '.') + '/../../engine/source_runtime.py'
with open(_bootstrap, 'rb') as _source:
    exec(compile(_source.read(), _bootstrap, 'exec'), {'__name__': '_publication_source_runtime'})

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from configure import ENGINE, PRODUCT, pub, project, product_lock, boundaries
import evidence
import source_model


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    lock, _, _ = product_lock.inspect(PRODUCT, pub)
    trials = lock['qualification']['trials']
    projects = [project.load(ENGINE, args.project, t['profile'], pub) for t in trials]
    if any(p.product != PRODUCT or not p.config.get('product') for p in projects):
        raise pub.PreparationError('qualification requires this versioned product instance')
    output = boundaries.for_project(args.output, projects[0], pub)
    if os.path.lexists(output):
        raise pub.PreparationError('qualification output must be a new directory')
    results = []
    with pub.absolute_directory(output, create=True) as out:
        terminal = pub.ResultCommit(out)
        def command(name, argv):
            start = time.monotonic()
            proc = subprocess.run(list(map(str, argv)), cwd=ENGINE, capture_output=True, timeout=1200)
            pub.write_bytes(out, name + '.stdout', proc.stdout)
            pub.write_bytes(out, name + '.stderr', proc.stderr)
            item = {'argv': list(map(str, argv)), 'exit_code': proc.returncode,
                    'seconds': round(time.monotonic() - start, 3)}
            if proc.returncode:
                raise RuntimeError(name + ' failed; inspect captured diagnostics')
            return proc.stdout, item
        try:
            for trial, selected in zip(trials, projects):
                profile, view = trial['profile'], trial.get('view')
                argv = [sys.executable, '-B', ENGINE/'engine/pub.py', '--project', selected.descriptor,
                        'preview', '--profile', profile]
                if view:
                    argv += ['--view', view]
                output_bytes, executed = command(profile, argv)
                run = Path(json.loads(output_bytes)['audit']).parents[1]
                record, ready, audit, manifest, _, _ = evidence.verify(run)
                source_model.verify_live_inputs(run, selected.content, pub)
                frozen, freeze_cmd = command(profile+'-candidate',
                    [sys.executable, '-B', ENGINE/'engine/pub.py', '--project', selected.descriptor,
                     'candidate', '--profile', profile, '--from-preview', str(run.relative_to(selected.output))])
                reviewed, review_cmd = command(profile+'-reading',
                    [sys.executable, '-B', ENGINE/'tools/reading-review.py', run,
                     '--corpus', PRODUCT/lock['qualification']['corpus']])
                _, sheets_cmd = command(profile+'-sheets',
                    [sys.executable, '-B', ENGINE/'tools/inspect-pages.py', run])
                if evidence.verify(run)[3] != manifest:
                    raise RuntimeError('evidence changed after derived inspection')
                item = {'profile': profile, 'attempt': str(run), 'preview_command': executed,
                        'candidate': json.loads(frozen), 'candidate_command': freeze_cmd, 'ready': ready,
                        'pages': sum(v['pages'] for v in audit['views']), 'artifact_files': len(manifest['files']),
                        'reading': json.loads(reviewed), 'reading_command': review_cmd,
                        'sheets_command': sheets_cmd, 'product': record['identity']['source']['product']}
                pub.write_json(out, profile + '.json', item)
                results.append(item)
                print(json.dumps(item, ensure_ascii=False), flush=True)
            product_lock.verify(projects[0], pub)
            pub.write_json(out, 'results.json', results)
            terminal.commit({'status': 'CURRENT_PRODUCT_CHECKED', 'trials': len(results),
                'results_sha256': pub.digest(pub.regular_bytes(out, 'results.json')),
                'historical_comparison': 'NOT_RUN', 'human_reading': 'NOT_RUN_BY_COMMAND',
                'reader_compatibility': 'NOT_RUN', 'formal_release': False})
        except BaseException as error:
            if terminal.is_committed():
                return
            pub.ResultCommit(out).commit({'status': 'CANCELLED' if isinstance(error, KeyboardInterrupt) else 'FAILED',
                                         'diagnostic': str(error), 'completed_trials': len(results)})
            raise


if __name__ == '__main__':
    main()
