"""Versioned integration transport. Exact sharing never supplies a missing judgment."""
import copy

FLAG = 'integration_contract_v1'

OUTPUT = '''INTEGRATION OUTPUT v1: Return the ordinary required tables, optionally with
integration_output_version:1 and shared_values:{V1:<actual value>,...}. An exact
{"$value":"V1"} may replace any repeated value. A row may use
"$fields":{"ref":"V1","names":["reason","evidence"]} to copy only those
fields from a shared object; never specify the same field locally as well.
In source_requirement_resolutions a row may use component_ids:[...] instead of
component_id ONLY when every field of the returned decision applies to each member;
candidate_reviews may likewise use candidate_ids, and dispositions/organization_dispositions
may use input_ids. Different statuses, routes, conditions or evidence require separate
rows (which can still reference shared reasons/evidence). The program expands each
explicit member; missing IDs remain errors. Canonical Source groups are hypotheses:
inspect all original alias quotes, conditions and occurrences before sharing a decision.
Write one concise actual decision/evidence account for equivalent questions and
reference it in the required views. Keep every source/candidate ID, assessment,
route, condition and occurrence explicitly accounted for. Same topic, output ID,
or Source assessment does NOT establish equivalent meaning. Distinct requirements
need distinct decisions. Independently check Verify decisions before sharing them;
do not copy a Source verdict as your own. Definitions are local to this response
or capacity part, not references to another response. Unused definitions are invalid.
Ordinary fully expanded JSON remains valid. The program expands exact references
before all ordinary validators; no extra semantic ledger or review call is created.'''

MERGE_ROLE = '''MERGE OWNERSHIP: Integrate the frozen initial findings, candidates and
Source requirement inventory into compatible proposed findings/editorial actions.
Source records are grounded inputs and hypotheses, not final verdicts. Preserve
their independent questions and unknowns in routes/closure goals; resolve conflicts
needed for integration with manuscript evidence. Do not repeat source decomposition,
routine successful execution checks or a full scientific verification sweep.
Return the required finding/organization/candidate dispositions and editorial
selection only. Do not add source_requirement_audit, source_expression_records,
source_requirement_resolutions or source_fidelity_checks tables here. These have
no separate Merge responsibility. Verify owns independent scientific, fidelity,
source-component and withdrawal decisions. Unsupported withdrawals remain forbidden;
unresolved requirements must stay visible. Do not delete a supported optional
structure/style action merely because measured comparative benefit is unavailable.'''

VERIFY_ROLE = '''VERIFY OWNERSHIP: Independently adjudicate scientific validity,
source fidelity, each source component/candidate and every withdrawal. Source and
Merge decisions are proposals. Inspect the shared original observations once per
actual question; explicitly distinguish manuscript truth, execution completeness
and delivery routing. Reuse the actual evidence account across views only where
it really applies. Preserve all conditions and occurrence scope. Extra Merge records
are registered as delivery_candidates with kind integration_extra; route each
substantive request or exclude with evidence in the SAME candidate_reviews table.
Do not add a separate audit table or a later integration review phase.'''

SOURCE = '''SOURCE OWNERSHIP: The candidate's original.question is its one literal
question, not three repeated relation/gap/closure fields. source_record retains the
complete origin. check_refs gives exact original check IDs/hashes; the complete
check is in original_stage_context/execution tasks, not missing evidence. Inspect the
same actual observation/calculation once and reference its exact value through
judgments/$judgment; still separately decide requirement necessity, execution
completeness and stage coverage. A successful calculation cannot settle a different
prerequisite, condition, reader task or unattempted check. Only stage_scope tasks
perform the whole-stage coverage comparison. Other tasks use the complete supplied
evidence to decide their assigned original requirements/checks, not to repeat it.
No implicit pass, topic-based deduplication, or missing-task inference is allowed.'''


