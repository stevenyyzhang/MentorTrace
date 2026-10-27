"""Bind explicit reuse of frozen verification; never infer semantic equivalence."""
import hashlib
import json
from pathlib import Path


def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def require(ok,message):
    if not ok:raise ValueError(message)


def build(run):
    run=Path(run).resolve()
    names=['final.json','findings_raw.json','RESULT_FREEZE.json','inputs/FREEZE.json',
           'inputs/protocol.json','inputs/paper/body.json','inputs/paper/manifest.json',
           'calls/verify/response.json','calls/verify/request.json','calls/verify/record.json',
           'calls/verify/raw_response.json']
    missing=[n for n in names if not (run/n).is_file()]
    if missing:return {'version':1,'available':False,'reason':'No complete frozen verification chain','missing':missing}
    record=read(run/'calls/verify/record.json')
    if record.get('schema_validated') is not True:
        return {'version':1,'available':False,'reason':'Verification acceptance is not established'}
    # Bind the complete frozen inputs, including applicable references and image bytes.
    for relative in read(run/'inputs/FREEZE.json')['files']:
        path=(run/'inputs'/relative).resolve()
        require(path.is_relative_to(run/'inputs'),'Frozen input escapes its root')
        names.append('inputs/'+relative)
    binding={'version':1,'available':True,'run':str(run),
             'files':{n:digest(run/n) for n in sorted(set(names))},
             'scope':'Prior accepted verification only; reuse still needs an explicit claim/conditions/uncertainty comparison. Not a new manuscript check.'}
    validate(binding)
    return binding


def validate(binding):
    require(binding.get('version')==1 and binding.get('available') is True,'No reusable verified review')
    run=Path(binding['run']).resolve();files=binding['files']
    required={'final.json','findings_raw.json','RESULT_FREEZE.json','inputs/FREEZE.json',
              'inputs/protocol.json','inputs/paper/body.json','inputs/paper/manifest.json',
              'calls/verify/response.json','calls/verify/request.json','calls/verify/record.json',
              'calls/verify/raw_response.json'}
    require(required<=set(files),'Incomplete verification reuse binding')
    for name,sha in files.items():
        path=(run/name).resolve();require(path.is_relative_to(run),'Reuse source escapes its root')
        require(path.is_file() and digest(path)==sha,'Verified reuse source changed: '+name)
    for name,sha in read(run/'inputs/FREEZE.json')['files'].items():
        require(files.get('inputs/'+name)==sha,'Frozen verification input binding incomplete')
    record=read(run/'calls/verify/record.json')
    require(record.get('schema_validated') is True,'Verification was not accepted')
    for key,name in [('request_sha256','request.json'),('response_sha256','response.json'),('raw_response_sha256','raw_response.json')]:
        require(record.get(key)==files['calls/verify/'+name],'Verification record does not bind '+name)
    require(read(run/'final.json')==read(run/'calls/verify/response.json'),'Frozen final differs from accepted verification')
    freeze=read(run/'RESULT_FREEZE.json')
    require(freeze.get('final')==files['final.json'] and freeze.get('raw')==files['findings_raw.json'],'Diagnostic result freeze changed')
    final=read(run/'final.json')
    return {'binding':binding,'findings':{f['id']:f for f in final.get('findings',[])}}


def validate_reference(assertion,context):
    require(context is not None,'Reused claim lacks a bound verified review')
    reference=assertion.get('reuse_reference',{})
    source=context['findings'].get(reference.get('finding_id'))
    field=reference.get('field')
    require(source is not None and field in {'relation','gap','impact'},'Reused claim must reference an accepted diagnostic statement, not a requested future action')
    require(isinstance(source.get(field),str) and source[field].strip(),'Empty verified diagnostic statement')
    comparison=reference.get('comparison',{})
    require(comparison.get('same_claim') is True and comparison.get('conditions_and_uncertainty_preserved') is True
            and comparison.get('no_new_fact') is True and isinstance(comparison.get('reason'),str)
            and bool(comparison['reason'].strip()),'Explicit unchanged-claim comparison required; hashes are not semantic approval')
    # The whole bound field remains the reference; no shortened quote can hide qualifiers.
    return {'finding_id':source['id'],'field':field,'complete_verified_statement':source[field],
            'scope':'Reused verified judgment, not fresh manuscript evidence'}
