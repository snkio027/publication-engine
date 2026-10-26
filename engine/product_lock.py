"""Optional consumer product lock; separate from immutable migration evidence."""
import json
import re
from pathlib import Path
from source_model import read, path_parts


def inspect(root, pub):
    with pub.absolute_directory(root) as fd:
        raw = read(fd, 'product.json', pub)
        lock = json.loads(raw)
        if (lock.get('schema_version') != 1 or not re.fullmatch(r'[a-z][a-z0-9-]*', lock.get('id', ''))
                or not re.fullmatch(r'\d+\.\d+\.\d+', lock.get('version', ''))):
            raise pub.PreparationError('unsupported product manifest')
        entries = lock['inputs']
        if not entries or len({e['path'] for e in entries}) != len(entries):
            raise pub.PreparationError('missing/duplicate product inputs')
        for entry in entries:
            path_parts(entry['path'], pub)
            data = read(fd, entry['path'], pub)
            if len(data) != entry['bytes'] or pub.digest(data) != entry['sha256']:
                raise pub.PreparationError('product lock mismatch: ' + entry['path'])
        for profile in lock['profiles'].values():
            if profile not in {e['path'] for e in entries}:
                raise pub.PreparationError('profile missing from product lock')
    identity = {key: lock[key] for key in ('id', 'version', 'repository', 'subdirectory')}
    identity.update(manifest='product.json', manifest_sha256=pub.digest(raw),
                    input_set_sha256=pub.digest(pub.canonical(entries)))
    return lock, identity, raw


def verify(project, pub):
    declared = project.config.get('product')
    if declared is None:
        return {'status': 'UNVERSIONED_CONSUMER_INPUTS'}
    lock, identity, raw = inspect(project.product, pub)
    if declared != identity:
        raise pub.PreparationError('product identity changed; configure a new workspace')
    if any(project.config[key] != lock[key] for key in ('engine', 'profiles', 'source_repository')):
        raise pub.PreparationError('project differs from selected product contract')
    return {**identity, 'engine_pin': lock['engine'], 'status': 'LOCK_VERIFIED'}
