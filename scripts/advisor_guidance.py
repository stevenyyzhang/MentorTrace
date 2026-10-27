"""Pinned semantic guidance view with complete local source-field restoration."""
import copy,hashlib,json

INSTRUCTIONS='''EXPRESSION GUIDANCE v1 overrides redundant operation text only.
Each case's operations list contains its complete consolidated analyst guidance,
NEVER mentor quotations. A feature's operation_index refers to that list using a
zero-based index. It may be omitted ONLY when the case has exactly one operation,
in which case it is zero. This binds each feature's own conditions to its action.
Identical text across cases can use the ordinary exact $same transport reference.
Each original case/feature
keeps its own conditions, prohibited transfers, facts, examples, roles and limits.
Apply those boundaries individually even when operation text is shared. Topic
groups are routing aids, not equivalent cases; sharing an operation does not share
applicability or a manuscript verdict. Read every member and inspect exceptions.
Capacity/workload packing can place members of one operation in different batches;
inspect every member supplied HERE. A shared ID is never evidence of completion
in this or another batch. No globally related but absent case is implicitly checked.
For actionable evidence quote a supplied original example, condition or factual
qualification; do not quote canonical guidance as original source text, or use
$input to retrieve the replaced operations/language-feature operation fields.
An original analytical-operation quotation explicitly retained as a feature's
source_quote with evidence_account.field="operations" remains citable as that
analytical account, never as mentor wording or as the rewritten canonical text.
Source IDs and feature IDs remain unchanged for draft/report references. Every
case and active use still needs an explicit disposition. No new screening call is
required and Concern's independent full-paper review remains unchanged.'''

def source_features(record):
    public=record.get('public_language_features')
    if isinstance(public,list):return public
    if isinstance(public,dict) and public.get('$projection_of')=='language_features':
        return [{k:record['language_features'][r['index']][k] for k in r['keys']} for r in public['items']]
    return record['language_features']

def source_fields(record):
    return {f'operations/{i}':v for i,v in enumerate(record['operations'])}|{
      f'language_features/{i}/operation':f['operation'] for i,f in enumerate(source_features(record))}

def signature(record):
    return hashlib.sha256(json.dumps(source_fields(record),ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def validate(registry,records):
    if registry.get('version')!=1:raise ValueError('Unsupported guidance registry')
    byid={r['id']:r for r in records}
    if set(registry['records'])!=set(byid):raise ValueError('Guidance source coverage differs')
    all_units=set()
    for rid,row in registry['records'].items():
        if row['source_fields_sha256']!=signature(byid[rid]):raise ValueError('Stale guidance source fields')
        paths=[]
        for u in row['units']:
            if u['id'] in all_units or not u['id'].startswith(rid+':'):raise ValueError('Invalid guidance unit identity')
            all_units.add(u['id']);paths+=u['paths']
            if u['guidance_id'] not in registry['guidance']:raise ValueError('Unknown guidance ID')
        if len(paths)!=len(set(paths)) or set(paths)!=set(source_fields(byid[rid])):
            raise ValueError('Guidance field loss or duplication')
    for g in registry['guidance'].values():
        if not isinstance(g['operation'],str) or not g['operation'].strip():raise ValueError('Empty canonical guidance')
    return True

def subset(registry,ids):
    rows={i:registry['records'][i] for i in ids}
    gids={u['guidance_id'] for r in rows.values() for u in r['units']}
    return {'version':1,'records':copy.deepcopy(rows),
      'guidance':{g:copy.deepcopy(registry['guidance'][g]) for g in sorted(gids)}}

def separate(review,administration):
    registry=review['expression_guidance'];records=review['expression_sources']['records']
    validate(registry,records)
    administration['expression_guidance']=copy.deepcopy(registry)
    topic_sources={}
    for record in records:
        saved={k:copy.deepcopy(record[k]) for k in ['operations','language_features','public_language_features'] if k in record}
        administration['expression_fields'].setdefault(record['id'],{}).update(saved)
        feature_indices={};gids=[]
        original_features=copy.deepcopy(source_features(record))
        record['operations']=[]
        for u in registry['records'][record['id']]['units']:
            gid=u['guidance_id'];topic=registry['guidance'][gid]['topic']
            topic_sources.setdefault(topic,set()).add(record['id'])
            if gid not in gids:
                gids.append(gid);record['operations'].append(registry['guidance'][gid]['operation'])
            for path in u['paths']:
                bits=path.split('/');idx=int(bits[1])
                if bits[0]!='operations':
                    fid=original_features[idx]['id'];feature_indices[fid]=gids.index(gid)
                    for feature in record['language_features']:
                        if feature['id']==fid:feature.pop('operation');feature['operation_index']=gids.index(gid)
        # Public projections may be explicit lists or same-record references.
        if isinstance(record.get('public_language_features'),list):
            for f in record['public_language_features']:
                if f.get('id') in feature_indices and 'operation' in f:f.pop('operation');f['operation_index']=feature_indices[f['id']]
        elif isinstance(record.get('public_language_features'),dict):
            for item in record['public_language_features'].get('items',[]):
                item['keys']=['operation_index' if k=='operation' else k for k in item['keys']]
        if len(record['operations'])==1:
            for feature in record['language_features']:feature.pop('operation_index',None)
            public=record.get('public_language_features')
            if isinstance(public,list):
                for feature in public:feature.pop('operation_index',None)
            elif isinstance(public,dict):
                for item in public.get('items',[]):item['keys']=[k for k in item['keys'] if k!='operation_index']
    review.pop('expression_guidance')
    review['expression_operation_families']=[{'topic':k,'source_ids':sorted(v)} for k,v in sorted(topic_sources.items()) if len(v)>1]

def restore(result,administration):
    result['expression_guidance']=copy.deepcopy(administration['expression_guidance'])

def withheld_path(path):
    return bool(path and path[0]=='expression_sources' and ('operations' in path or ('operation' in path and any(k in path for k in ['language_features','public_language_features']))))

def operation_excerpt_visible(record,excerpt):
    return isinstance(excerpt,str) and bool(excerpt.strip()) and any(
      f.get('evidence_kind')=='analytical_operation' and f.get('evidence_account',{}).get('field')=='operations'
      and excerpt in f.get('source_quote','') for f in record.get('language_features',[]))
