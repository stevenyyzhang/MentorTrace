"""Lossless response references and checked carryover. No semantic decisions or calls."""
import copy
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RULES=['scripts/native_delivery.py','scripts/report_revision.py','scripts/delivery_reliability.py','scripts/delivery_recovery.py','scripts/review_workflow.py','scripts/delivery_efficiency.py','scripts/prepare_delivery_delta.py','scripts/lossless_delivery_wire.py','scripts/delivery_global_views.py',
       'scripts/audit_merge_obligations.py','scripts/verification_basis.py','scripts/review_quality.py',
       'scripts/report_concision.py','scripts/expression_realization.py','scripts/review_contract.py','scripts/review_integrity.py','scripts/delivery_runtime.py','scripts/validation_cache.py','scripts/layout_evidence.py','scripts/execution_trace.py','scripts/delivery_protocol.py','scripts/delivery_cycle.py','scripts/delivery_focus.py','scripts/canonical_draft.py','scripts/coverage_basis.py','scripts/runtime_guidance.py','scripts/draft_context.py',
       '.agents/skills/mentortrace/scripts/audit_report_preservation.py',
       *['.agents/skills/mentortrace/references/'+name+'.md' for name in
         ['generic-coverage-efficiency','delivery-compact','delivery-hardening','delivery-reliability','delivery-preservation','report-language','source-fidelity','expression-realization',
          'review-workflow','execution-efficiency','review-stability','repair-contract',
          'section-argument','expression']]]

INSTRUCTIONS='''LOSSLESS DELIVERY REFERENCES v1:
Keep all independent judgments, conditions and evidence. To avoid retyping the SAME complete
task text, a string may be returned as {"$input_text":"<assigned task_id>"}. Available texts
are target/source_field data.text and coverage data.component.source_quote. Use this only
when that complete string is the appropriate focused quotation; do not broaden an assertion
or combine independent components to use a shorter reference. For any excerpt repeated in
your response, optionally declare texts:{"Q1":"exact text",...} once and use {"$text":"Q1"}.
Programs substitute exact strings before the ordinary validators. No approximate matching,
inferred quotes, automatic pass or source judgment is allowed. Other strings remain literal.
Carried review records have explicit prior provenance. Review the complete current context
and every assigned task; flag any conflict with a carried record in global_scope.issues.
Global completeness, clarity and changed Original checks remain actual tasks. Individually valid unchanged B rows may be reused with their source/report/dependency bindings; no whole-report pass is inferred.
'''

def require(ok,message):
    if not ok:raise ValueError(message)

def rule_binding():
    return {rel:hashlib.sha256((ROOT/rel).read_bytes()).hexdigest() for rel in RULES}


def compatible_local_rules(previous,current,receipt):
    """Explicit old/new hashes for transport-only migration; scientific gates excluded."""
    if previous==current:return True
    allowed={'scripts/delivery_runtime.py','scripts/review_workflow.py','scripts/delivery_protocol.py',
             'scripts/delivery_cycle.py','scripts/lossless_delivery_wire.py','scripts/delivery_global_views.py','scripts/delivery_efficiency.py',
             'scripts/prepare_delivery_delta.py','.agents/skills/mentortrace/references/delivery-compact.md'}
    changed={k for k in set(previous or {})|set(current) if (previous or {}).get(k)!=current.get(k)}
    if not receipt or not receipt.get('reviewer') or not receipt.get('reason'):return False
    if 'scripts/review_contract.py' in changed:
        import ast
        old_path=Path(receipt.get('previous_rule_root',''))/'scripts/review_contract.py'
        current_path=ROOT/'scripts/review_contract.py'
        if not old_path.is_file() or hashlib.sha256(old_path.read_bytes()).hexdigest()!=(previous or {}).get('scripts/review_contract.py'):return False
        old_tree=ast.parse(old_path.read_text(encoding='utf-8-sig'));new_tree=ast.parse(current_path.read_text(encoding='utf-8-sig'))
        keep=lambda tree:ast.dump(ast.Module(body=[n for n in tree.body if not isinstance(n,ast.FunctionDef) or n.name!='normalize'],type_ignores=[]),include_attributes=False)
        if keep(old_tree)!=keep(new_tree):return False
        allowed.add('scripts/review_contract.py')
    if not changed<=allowed:return False
    if receipt.get('scientific_validation_unchanged') is not True:return False
    expected={k:{'before':(previous or {}).get(k),'after':current.get(k)} for k in changed}
    return receipt.get('changes')==expected

