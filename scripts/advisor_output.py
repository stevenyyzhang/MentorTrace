"""Versioned, reversible Advisor output. No judgments are inferred or model calls made.

The ordinary validators consume the expanded response, not this transport format.
Historical requests without the pinned contract keep their original protocol.
"""
import copy
import json
from collections import Counter

VERSION = 1
MARKERS = {'$same', '$input', '$anchor', '$image_anchor', '$object_anchor', '$rows', '$absent'}
NO_OUTPUT = {'keep', 'not_applicable', 'unknown', 'unfinished'}
ROLES = {'keep': 'no_change', 'not_applicable': 'no_change',
         'unknown': 'unresolved', 'unfinished': 'unresolved',
         'optional_improvement': 'expression_improvement'}

INSTRUCTIONS = '''ADVISOR OUTPUT CONTRACT v1 (one complete review, reversible records):
Return {advisor_output_version:1,definitions:{},response:{...ordinary review fields...}}.
The ordinary Concern, Expression, check, finding and source-use requirements still apply.
Every assigned source/use needs its own explicit disposition. Never infer completion
from an ID inventory, a related Concern's result or a shared explanation.
Write each genuinely shared analysis ONCE in definitions, e.g. {A1:"full target analysis"};
{"$same":"A1"} uses that exact value wherever needed, including a check and transfers.
Share only when the analysis actually answers each source's operation/conditions.
Distinct applicability, counterevidence, boundaries and dependencies need distinct text.
Do not repeat source descriptions or the same target analysis in synonymous fields.
Choose an exact source value with {"$input":["expression_sources","records",0,...field path]}.
This copies that supplied string, not a new target judgment. A partial source excerpt
may instead be written literally. Source facts never establish missing target facts.
Manuscript text is preserved as ordered $passages. {"$anchor":"P1.3"} copies that
exact passage with its page; {"$anchor":["P1.3","P1.5"]} joins the inclusive contiguous
range. Choose the actual location; this does not certify interpretation or glyphs.
An ordinary exact text/image anchor remains valid. Do not fabricate image observations.
Lists of records may use {"$rows":{columns:[...],values:[[...],...],constants:{...}}}.
Each row has exactly one value per column. Constants are explicitly shared fields;
{"$absent":true} means an absent optional field in that cell, never an omitted source.
For writing_transfers, source_kind is resolved from the supplied unique source_id.
For explicit keep/not_applicable/unknown/unfinished decisions, finding_ids and
suggestion_ids may be omitted: they are necessarily empty, never positive links.
The no_change/unresolved/expression_improvement contribution role is derived only
from its explicit decision; feature_ids and supporting_concern_ids remain explicit.
Required repairs must explicitly distinguish repair_realization from expression_repair.
For source_use_dispositions, use_id is the ONE-BASED index in INPUT.source_uses.
Return each use_id once with status, transfer_ids and its reason/reason_ref. The program
expands its source/target IDs; it NEVER assigns checked status or reasoning for you.
Check finding_ids may be omitted only because the inverse of explicit finding.check_ids
is generated. Every target/check, scope, decision, gain, limitation and applicable
alternative still requires actual model inspection. Nonmatches need a concrete
operation/condition reason; KEEP needs actual anchored comparison. All existing
validators run after expansion. Unfinished work is not silently completed.
Keep the full source language/feature references for later report drafting. This
format adds no screening pass and does not restrict independent full-paper review.'''


def require(ok, message):
    if not ok:
        raise ValueError(message)


