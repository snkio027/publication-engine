"""Explicit engine/content/product/output roots. No implicit current repository."""
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

from source_model import git, read, blob

OUTPUT_MARKER = b'publication-engine-output-v1\n'


@dataclass(frozen=True)
class Project:
    engine: Path
    content: Path
    product: Path
    output: Path
    descriptor: Path
    raw: bytes
    config: dict
    profile: str
    profile_path: str

    def provenance(self, pub):
        from product_lock import verify
        return {'engine': pub.git_context(self.engine),
                'content': pub.git_context(self.content),
                'product': verify(self, pub),
                'engine_pin': self.config['engine'],
                'project_sha256': pub.digest(self.raw)}

    def roots(self):
        return {name: str(getattr(self, name)) for name in ('engine', 'content', 'product', 'output')}


def load(engine, descriptor, profile, pub):
    descriptor = Path(descriptor).absolute()
    # Validate the entire actual path with no-follow handles, including parents.
    with pub.root_handle(Path('/')) as fd:
        raw = read(fd, str(descriptor).lstrip('/'), pub)
    config = json.loads(raw)
    if config.get('schema_version') != 1 or not isinstance(config.get('profiles'), dict):
        raise pub.PreparationError('unsupported project descriptor')
    if profile not in config['profiles'] or not re.fullmatch('[a-z][a-z0-9-]*', profile):
        raise pub.PreparationError('unknown project profile')
    pin = config['engine']
    if not re.fullmatch('[0-9a-f]{40}', pin.get('commit', '')) or not pin.get('repository'):
        raise pub.PreparationError('engine must be pinned to a full Git commit and repository')
    paths = {}
    for name in ('content', 'product', 'output'):
        value = config[name + '_root']
        if not isinstance(value, str) or not value:
            raise pub.PreparationError('missing root: ' + name)
        # Normalize lexical .. in descriptor-relative roots, not symlinks.
        paths[name] = Path(os.path.abspath(descriptor.parent / value))
    for name in ('content', 'product'):
        with pub.root_handle(Path('/')) as fd, pub.directory(fd, str(paths[name]).lstrip('/')):
            pass
    engine = Path(engine).absolute()
    if engine == paths['content'] or engine == paths['product']:
        raise pub.PreparationError('engine must be an independent checkout')
    from boundaries import check
    check(paths['output'], engine=engine, content=paths['content'], product=paths['product'], pub=pub)
    profile_path = config['profiles'][profile]
    pub.parts(profile_path)
    if profile_path != '/'.join(pub.parts(profile_path)) or not profile_path.endswith('/profile.json'):
        raise pub.PreparationError('profile path must be a canonical relative profile.json')
    selected = Project(engine=engine, descriptor=descriptor, raw=raw, config=config,
                       profile=profile, profile_path=profile_path, **paths)
    from product_lock import verify
    verify(selected, pub)
    return selected


def open_output(project, pub):
    """Initialize only an empty dedicated output root; never adopt existing data."""
    from boundaries import for_project
    for_project(project.output, project, pub)
    with pub.absolute_directory(project.output, create=True) as out:
        names = os.listdir(out)
        if not names:
            pub.write_bytes(out, '.publication-output', OUTPUT_MARKER)
        elif '.publication-output' not in names or pub.regular_bytes(out, '.publication-output') != OUTPUT_MARKER:
            raise pub.PreparationError('output is not an initialized publication workspace')


def engine_snapshot(project, pub):
    """Selected engine bytes must equal the committed pin; no floating latest."""
    snapshot = {}
    paths = []
    for folder in ('engine', 'latex', 'tools'):
        paths += git(project.engine, 'ls-tree', '-r', '--name-only', project.config['engine']['commit'], '--', folder).decode().splitlines()
        live = sorted(str(p.relative_to(project.engine)) for p in (project.engine/folder).rglob('*')
                      if p.is_file() and '__pycache__' not in p.parts)
        expected = sorted(p for p in paths if p.startswith(folder + '/'))
        if live != expected:
            raise pub.PreparationError('engine input collection differs from pinned commit: ' + folder)
    paths += ['pyproject.toml', 'uv.lock', '.python-version']
    with pub.root_handle(project.engine) as fd:
        for path in paths:
            data = read(fd, path, pub)
            if data != blob(project.engine, project.config['engine']['commit'], path, pub):
                raise pub.PreparationError('engine pin mismatch: ' + path)
            # A stable virtual snapshot namespace preserves the v1 renderer ABI.
            snapshot['publication/' + path] = data
    return snapshot
