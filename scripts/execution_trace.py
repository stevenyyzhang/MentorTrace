"""Append-only stage spans; overlapping wall times must be unioned, not summed."""
from contextlib import contextmanager
from pathlib import Path
import datetime
import json
import time
import uuid


@contextmanager
def span(folder, phase, kind, **metadata):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    path=folder/(uuid.uuid4().hex+'.json');started=datetime.datetime.now(datetime.timezone.utc).isoformat();timer=time.monotonic();status='completed'
    try:yield
    except BaseException:
        status='failed';raise
    finally:
        path.write_text(json.dumps({'phase':phase,'kind':kind,'started_utc':started,
            'ended_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'elapsed_seconds':time.monotonic()-timer,'status':status,'metadata':metadata,
            'limit':'Wall span, not CPU or exclusive causal attribution; model usage comes from its audit.'},ensure_ascii=False,indent=2),encoding='utf-8')