def expand(response, context):
    if 'integration_output_version' not in response:
        return copy.deepcopy(response)
    if context.get(FLAG) != 1 or response['integration_output_version'] != 1:
        raise ValueError('Integration output protocol not enabled/version mismatch')
    definitions = response.get('shared_values', {})
    if not isinstance(definitions, dict):
        raise ValueError('Shared values must be an object')
    used = set(); selections = {}; whole = set()
    def definition(key, trail, names=None):
        if not isinstance(key, str) or key not in definitions or key in trail:
            raise ValueError('Missing/cyclic shared integration value')
        used.add(key)
        if names is None: whole.add(key)
        else: selections.setdefault(key, set()).update(names)
        return visit(definitions[key], trail + (key,))
    def visit(value, trail=()):
        if isinstance(value, list):
            return [visit(v, trail) for v in value]
        if not isinstance(value, dict):
            return copy.deepcopy(value)
        if '$value' in value:
            if set(value) != {'$value'}:
                raise ValueError('Ambiguous shared integration value')
            return definition(value['$value'], trail)
        result = {k: visit(v, trail) for k, v in value.items() if k != '$fields'}
        if '$fields' in value:
            spec = value['$fields']
            if not isinstance(spec, dict) or set(spec) != {'ref', 'names'}:
                raise ValueError('Invalid shared field reference')
            names = spec['names']
            if not isinstance(names, list) or not all(isinstance(n, str) for n in names):
                raise ValueError('Invalid shared field names')
            donor = definition(spec['ref'], trail, names)
            if (not isinstance(names, list) or not names or
                    not all(isinstance(n, str) for n in names) or len(set(names)) != len(names) or
                    not isinstance(donor, dict) or not set(names) <= set(donor) or set(names) & set(result)):
                raise ValueError('Missing/conflicting shared integration fields')
            result.update({n: copy.deepcopy(donor[n]) for n in names})
        return result
    result = visit({k: v for k, v in response.items()
                    if k not in {'integration_output_version', 'shared_values'}})
    if used != set(definitions):
        raise ValueError('Unused shared integration values may contain an unrouted opinion')
    for key, names in selections.items():
        if key not in whole and set(definitions[key]) != names:
            raise ValueError('Unused shared integration fields may contain an unrouted opinion')
    for table, singular, plural in GROUPS:
        if table not in result: continue
        expanded = []
        for row in result[table]:
            if plural not in row:
                expanded.append(row); continue
            members = row[plural]
            if (singular in row or not isinstance(members, list) or not members or
                    not all(isinstance(i, str) and i for i in members) or len(set(members)) != len(members)):
                raise ValueError('Invalid explicit integration decision group')
            expanded.extend({**copy.deepcopy({k:v for k,v in row.items() if k != plural}), singular: ident}
                            for ident in members)
        result[table] = expanded
    return result


GROUPS = [('source_requirement_resolutions', 'component_id', 'component_ids'),
          ('candidate_reviews', 'candidate_id', 'candidate_ids'),
          ('dispositions', 'input_id', 'input_ids'),
          ('organization_dispositions', 'input_id', 'input_ids')]


def require_expanded(response):
    def walk(value):
        if isinstance(value, dict):
            if set(value) & {'integration_output_version', 'shared_values', '$value', '$fields'}:
                raise ValueError('Expand integration transport before canonical validation')
            for child in value.values(): walk(child)
        elif isinstance(value, list):
            for child in value: walk(child)
    walk(response)
    for table, _, plural in GROUPS:
        if any(plural in row for row in response.get(table, [])):
            raise ValueError('Expand integration decision groups before canonical validation')


MERGE_FIELDS = {'findings', 'dispositions', 'organization_suggestions',
                'organization_dispositions', 'editorial_selection', 'candidate_reviews', 'limits'}


def extra_candidates(merged):
    """Unexpected output stays raw and enters the existing Verify accounting path."""
    import delivery_reliability as reliability
    result = []
    def anchors(value):
        found = []
        if isinstance(value, dict):
            if 'page' in value and ('quote' in value or value.get('kind') == 'image'):
                found.append(copy.deepcopy(value))
            else:
                for v in value.values(): found.extend(anchors(v))
        elif isinstance(value, list):
            for v in value: found.extend(anchors(v))
        return found
    for field in sorted(set(merged) - MERGE_FIELDS):
        value = merged[field]
        if value in (None, [], {}, ''): continue
        rows = value if isinstance(value, list) else [value]
        for index, row in enumerate(rows):
            result.append({'id': f'merge:candidate:extra:{field}:{index}',
                'kind': 'integration_extra', 'origin_stage': 'merge',
                'origin_path': f'{field}/{index}', 'source_sha256': reliability.digest(row),
                'source': copy.deepcopy(row), 'anchors': anchors(row),
                'text': 'Assess every substantive request in this exact extra Merge record; route or exclude with evidence.'})
    return result


def canonical_context(context):
    """Read-only external canonical records for partition-local duplicate decisions."""
    units = context.get('initial_source_review', {}).get('source_requirements', [])
    components = {c['id']: c for u in units for c in u['components']}
    return {c['duplicate_of']: copy.deepcopy(components[c['duplicate_of']])
            for c in components.values() if c.get('duplicate_of') in components}


def output_estimate(context, stage):
    """Planning allowance, not generated tokens or a quota of review findings.

    Compression is optional: never assume the model will share all decisions.
    Count independently required output views before taking a smaller input as
    permission to collapse an output-heavy Verify pass into one call.
    """
    total = (250 if stage == 'merge' else 500) * len(context.get('input_findings', []))
    total += 500 * (len(context.get('input_organization_suggestions', [])) +
                    len(context.get('excluded_organization_candidates', [])))
    total += 200 * len(context.get('delivery_candidates', []))
    if stage == 'verify':
        total += 100 * sum(len(u['components']) for u in context.get('initial_source_review', {}).get('source_requirements', []))
        total += 200 * len(context.get('coverage_execution_issues', []))
    return total
