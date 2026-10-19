"""File-layout compatibility for this research workspace; no analysis or network calls."""
from pathlib import Path as _Path
import fnmatch
import json

ROOT = _Path(__file__).resolve().parents[2]
MAP_FILE = ROOT / '00_導覽' / '檔案搬移對照.json'
_DOC = json.loads(MAP_FILE.read_text(encoding='utf-8')) if MAP_FILE.exists() else {}
_MAP = _DOC.get('mapping', {})
_FOLDERS = _DOC.get('folder_mapping', {})


def _destination(p):
    try:
        relative = p.relative_to(ROOT).as_posix()
    except ValueError:
        try:
            relative = p.relative_to(_Path(_DOC.get('root', str(ROOT)))).as_posix()
        except ValueError:
            return p
    if relative in _MAP:
        return ROOT / _MAP[relative]
    head, _, tail = relative.partition('/')
    if head in _FOLDERS:
        return ROOT / _FOLDERS[head] / tail
    return p


class ResearchPath(type(_Path())):
    """Resolve recorded old paths while keeping real current paths usable."""

    def __init__(self, *args):
        original = _Path(*args)
        super().__init__(_destination(original))

    def __truediv__(self, key):
        return type(self)(_Path(str(self)) / key)

    def glob(self, pattern, **kwargs):
        if _Path(str(self)) != ROOT or '/' in str(pattern) or '\\' in str(pattern):
            yield from super().glob(pattern, **kwargs)
            return
        # Legacy code used a flat root. Search recorded old names without
        # traversing Git, backups, or newly unrelated directories.
        seen = set()
        for p in super().glob(pattern, **kwargs):
            seen.add(str(p))
            yield p
        for old, new in _MAP.items():
            if '/' not in old and fnmatch.fnmatchcase(old, str(pattern)):
                p = type(self)(ROOT / new)
                if p.exists() and str(p) not in seen:
                    seen.add(str(p))
                    yield p


def rebind_workspace_paths(namespace):
    """Rebind only retained Path objects rooted in this workspace."""
    changed = []
    for name, value in list(namespace.items()):
        if isinstance(value, _Path):
            try:
                _Path(str(value)).relative_to(ROOT)
            except ValueError:
                continue
            namespace[name] = ResearchPath(str(value))
            changed.append(name)
    namespace['Path'] = ResearchPath
    return changed
