"""Selected local runtime versus observed TeX closure; neither implies reproducibility."""
import hashlib
import importlib.metadata
import json
import platform
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

CONFIG = ('pyproject.toml', 'uv.lock', '.python-version')
TOOLS = ('pandoc', 'lualatex', 'pdftoppm', 'kpsewhich', 'uv')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def output(argv):
    return subprocess.check_output(argv, stderr=subprocess.STDOUT, text=True, timeout=30).strip()


def python_package(name):
    dist = importlib.metadata.distribution(name)
    files = {str(p): sha(dist.locate_file(p)) for p in dist.files or []
             if str(p).endswith(('.py','.so','.dylib')) and dist.locate_file(p).is_file()}
    return {'version':dist.version, 'files':files}


def require_managed(project):
    pinned = (project / '.python-version').read_text().strip()
    cfg = Path(sys.prefix) / 'pyvenv.cfg'
    if platform.python_version() != pinned or not cfg.is_file():
        raise RuntimeError('use uv sync/run --project publication --locked; pinned project venv required')
    # python-build-standalone used by uv has this marker. Also bind exact base
    # interpreter and config; the path alone is not a hostile-code security claim.
    managed = Path(sys.base_prefix) / 'lib' / f'python{sys.version_info.major}.{sys.version_info.minor}' / 'EXTERNALLY-MANAGED'
    if not managed.is_file() or 'uv' not in managed.read_text().lower():
        raise RuntimeError('uv-managed Python required; no system-Python fallback')
    lock = tomllib.loads((project / 'uv.lock').read_text())
    expected = next(p['version'] for p in lock['package'] if p['name'] == 'pypdf')
    if importlib.metadata.version('pypdf') != expected:
        raise RuntimeError('installed pypdf differs from uv.lock; run uv sync --locked')


def capture(project, layout):
    require_managed(project)
    if sys.platform != 'darwin': raise RuntimeError('macOS is the only qualified backend')
    tools = {}
    for name in TOOLS:
        path = shutil.which(name)
        if not path: raise RuntimeError('missing native tool: ' + name)
        path = str(Path(path).resolve())
        tools[name] = {'path':path, 'sha256':sha(path),
                       'version':output([path, '-v' if name=='pdftoppm' else '--version']).splitlines()[0]}
    style = (layout / 'kb-base.sty').read_text()
    fonts = sorted(set(re.findall(r'[A-Za-z0-9_-]+\.otf', style)))
    packages = sorted(set(x.strip() + '.sty' for group in re.findall(r'\\usepackage(?:\[[^]]*\])?\{([^}]+)\}', style) for x in group.split(',')))
    native = {}
    for name in fonts + packages + ['book.cls', 'luatexja-fontspec.sty']:
        path = output([tools['kpsewhich']['path'], name])
        if not path or not Path(path).is_file(): raise RuntimeError('unresolved TeX/font input: ' + name)
        native[name] = {'path':str(Path(path).resolve()), 'sha256':sha(path)}
    return {'platform':platform.platform(), 'architecture':platform.machine(),
            'python':{'version':platform.python_version(), 'path':str(Path(sys.executable).resolve()),
                      'sha256':sha(Path(sys.executable).resolve()), 'base_prefix':sys.base_prefix},
            'project':{n:sha(project/n) for n in CONFIG}, 'tools':tools,
            'pypdf':python_package('pypdf'), 'selected_tex_fonts':native,
            'boundary':'Selected files checked before/after. Additional .fls inputs are post-run observations, not a hermetic toolchain.'}


def doctor(project):
    import tempfile
    with tempfile.TemporaryDirectory(prefix='kb-doctor-') as tmp:
        policy = '(version 1)(deny default)(allow process*)(allow file-read*)'
        subprocess.run(['/usr/bin/sandbox-exec', '-p', policy, '/usr/bin/true'], check=True, capture_output=True)
        denied = subprocess.run(['/usr/bin/sandbox-exec','-p',policy,'/usr/bin/touch',str(Path(tmp)/'denied')], capture_output=True)
        if denied.returncode == 0 or (Path(tmp)/'denied').exists():
            raise RuntimeError('Seatbelt write-denial probe failed')
    result = capture(project, project/'latex')
    result['seatbelt'] = 'WRITE_DENIAL_OBSERVED'
    result['review'] = python_package('Pillow')
    lock = tomllib.loads((project / 'uv.lock').read_text())
    if result['review']['version'] != next(p['version'] for p in lock['package'] if p['name'] == 'pillow'):
        raise RuntimeError('installed Pillow differs from uv.lock; sync --group review')
    result['status'] = 'LOCAL_ENVIRONMENT_OBSERVED'
    print(json.dumps(result,ensure_ascii=False,indent=2))