def dump(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def passages(context):
    result = {}
    for page in context['manuscript']:
        for index, text in enumerate(page['text'].splitlines(keepends=True), 1):
            result[f"P{page['page']}.{index}"] = (page['page'], index, text)
    return result


def project(context):
    """Label exact extraction lines, retaining their original order and whitespace."""
    result = copy.deepcopy(context)
    if result.get('advisor_output_contract') != VERSION:
        return result
    if result.get('advisor_locators') == 1:
        import advisor_locators
        result['manuscript_locators']=advisor_locators.catalogue(context)
    for page in result['manuscript']:
        page['text'] = {'$passages': {f"P{page['page']}.{i}": text
                        for i, text in enumerate(page['text'].splitlines(keepends=True), 1)}}
    return result


def inflate(context):
    result = copy.deepcopy(context)
    locators=result.pop('manuscript_locators',None)
    for page in result.get('manuscript', []):
        if isinstance(page['text'], dict) and set(page['text']) == {'$passages'}:
            require(result.get('advisor_output_contract') == VERSION, 'Unpinned passage projection')
            chunks = page['text']['$passages']
            require(isinstance(chunks, dict) and list(chunks) ==
                    [f"P{page['page']}.{i}" for i in range(1, len(chunks) + 1)], 'Passage order changed')
            require(all(isinstance(v, str) for v in chunks.values()), 'Invalid passage text')
            page['text'] = ''.join(chunks.values())
    if locators is not None:
        import advisor_locators
        require(result.get('advisor_locators')==1 and locators==advisor_locators.catalogue(result), 'Changed or unpinned locator catalogue')
    return result


def source_kinds(context):
    import writing_transfer
    result = {}
    for kind, ident in writing_transfer.sources(context):
        result.setdefault(ident, []).append(kind)
    result['manuscript'] = ['manuscript']
    return result


def _input_value(context, spec):
    path = spec.get('path') if isinstance(spec, dict) else spec
    require(isinstance(path, list) and path and path[0] in
            {'cards', 'expression_sources', 'manuscript', 'source_uses'}, 'Invalid input reference')
    if context.get('advisor_review_view')==1:
        import advisor_views
        require(not advisor_views.withheld_path(path), 'Draft-only field is not visible review evidence')
    if context.get('advisor_guidance')==1:
        import advisor_guidance
        require(not advisor_guidance.withheld_path(path), 'Original operation replaced by analyst guidance; quote visible source evidence')
    value = context
    for key in path:
        if context.get('advisor_efficiency') == 1 and path[0]=='expression_sources':
            import advisor_efficiency
            require(key not in advisor_efficiency.LOCAL_FIELDS, 'Input reference names a locally withheld narrative field')
        require((isinstance(value, dict) and isinstance(key, str) and key in value) or
                (isinstance(value, list) and type(key) is int and 0 <= key < len(value)),
                'Unknown input reference')
        value = value[key]
    require(isinstance(value, str), 'Input reference must copy an exact supplied string')
    if isinstance(spec, dict):
        require(set(spec) == {'path', 'start', 'end'} and type(spec['start']) is int and
                type(spec['end']) is int and 0 <= spec['start'] < spec['end'] <= len(value),
                'Invalid input substring')
        value = value[spec['start']:spec['end']]
    return value


def expand(value, context):
    """Resolve explicit references; derive only mechanically determined fields."""
    if 'advisor_output_version' not in value:
        return copy.deepcopy(value)
    require(context.get('advisor_output_contract') == VERSION and
            value.get('advisor_output_version') == VERSION, 'Unpinned/unsupported Advisor output contract')
    require(set(value) == {'advisor_output_version', 'definitions', 'response'}, 'Unexpected output envelope field')
    definitions = value['definitions']
    require(isinstance(definitions, dict) and len(definitions) <= 20000, 'Invalid output definitions')
    locations = passages(context)
    remaining = [2000000]

    def decode(node, stack=(), depth=0):
        remaining[0] -= 1
        require(remaining[0] >= 0 and depth < 80, 'Output reference expansion limit')
        if isinstance(node, list):
            return [decode(v, stack, depth + 1) for v in node]
        if not isinstance(node, dict):
            return node
        if '$same' in node:
            ident = node['$same']
            require(set(node) == {'$same'} and isinstance(ident, str) and ident in definitions,
                    'Unknown output definition')
            require(ident not in stack, 'Cyclic output definition')
            return decode(definitions[ident], stack + (ident,), depth + 1)
        if '$input' in node:
            require(set(node) == {'$input'}, 'Invalid input reference shape')
            return _input_value(context, node['$input'])
        if '$anchor' in node:
            require(set(node) == {'$anchor'}, 'Invalid passage anchor')
            ids = [node['$anchor']] if isinstance(node['$anchor'], str) else node['$anchor']
            require(isinstance(ids, list) and len(ids) in {1, 2} and
                    all(isinstance(i, str) and i in locations for i in ids), 'Unknown passage anchor')
            first, last = locations[ids[0]], locations[ids[-1]]
            require(first[0] == last[0] and first[1] <= last[1], 'Invalid passage range')
            return {'page': first[0], 'quote': ''.join(locations[f'P{first[0]}.{i}'][2]
                    for i in range(first[1], last[1] + 1))}
        if '$object_anchor' in node:
            import advisor_locators
            require(set(node)=={'$object_anchor'}, 'Invalid object locator shape')
            return advisor_locators.expand(node['$object_anchor'],context)
        if '$image_anchor' in node:
            require(context.get('advisor_efficiency') == 1 and set(node)=={'$image_anchor'}, 'Unpinned image locator')
            item=node['$image_anchor']
            if context.get('advisor_shared_results')==1 and isinstance(item,dict) and 'page_locator' in item:
                available={f"IMG:P{p['page']}":p['page'] for p in context['manuscript']}
                require(set(item)<={'page','page_locator','description'} and item['page_locator'] in available,'Unknown/invalid image page locator')
                page=available[item['page_locator']]
                require('page' not in item or (type(item['page']) is int and item['page']==page),'Contradictory image page locator')
                item={'page':page,'description':item.get('description')}
            require(isinstance(item,dict) and set(item)=={'page','description'} and
                    type(item['page']) is int and item['page'] in {p['page'] for p in context['manuscript']} and
                    isinstance(item['description'],str) and item['description'].strip(), 'Invalid image locator')
            return {'page':item['page'],'kind':'image','description':item['description']}
        if '$rows' in node:
            require(set(node) == {'$rows'} and isinstance(node['$rows'], dict), 'Invalid row table')
            table = node['$rows']; columns = table.get('columns'); rows = table.get('values')
            constants = table.get('constants', {})
            require(set(table) <= {'columns', 'values', 'constants'} and isinstance(columns, list) and
                    all(isinstance(k, str) for k in columns) and len(columns) == len(set(columns)) and
                    isinstance(constants, dict) and not set(columns) & set(constants) and
                    isinstance(rows, list), 'Invalid table columns/constants')
            result = []
            for row in rows:
                require(isinstance(row, list) and len(row) == len(columns), 'Output table row width mismatch')
                record = {k: decode(v, stack, depth + 1) for k, v in constants.items()}
                for key, cell in zip(columns, row):
                    if cell != {'$absent': True}:
                        record[key] = decode(cell, stack, depth + 1)
                result.append(record)
            return result
        require(not MARKERS & set(node), 'Misplaced output marker')
        return {k: decode(v, stack, depth + 1) for k, v in node.items()}

    result = decode(value['response'])
    require(isinstance(result, dict), 'Expanded response must be an object')
    if 'analyses' in result or 'concern_results' in result or 'expression_results' in result:
        import advisor_results
        result=advisor_results.expand(result,context)
    import advisor_efficiency
    advisor_efficiency.expand_groups(result, context)
    kinds = source_kinds(context)
    for row in result.get('writing_transfers', []):
        if 'source_kind' not in row:
            candidates = kinds.get(row.get('source_id'), [])
            require(len(candidates) == 1, 'Missing/ambiguous source kind')
            row['source_kind'] = candidates[0]
        import advisor_brief
        advisor_brief.expand_metadata(row, context)
        if row.get('decision') in NO_OUTPUT:
            row.setdefault('finding_ids', []); row.setdefault('suggestion_ids', [])
        contribution = row.get('expression_contribution')
        if isinstance(contribution, dict) and 'role' not in contribution and row.get('decision') in ROLES:
            contribution['role'] = ROLES[row['decision']]
    uses = context.get('source_uses', [])
    for row in result.get('source_use_dispositions', []):
        if 'use_id' not in row:
            continue
        index = row.pop('use_id')
        require(type(index) is int and 1 <= index <= len(uses), 'Unknown source use ID')
        source = uses[index - 1]
        for key in ['expression_id', 'target_kind', 'target_id']:
            require(key not in row or row[key] == source[key], 'Contradictory source use IDs')
            row[key] = source[key]
    if isinstance(result.get('findings'), list):
        for check in result.get('checks', []):
            if 'finding_ids' not in check:
                check['finding_ids'] = [f['id'] for f in result['findings']
                                        if check['id'] in f.get('check_ids', [])]
    return result


def encode(response, context):
    """Offline lossless replay encoder. Never paraphrases or merges different text."""
    require(context.get('advisor_output_contract') == VERSION, 'Pin output contract before encoding')
    data = copy.deepcopy(response); kinds = source_kinds(context)
    use_ids = {(u['expression_id'], u['target_kind'], u['target_id']): i
               for i, u in enumerate(context.get('source_uses', []), 1)}
    for row in data.get('writing_transfers', []):
        if kinds.get(row.get('source_id')) == [row.get('source_kind')]:
            row.pop('source_kind')
        if row.get('decision') in NO_OUTPUT:
            for key in ['finding_ids', 'suggestion_ids']:
                if row.get(key) == []:
                    row.pop(key)
        contribution = row.get('expression_contribution', {})
        if 'role' in contribution and contribution['role'] == ROLES.get(row.get('decision')):
            contribution.pop('role')
    for row in data.get('source_use_dispositions', []):
        key = tuple(row[k] for k in ['expression_id', 'target_kind', 'target_id'])
        require(key in use_ids, 'Unsupplied use in replay')
        row['use_id'] = use_ids[key]
        for k in ['expression_id', 'target_kind', 'target_id']:
            row.pop(k)
    for check in data.get('checks', []):
        inverse = [f['id'] for f in data.get('findings', []) if check['id'] in f.get('check_ids', [])]
        if check.get('finding_ids') == inverse:
            check.pop('finding_ids')
    supplied = {}

    def collect(node, path):
        if context.get('advisor_review_view')==1:
            import advisor_views
            if advisor_views.withheld_path(path):return
        if context.get('advisor_guidance')==1:
            import advisor_guidance
            if advisor_guidance.withheld_path(path):return
        if isinstance(node, str) and len(node) >= 60:
            ref = {'$input': path}
            if len(dump(ref)) + 8 < len(dump(node)):
                old = supplied.get(node)
                if old is None or len(dump(ref)) < len(dump(old)):
                    supplied[node] = ref
        elif isinstance(node, dict):
            for k, v in node.items():
                if context.get('advisor_efficiency') == 1 and path and path[0]=='expression_sources':
                    import advisor_efficiency
                    if k in advisor_efficiency.LOCAL_FIELDS:continue
                collect(v, path + [k])
        elif isinstance(node, list):
            for i, v in enumerate(node): collect(v, path + [i])
    for key in ['cards', 'expression_sources', 'manuscript', 'source_uses']:
        if key in context: collect(context[key], [key])
    counts = Counter()

    def count(node):
        if isinstance(node, (str, dict, list)):
            serial = dump(node)
            if len(serial) >= 40: counts[serial] += 1
        if isinstance(node, dict):
            require(not MARKERS & set(node), 'Reserved marker in ordinary response')
            for v in node.values(): count(v)
        elif isinstance(node, list):
            for v in node: count(v)
    count(data)
    definitions, ids = {}, {}

    def pack(node, intern=True):
        serial = dump(node)
        if isinstance(node, str) and node in supplied:
            return supplied[node]
        if intern and counts[serial] > 1 and (counts[serial] - 1) * len(serial) > counts[serial] * 22 + 15:
            if serial not in ids:
                ident = 'D' + str(len(ids) + 1); ids[serial] = ident
                definitions[ident] = pack(node, False)
            return {'$same': ids[serial]}
        if isinstance(node, dict): return {k: pack(v) for k, v in node.items()}
        if isinstance(node, list):
            if len(node) >= 3 and all(isinstance(r, dict) and r for r in node):
                columns = list(dict.fromkeys(k for r in node for k in r))
                constants = {k: pack(node[0][k]) for k in columns if all(k in r and r[k] == node[0].get(k) for r in node)}
                columns = [k for k in columns if k not in constants]
                table = {'$rows': {'columns': columns, 'values': [[pack(r[k]) if k in r else {'$absent': True}
                          for k in columns] for r in node], 'constants': constants}}
                plain = [pack(r) for r in node]
                return table if len(dump(table)) < len(dump(plain)) else plain
            return [pack(v) for v in node]
        return node
    packed = pack(data)
    used = set()
    def reachable(node):
        if isinstance(node, dict):
            if set(node) == {'$same'} and node['$same'] not in used:
                used.add(node['$same']); reachable(definitions[node['$same']])
            else:
                for child in node.values(): reachable(child)
        elif isinstance(node, list):
            for child in node: reachable(child)
    reachable(packed)
    definitions = {k: v for k, v in definitions.items() if k in used}
    result = {'advisor_output_version': VERSION, 'definitions': definitions, 'response': packed}
    require(expand(result, context) == response, 'Output replay changed a field or judgment')
    return result


def preflight(response, context):
    """Collect local deficiencies together; not semantic review or acceptance."""
    issues = []
    def issue(path, reason): issues.append({'path': path, 'reason': reason})
    def records(key):
        rows = response.get(key)
        if not isinstance(rows, list) or not all(isinstance(r, dict) for r in rows):
            issue(key, 'Missing or malformed record list'); return []
        return rows
    dispositions = records('card_dispositions')
    expected = Counter(context.get('primary_card_ids', []))
    actual = Counter(r.get('card_id') for r in dispositions)
    if actual != expected: issue('card_dispositions', 'Missing/duplicate/unsupplied primary Concern IDs')
    transfers = records('writing_transfers')
    expected_e = {r['id'] for r in context.get('expression_sources', {}).get('records', [])}
    actual_e = {r.get('source_id') for r in transfers if r.get('source_kind') == 'mentor_expression'}
    if actual_e != expected_e: issue('writing_transfers', 'Missing/unsupplied Expressions: ' +
                                    ', '.join(sorted((expected_e ^ actual_e) - {None})))
    checks = {r.get('id'): r for r in records('checks')}
    findings = {r.get('id') for r in records('findings')}
    suggestions = {r.get('id') for r in response.get('organization_suggestions', []) if isinstance(r, dict)}
    for i, row in enumerate(transfers):
        prefix = f'writing_transfers[{i}]'
        if 'assessment' in row:
            import advisor_brief
            try: advisor_brief.validate(row, context)
            except (ValueError, KeyError, TypeError) as error: issue(prefix, str(error))
            continue
        for key in ['learned_distinction','reader_task','current_handling','proposed_action','preserved_dependencies','limits']:
            if context.get('advisor_shared_results') and key=='preserved_dependencies':
                import advisor_results
                if not advisor_results.dependencies_valid(row.get(key)):issue(prefix+'.'+key,'Missing substantive dependencies')
                continue
            if not isinstance(row.get(key), str) or not row[key].strip(): issue(prefix+'.'+key, 'Missing substantive account')
        for key, available in [('check_ids', checks),('finding_ids', findings),('suggestion_ids', suggestions)]:
            values = row.get(key)
            if not isinstance(values, list) or not all(isinstance(v, str) and v in available for v in values):
                issue(prefix+'.'+key, 'Missing/unknown explicit output links')
        if row.get('decision') not in {'not_applicable','unfinished'}:
            if not row.get('target_anchors') or not row.get('check_ids'):
                issue(prefix, 'Applied/KEEP/unknown transfer lacks an anchored actual check')
        if context.get('advisor_role_division') and row.get('source_kind') == 'mentor_expression':
            import advisor_batching
            try: advisor_batching.validate_contributions({**response,'writing_transfers':[row]},context)
            except (ValueError,KeyError,TypeError) as error: issue(prefix+'.expression_contribution',str(error))
    if context.get('advisor_shared_results'):
        import advisor_results
        try: advisor_results.validate_uses(response,context)
        except (ValueError,KeyError,TypeError) as error: issue('source_use_dispositions',str(error))
        return {'scope':'Explicit source decisions, unresolved states and unassessed association manifest', 'issues':issues,'judgments_generated':0,'model_calls':0}
    uses = records('source_use_dispositions')
    expected_uses = Counter((r['expression_id'],r['target_kind'],r['target_id']) for r in context.get('source_uses',[]))
    actual_uses = Counter((r.get('expression_id'),r.get('target_kind'),r.get('target_id')) for r in uses)
    if actual_uses != expected_uses: issue('source_use_dispositions','Missing/duplicate/unsupplied active uses')
    transfer_ids = {r.get('id'):r for r in transfers}
    for i,row in enumerate(uses):
        links=row.get('transfer_ids'); prefix=f'source_use_dispositions[{i}]'
        if row.get('status') not in {'checked','unfinished'}: issue(prefix+'.status','Missing explicit use judgment')
        if not isinstance(links,list) or not all(isinstance(v,str) and v in transfer_ids and
                transfer_ids[v].get('source_id')==row.get('expression_id') for v in links):
            issue(prefix+'.transfer_ids','Missing/invalid transfer links')
        elif row.get('status')=='checked' and (not links or any(transfer_ids[v].get('decision')=='unfinished' for v in links)):
            issue(prefix,'Claimed checked use lacks a completed transfer')
        if not (isinstance(row.get('reason'),str) and row['reason'].strip()) and not (
                isinstance(links,list) and row.get('reason_ref') in links):
            issue(prefix+'.reason','Missing use-specific reason/reference')
    return {'scope':'Local deficiency inventory only; all ordinary validators and actual semantic review still required',
            'issues':issues,'judgments_generated':0,'model_calls':0}
