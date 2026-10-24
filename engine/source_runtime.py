"""Source-only import policy for publication entry points.

Bootstrap this file with read_bytes/compile/exec, NOT an import: a cached copy of
the policy itself must never run first. CPython startup and this source remain
trusted. This does not sandbox arbitrary source code or replace engine pinning.
"""
import sys
from importlib.machinery import SourceFileLoader, SourcelessFileLoader


def source_code(loader, fullname):
    """Bypass all timestamp/hash caches, including explicit spec loaders."""
    filename = loader.get_filename(fullname)
    return loader.source_to_code(loader.get_data(filename), filename)


def reject_bytecode(loader, fullname):
    raise ImportError('publication source-only policy rejects bytecode-only module: ' + fullname)


sys.dont_write_bytecode = True
SourceFileLoader.get_code = source_code
SourcelessFileLoader.get_code = reject_bytecode
