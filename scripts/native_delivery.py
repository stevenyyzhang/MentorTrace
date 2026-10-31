"""Resumable native delivery closure; never manufacture an acceptance verdict."""
from contextlib import contextmanager
from pathlib import Path
import os
import json
import time
import mentortrace_v1 as m


@contextmanager
def locked(path):
    """OS lock releases on crash; a surviving lock file is not a running process."""
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    stream=path.open('a+b')
    if stream.tell()==0:stream.write(b'0');stream.flush()
    stream.seek(0)
    try:
        if os.name=='nt':
            import msvcrt
            msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1)
        else:
            import fcntl
            fcntl.flock(stream.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
    except OSError:
        stream.close();raise ValueError('Another process owns this native execution')
    try:yield
    finally:
        stream.seek(0)
        if os.name=='nt':msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)
        else:fcntl.flock(stream.fileno(),fcntl.LOCK_UN)
        stream.close()


def execute(bundle,calls,args,authorization):
    import delivery_cycle as cycle, report_revision as revision, review_workflow as w
    from execution_policy import validate_authorization
    bundle=Path(bundle).resolve();calls=Path(calls).resolve();calls.mkdir(parents=True,exist_ok=True)
    validate_authorization(authorization,args.model,args.effort,args.service_tier)
    w.verify_bundle(bundle)
    binding={'bundle':str(bundle),'sha256':m.sha(bundle/'manifest.json'),'model':args.model,'effort':args.effort,'service_tier':args.service_tier,'max_report_revisions':2}
    revision.save_once(calls/'native-binding.json',binding)
    started=time.monotonic();active=bundle;rounds=[];seen=set()
    with locked(calls/'native.lock'):
        for n in range(3):
            # The native reviewer cycle revalidates saved raw evidence and both gates
            # on resume; it cannot silently trust a persisted delivery_ready flag.
            result=cycle.execute_records(active,calls/f'round-{n}',args,authorization)
            rounds.append(result)
            if result.get('delivery_ready'):
                answer={**result,'native_report_revisions':n,'native_rounds':rounds,
                        'native_wall_seconds':time.monotonic()-started,'report_edited':n>0}
                m.save(calls/'native-result.json',answer);return answer
            semantic=result.get('next_action')=='revise_report_and_recheck_affected'
            if not semantic or n==2:
                answer={**result,'native_report_revisions':n,'native_rounds':rounds,
                        'boundary':'Completed bounded native recovery; unresolved transport/record defect or report revision budget remains. Saved state is resumable; not a deliverable report.'}
                m.save(calls/'native-continuation.json',answer);return answer
            wave=result['waves'][-1];ctx=m.read(Path(wave['bundle'])/'context.json')
            fingerprint=(m.sha(ctx['report_correspondence_evidence']['path']),json.dumps(result.get('failed',[]),sort_keys=True))
            m.require(fingerprint not in seen,'No progress: same report and same defects; do not repeat approval requests')
            seen.add(fingerprint)
            folder=calls/f'report-revision-{n+1}'
            from execution_trace import span
            with span(calls/'trace','prepare-report-revision','deterministic_preparation',round=n+1):
                revision.prepare(wave['bundle'],wave['responses'],folder,result.get('failed',[])+result.get('language_blockers',[]))
            with span(calls/'trace','report-revision','revision_and_validation',round=n+1):
                revision.submit(folder,args,authorization)
            with span(calls/'trace','prepare-affected-recheck','deterministic_preparation',round=n+1):
                active=revision.recheck(folder)
        raise AssertionError('Unreachable native cycle')