def input_texts(tasks):
    result={}
    for t in tasks:
        if t['kind'] in {'target','source_field'}:text=t['data']['text']
        elif t['kind']=='coverage':text=t['data']['component']['source_quote']
        else:continue
        require(isinstance(text,str),'Reference input must be literal text')
        result[t['id']]=text
    return result

def expand(value,texts,inputs):
    require(isinstance(texts,dict) and all(isinstance(k,str) and isinstance(v,str) for k,v in texts.items()),
            'Shared texts must be literal strings')
    if isinstance(value,list):return [expand(v,texts,inputs) for v in value]
    if isinstance(value,dict):
        for key,table in [('$text',texts),('$input_text',inputs)]:
            if key in value:
                require(set(value)=={key} and isinstance(value[key],str) and value[key] in table,
                        'Unknown or malformed exact text reference')
                return table[value[key]]
        return {k:expand(v,texts,inputs) for k,v in value.items()}
    return value

def checked_carryover(ledger,contract=None):
    """Recompute eligibility; never trust claimed carried IDs or populated review fields."""
    import prepare_delivery_delta as delta
    carry=ledger.get('carryover')
    if not carry:return {'source_ids':[],'target_ids':[],'language':[],'bindings':{},'reason':'No approved carryover'}
    path=Path(carry['previous_ledger'])
    require(delta.audit.digest(path)==carry['previous_ledger_sha256'],'Previous carryover ledger changed')
    previous=delta.audit.read(path)
    migration=carry.get('affected_scope_assessment',{}).get('local_rule_compatibility')
    if not compatible_local_rules(previous.get('delivery_rule_binding'),rule_binding(),migration) or previous.get('delivery_contract')!=contract:
        return {'source_ids':[],'target_ids':[],'language':[],'bindings':{},
                'reason':'Earlier review rules absent or changed; all tasks require review'}
    assessment=carry.get('affected_scope_assessment')
    require(assessment is not None,'Carryover needs an affected-scope assessment')
    fresh,plan=delta.prepare(path,previous['report'],ledger['report'],
                           [s['path'] for s in ledger['sources']],assessment)
    require(plan['previous_valid'] or plan.get('partial_review_eligible'),'Earlier delivery has no valid full or local review')
    for field,ids,rows in [('units','carried_source_ids','source_ids'),('target_units','carried_target_ids','target_ids')]:
        require(carry.get(ids)==plan[ids],'Carryover eligibility changed')
        actual={r['id']:r for r in ledger[field]};expected={r['id']:r for r in fresh[field]}
        for ident in plan[ids]:require(actual.get(ident)==expected[ident],'Carried review was edited: '+ident)
    language=fresh.get('language_realization',{}).get('review',{}).get('groups',[])
    require(ledger.get('language_realization',{}).get('review',{}).get('groups',[])==language,
            'Carried language review differs from checked scope')
    if previous.get('language_realization'):
        for key in ['response','evidence']:
            require(ledger['language_realization'][key]==fresh['language_realization'][key],
                    'Language source changed; renew its review')
    if previous.get('verified_review_reuse'):
        require(ledger.get('verified_review_reuse')==fresh.get('verified_review_reuse'),
                'Carryover verification basis changed')
    bindings={str(path.resolve()):delta.audit.digest(path),str(Path(previous['report']).resolve()):delta.audit.digest(previous['report'])}
    def bind(value):
        if isinstance(value,list):
            for v in value:bind(v)
        elif isinstance(value,dict):
            if 'path' in value and 'sha256' in value:
                require(delta.audit.digest(value['path'])==value['sha256'],'Carried evidence changed')
                bindings[value['path']]=value['sha256']
            for v in value.values():bind(v)
    # A failed sibling judgment must not poison otherwise valid local carryover.
    # The immutable original ledger/report remain bound above for provenance.
    bind([u for u in previous['units'] if u['id'] in plan['carried_source_ids']])
    bind([u for u in previous['target_units'] if u['id'] in plan['carried_target_ids']])
    bind(language)
    if fresh.get('coverage_carryover'):
        ref=fresh['coverage_carryover'];bindings[ref['previous_b']]=ref['sha256']
    # Bind the actual shared provenance records used by retained judgments.
    for ident in ['target:'+i for i in plan['carried_target_ids']]+['source_field:'+i for i in plan['carried_source_ids']]+['language:'+g['draft_label'] for g in language]:
        ref=previous.get('task_provenance',{}).get(ident,{})
        if ref.get('review_id'):
            from delivery_runtime import expand_provenance
            bind(expand_provenance(ref,previous.get('review_provenance_index',{})))
    return {'source_ids':plan['carried_source_ids'],'target_ids':plan['carried_target_ids'],
            'language':copy.deepcopy(language),'coverage':copy.deepcopy(fresh.get('coverage_carryover',{}).get('rows',[])),'coverage_binding':fresh.get('coverage_carryover'),'bindings':bindings,'provenance':copy.deepcopy(carry),
            'reason':'Exact context/evidence plus recorded dependency assessment; not a new review'}

