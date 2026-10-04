"""Load English analyst-written case summaries with public source references."""
import hashlib
import json
from pathlib import Path

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def require(condition, message):
    if not condition:
        raise ValueError(message)

def route_input(library, objects):
    library = Path(library)
    manifest = read(library / 'manifest.json')
    return {'library_version': manifest['version'], 'objects': objects,
            'reader_index': read(library / 'reader_index.json'),
            'technical_index': read(library / 'technical_index.json'),
            'semantic_pairs': read(library / 'semantic_pairs.json')['same_task_pair_candidates']}

def validate_routes(route, library, objects, plan_sha):
    library = Path(library)
    require(route.get('source_plan_sha256') == plan_sha, 'Case route does not match frozen object plan')
    by_object = {obj['id']: obj for obj in objects}
    r_cases = read(library / 'reader_cases.json')
    t_cases = read(library / 'technical_cases.json')
    companions = read(library / 'technical_companions.json')
    r_entries = {entry['id']: entry for entry in read(library / 'reader_index.json')['entries']}
    t_entries = {entry['id']: entry for entry in read(library / 'technical_index.json')['entries']}
    for lane, cases, entries in [('reader', r_cases, r_entries), ('technical', t_cases, t_entries)]:
        require(isinstance(route.get(lane), list), f'Missing {lane} routes')
        for item in route[lane]:
            require(bool(item.get('task') and item.get('reason') and item.get('sufficiency_question')), f'Incomplete {lane} route')
            require(bool(item.get('object_ids')) and set(item['object_ids']) <= set(by_object), f'Unknown {lane} object')
            require(all(lane in by_object[obj]['lanes'] for obj in item['object_ids']), f'Object not assigned to {lane}')
            require(bool(item.get('case_ids')) and set(item['case_ids']) <= set(cases), f'Unknown {lane} case')
            require(set(item.get('entry_ids', [])) <= set(entries), f'Unknown {lane} entry')
            if lane == 'technical':
                require(bool(item.get('entry_ids')), 'Technical case requires a navigation entry')
                require(all(any(cid in entries[eid]['candidate_case_ids'] for eid in item['entry_ids']) for cid in item['case_ids']), 'Technical case does not belong to selected entry')
                for cid in item.get('companion_ids', []):
                    require(cid in companions and companions[cid]['paired_from'] in item['case_ids'], 'Unknown or unrelated companion')
            else:
                require(not item.get('companion_ids'), 'Reader cannot load Technical companions')
    require(isinstance(route.get('skipped_entries'), list), 'Missing skipped-entry reasons')
    selected = {(lane, eid) for lane in ['reader', 'technical'] for item in route[lane] for eid in item.get('entry_ids', [])}
    skipped = {(item.get('lane'), item.get('entry_id')) for item in route['skipped_entries'] if item.get('reason')}
    all_entries = {('reader', eid) for eid in r_entries} | {('technical', eid) for eid in t_entries}
    require(skipped == all_entries - selected, 'Unaccounted task entries')

def selected_for_lane(library, route, lane):
    library = Path(library)
    cases = read(library / ('reader_cases.json' if lane == 'reader' else 'technical_cases.json'))
    companions = read(library / 'technical_companions.json') if lane == 'technical' else {}
    selected = list(dict.fromkeys(cid for item in route[lane] for cid in item['case_ids']))
    companion_ids = list(dict.fromkeys(cid for item in route[lane] for cid in item.get('companion_ids', [])))
    def execution_view(record, field, technical=False):
        record = dict(record)
        blocked = {'plausible_alternative', 'writing_pattern', 'writing_moves', 'conditional_skeleton',
                   'analyst_assessment', 'analyst_research_note', 'analyst_critical_note',
                   'transfer_hypothesis', 'sufficiency_hypothesis', 'sufficient_alternative'}
        summary = record[field]
        if technical and 'source_description' in summary:
            source_fields = {'source_description', 'source_description_status', 'source_example_status',
                             'case_role', 'anchor_pages', 'analysis_status', 'verification_limit', 'source_review_limits'}
            record[field] = {key: value for key, value in summary.items() if key in source_fields}
        else:
            record[field] = {key: value for key, value in summary.items() if key not in blocked}
        return record
    records = []
    for cid in selected:
        field = 'full_case' if lane == 'reader' else 'full_source_record'
        # Unvalidated editing recipes remain research notes, never execution rules.
        records.append(execution_view(cases[cid], field, lane == 'technical'))
    return {'selection_basis': 'frozen target tasks; analyst reconstructions prompt questions, not verdicts or required target order',
            'routes': route[lane], 'complete_cases': records,
            'same_task_companions': [execution_view(companions[cid], 'full_source_record', True) for cid in companion_ids]}
