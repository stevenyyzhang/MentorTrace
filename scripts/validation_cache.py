"""Invocation-scoped immutable file cache; never a semantic-review cache."""
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from pathlib import Path
import hashlib

_current = ContextVar('mentortrace_validation_cache', default=None)


@contextmanager
def session():
    if _current.get() is not None:
        yield _current.get(); return
    state = {'files': {}, 'reads': 0, 'hits': 0}
    token = _current.set(state)
    try: yield state
    finally: _current.reset(token)


def scoped(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        with session(): return function(*args, **kwargs)
    return wrapped


def content(path):
    path = Path(path).resolve(); state = _current.get()
    if state is None: return path.read_bytes()
    stat = path.stat(); stamp = (stat.st_size, stat.st_mtime_ns)
    old = state['files'].get(str(path))
    if old:
        if old[0] != stamp: raise ValueError('Evidence changed during validation: ' + str(path))
        state['hits'] += 1; return old[1]
    data = path.read_bytes(); state['files'][str(path)] = (stamp, data)
    state['reads'] += 1; return data


def digest(path): return hashlib.sha256(content(path)).hexdigest()


def text(path): return content(path).decode('utf-8-sig')
