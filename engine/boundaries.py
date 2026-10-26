"""One write-boundary policy for configured and derived publication outputs.

Trusted local inputs, no concurrent directory replacement guarantee. Lexical
normalization must never hide a symlink; existing ancestors are opened no-follow.
"""
import os
from pathlib import Path


def absolute(path):
    return Path(os.path.abspath(path))


def check(path, *, engine, content, product, pub):
    path = absolute(path)
    engine, content, product = map(absolute, (engine, content, product))
    protected = (content, product, *(engine / n for n in
        ('engine', 'latex', 'tools', 'pyproject.toml', 'uv.lock', '.python-version')))
    if (path == Path('/') or engine == path or engine.is_relative_to(path) or
            any(path.is_relative_to(root) or root.is_relative_to(path) for root in protected)):
        raise pub.PreparationError('output must be outside content/product/implementation inputs')
    if any(p.startswith('.') for p in path.parts[1:]):
        raise pub.PreparationError('output may not target hidden administrative directories')
    # Validate without creating anything, including broken symlinks and files.
    ancestor = path
    while not os.path.lexists(ancestor):
        ancestor = ancestor.parent
    if ancestor == path and path.is_file():
        with pub.absolute_directory(path.parent) as fd:
            pub.regular_bytes(fd, path.name)
    else:
        with pub.absolute_directory(ancestor):
            pass
    # On common macOS volumes, different spelling/case can denote one inode.
    # No-follow validation above runs first; never resolve away a link.
    def same(a, b):
        return os.path.exists(a) and os.path.exists(b) and os.path.samefile(a, b)
    for root in protected:
        if (any(same(root, p) for p in (path, *path.parents)) or
                any(same(path, p) for p in (root, *root.parents))):
            raise pub.PreparationError('output aliases content/product/implementation inputs')
    if any(same(path, p) for p in (engine, *engine.parents)):
        raise pub.PreparationError('output aliases engine root or ancestor')
    return path


def for_project(path, project, pub):
    return check(path, engine=project.engine, content=project.content,
                 product=project.product, pub=pub)


def for_attempt(attempt, pub):
    """Only modern, verified evidence with explicit roots can gain derived files."""
    import evidence
    attempt = absolute(attempt)
    record = evidence.verify(attempt)[0]
    mounts = record.get('mounts')
    if not mounts or mounts != record['identity'].get('mounts'):
        raise pub.PreparationError('derived output requires explicit verified root bindings')
    output = check(mounts['output'], engine=mounts['engine'], content=mounts['content'],
                   product=mounts['product'], pub=pub)
    expected = output / 'preview' / record['build_id'] / record['attempt_id']
    if attempt != expected:
        raise pub.PreparationError('attempt is not at its bound output location')
    with pub.absolute_directory(attempt):
        pass
    return attempt