def preflight(ledger,bindings):
    """Collect all available file/hash failures before a model submission."""
    errors=[]
    expected=dict(bindings)
    if ledger.get('language_realization_required'):
        for key in ['response','evidence']:
            item=ledger['language_realization'][key];expected[item['path']]=item['sha256']
    for name,sha in expected.items():
        p=Path(name)
        if not p.is_file():errors.append('Missing source: '+name)
        elif hashlib.sha256(p.read_bytes()).hexdigest()!=sha:errors.append('Changed source: '+name)
    require(not errors,'Delivery preflight failed:\n'+'\n'.join(errors))

def inspect_values(tasks,values):
    """Collect common local defects together; ordinary gates still decide acceptance."""
    issues=[]
    def add(t,field,problem,kind='format'):
        issues.append({'task_id':t['id'],'field':field,'problem':problem,'kind':kind})
    for t in tasks:
        if t['id'] not in values:
            add(t,'result','Assigned task has no result');continue
        v=values[t['id']]
        if t['kind']=='source_field' and bool(v.get('components'))==bool(v.get('non_substantive_reason')):
            add(t,'components','Provide obligations OR a non-substantive reason, not both/neither')
        lists=[]
        if t['kind']=='coverage':lists.append(('report_quotes',v.get('report_quotes',[])))
        if t['kind']=='source_field':
            for n,c in enumerate(v.get('components',[])):
                lists.append((f'components[{n}].target_quotes',c.get('target_quotes',[])))
                if not isinstance(c.get('source_quote'),str) or c['source_quote'] not in t['data']['text']:
                    add(t,f'components[{n}].source_quote','Source excerpt is not literal in the bound source field')
        for field,quotes in lists:
            if not isinstance(quotes,list) or any(not isinstance(q,str) for q in quotes):
                add(t,field,'Expected exact strings or explicit lossless text references')
        for n,a in enumerate(v.get('assertions',[])):
            field=f'assertions[{n}]'
            if not isinstance(a.get('quote'),str) or a['quote'] not in t['data'].get('text',''):
                add(t,field+'.quote','Assertion excerpt is not literal in its target block')
            if a.get('status')=='reused_verified' and a.get('reuse_reference',{}).get('field') not in {'relation','gap','impact'}:
                add(t,field+'.reuse_reference','Requested future work cannot ground an implemented fact; inspect actual evidence','needs_judgment')
            if a.get('status')=='supported' and not a.get('evidence'):
                add(t,field+'.evidence','Supported assertion has no evidence','needs_judgment')
    return issues
