"""Conservative local registry projection; full prose/evidence stays available.

This is not a semantic dependency guess. Paper, report, verified findings and evidence
remain complete by default. Global requests are never projected here.
"""
import copy
import hashlib
import json


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def project(base, tasks):
    result = copy.deepcopy(base)
    if any(t['kind'] == 'global_scope' for t in tasks):
        return result
    known = {'target', 'source_field', 'coverage', 'language'}
    if any(t['kind'] not in known for t in tasks):
        result['local_projection'] = {'mode': 'full', 'reason': 'Unrecognized task kind'}
        return result
    # Only task inventories/routing wrappers are narrowed. Full prose lets the local
    # reviewer detect wider dependencies and ask for expansion without guessing them.
    sources = {t['key'] for t in tasks if t['kind'] == 'source_field'}
    target_ids = {t['key'] for t in tasks if t['kind'] == 'target'}
    contexts = {t['data']['context_id'] for t in tasks if t['kind'] == 'target' and t['data'].get('context_id')}
    for t in tasks:
        if t['kind'] == 'language':
            target_ids.update(t['data'].get('target_unit_ids', []))
        target_ids.update(t['data'].get('member_ids', []))
    targets = base.get('all_target_inventory', [])
    contexts |= {r['context_id'] for r in targets if r['id'] in target_ids and r.get('context_id')}
    selected = [r for r in targets if r['id'] in target_ids or r.get('context_id') in contexts]
    # Coverage can locate any exact report quotation, and source-field checks may
    # point anywhere. Keep their complete report index; it is much smaller than prose.
    if any(t['kind'] in {'coverage', 'source_field'} for t in tasks):
        selected = targets
    for key, selected_rows in [('all_source_inventory', [r for r in base.get('all_source_inventory', []) if r['id'] in sources]),
                               ('all_target_inventory', selected)]:
        if key in base:
            result[key] = copy.deepcopy(selected_rows)
    source_ids = {t['data']['source_id'] for t in tasks if t['kind'] == 'coverage'}
    result['routes'] = {k: copy.deepcopy(v) for k, v in base.get('routes', {}).items() if k in source_ids}
    # Historical originals are needed by source-field checks, not by delivery of an
    # already-frozen A component. Those components and their actual judgments stay.
    if not sources and all(t['kind'] in {'coverage', 'language'} for t in tasks):
        result.pop('historical_report_evidence', None)
    # Keep complete selected frozen units and transitive canonical duplicates.
    units = base.get('frozen_a', [])
    owners = {c['id']: u['source_id'] for u in units for c in u['components']}
    wanted = set(source_ids)
    while True:
        more = set()
        for u in units:
            if u['source_id'] in wanted:
                for c in u['components']:
                    if c.get('duplicate_of'):
                        if c['duplicate_of'] not in owners:
                            raise ValueError('Missing canonical duplicate dependency')
                        more.add(owners[c['duplicate_of']])
        if more <= wanted:
            break
        wanted |= more
    if 'frozen_a' in base:
        result['frozen_a'] = [copy.deepcopy(u) for u in units if u['source_id'] in wanted]
    result['local_projection'] = {
        'mode': 'registry_only', 'base_sha256': digest(base),
        'task_ids': [t['id'] for t in tasks],
        'retained_whole_context': [k for k in ['manuscript', 'page_images', 'report_text', 'final_targets',
                                    'manuscript_evidence', 'review_execution_evidence', 'report_correspondence_evidence'] if k in base],
        'source_ids': sorted(source_ids), 'source_field_ids': sorted(sources),
        'note': 'Registry projection is not a claim of semantic sufficiency. Return an explicit dependency request if supplied context is insufficient; do not guess or pass.'}
    return result
