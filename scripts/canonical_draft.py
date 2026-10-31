"""One authored group record; derive legacy delivery views without new judgments."""
import copy
import hashlib
import json

FIELDS = ('delivery_map', 'revision_actions', 'draft_checks', 'requirement_delivery', 'candidate_delivery_map')
INSTRUCTIONS = '''CANONICAL DRAFT v1 replaces the top-level delivery metadata lists:
each report_fragments row owns delivery:{delivery_map:[],revision_actions:[],draft_checks:[],
requirement_delivery:[],candidate_delivery_map:[]}. Write each authored action/check once
inside its owning group; programs derive the legacy top-level lists. Do not return those
lists a second time. A coordinated shared replacement has one owner. Each component_id
in requirement_delivery is the existing source_requirement_resolutions ID, not a newly
phrased duplicate requirement. Preserve conditions, alternative paths and optionality.
Replacement passages and actions must agree. Edit a group and its delivery metadata as
one transaction; never append a contradictory action while leaving the old one active.
'''


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def compile(response, partial=False):
    import review_integrity
    result = expand_wire(response)
    version = result.get('canonical_draft', 1)
    fields = fields_for(version)
    groups = result.get('report_fragments', [])
    text, _ = review_integrity.assemble_fragments([result], partial=partial)
    if version==2:
        for group in groups:derive_locations(group)
    values = {k: [] for k in fields}
    for group in groups:
        delivery = group.get('delivery')
        require(isinstance(delivery, dict) and set(delivery) == set(fields), 'Group delivery record incomplete')
        for k in fields:
            require(isinstance(delivery[k], list), 'Group delivery field must be a list')
            values[k].extend(copy.deepcopy(delivery[k]))
        declared = set(group.get('verified_ids', []))
        mapped={r['verified_id'] for r in delivery['delivery_map']}
        actions={i for r in delivery['revision_actions'] for i in r['verified_ids']}
        require(mapped == declared if version==1 else mapped<=declared, 'Group target map differs from ownership')
        require(actions == declared if version==1 else actions<=declared, 'Group action ownership differs')
        for r in delivery['requirement_delivery']:
            quote_groups=r.get('quote_group_ids',[group['group_id']]*len(r.get('report_quotes',[])))
            by_id={g['group_id']:g for g in groups}
            require(r.get('report_quotes') and len(quote_groups)==len(r['report_quotes']) and all(q and gid in by_id and q in by_id[gid]['text'] for q,gid in zip(r['report_quotes'],quote_groups)), 'Requirement quote outside bound group')
        for r in delivery['candidate_delivery_map']:
            require(r.get('report_excerpt') and r['report_excerpt'] in group['text'], 'Candidate quote outside owning group')
    keys = {'delivery_map': 'verified_id', 'revision_actions': 'draft_label', 'draft_checks': 'draft_label',
            'requirement_delivery': 'component_id', 'candidate_delivery_map': 'candidate_id', 'language_realizations':'draft_label', 'revision_attribution':'verified_id'}
    for group in groups:
        if version >= 2:
            validate_related(group)
    for k in fields:
        ids = [r[keys[k]] for r in values[k]]
        require(len(ids) == len(set(ids)), 'Conflicting/duplicate canonical delivery item: ' + k)
        if k in result:
            require(result[k] == values[k], 'Stale derived delivery metadata: ' + k)
        result[k] = values[k]
    if 'report_markdown' in result:
        require(result['report_markdown'] == text, 'Stale derived report text')
    result['report_markdown'] = text
    result['canonical_draft'] = version
    result['canonical_groups_sha256'] = digest(groups)
    return result


def validate(response):
    if not response.get('canonical_draft'):
        return
    require(response.get('canonical_groups_sha256') == digest(response['report_fragments']), 'Canonical groups changed without rebuilding derived views')
    compile(response)


def replace_groups(response, replacements, expected_sha256):
    """All-or-nothing in memory; caller saves to a NEW path and renews affected review."""
    validate(response)
    require(digest(response) == expected_sha256, 'Draft transaction base changed')
    ids = [r['group_id'] for r in replacements]
    require(len(ids) == len(set(ids)), 'Duplicate replacement group')
    known = {g['group_id'] for g in response['report_fragments']}
    require(set(ids) <= known, 'Replacement group absent')
    by_id = {g['group_id']: g for g in replacements}
    result = copy.deepcopy(response)
    result['report_fragments'] = [copy.deepcopy(by_id.get(g['group_id'], g)) for g in response['report_fragments']]
    for k in (*fields_for(response.get('canonical_draft',1)), 'report_markdown', 'canonical_groups_sha256'):
        result.pop(k, None)
    result = compile(result)
    require(inventory(response) == inventory(result), 'Group transaction lost or moved an opinion/requirement/attribution')
    import review_integrity
    def originals(text):
        return [text[start.end():end.start() if end else len(text)]
                for start, end in review_integrity._original_ranges(text)]
    require(originals(response['report_markdown']) == originals(result['report_markdown']),
            'Group transaction changed an Original field; use a separately evidenced source-quotation repair')
    result['draft_transaction'] = {'base_sha256': expected_sha256, 'changed_group_ids': ids,
                                  'semantic_review_renewal_required': True, 'new_model_calls': 0}
    return result



FIELDS_V2 = FIELDS + ('language_realizations', 'revision_attribution')
INSTRUCTIONS_V2 = INSTRUCTIONS.replace('v1','v2').replace('candidate_delivery_map:[]}',
    'candidate_delivery_map:[],language_realizations:[],revision_attribution:[]}') + """
Set canonical_draft=2. These seven lists belong only inside their group. The program
assembles report_markdown and the seven top-level views; never output them twice.
Optional local text_units:{name:exact_text} lets group.text use [[TEXT:name]] and
any delivery string use {"$text":"name"}. Definitions are literal and nonrecursive;
use this only for exact repeated prose/excerpts, never merge independent judgments.
delivery_map rows may omit report_section (derived from owning group). For a single
numbered comment heading display_number is derived too; otherwise supply comment_ref
as its exact heading, or the assigned display_number. Conflicting fields fail locally.
Each revision_actions row adds action_bindings, one per actions index (zero based):
{action_index,applies_when:"always|actual condition stated in report",requirement_ids:[],
new_assertions:[{claim,source_support:[]}]}. An independent edit keeps its own
condition; sharing a paragraph does not inherit another action's author uncertainty.
List changed assertions with their actual source basis, without inventing author facts.
All independent requirements retain their own disposition and exact report binding.
For a requirement spanning groups, quote_group_ids parallels report_quotes and names
the exact owning group of each quote; its record has one owner and all groups are dependencies.
"""


def fields_for(version):
    require(version in (1, 2), 'Unsupported canonical draft version')
    return FIELDS_V2 if version == 2 else FIELDS


def expand_wire(response):
    import re
    result=copy.deepcopy(response)
    for group in result.get('report_fragments',[]):
        units=group.pop('text_units',{})
        require(isinstance(units,dict) and all(isinstance(v,str) and v and '[[TEXT:' not in v for v in units.values()), 'Invalid literal text units')
        def expand(v):
            if isinstance(v,dict) and set(v)=={'$text'}:
                require(v['$text'] in units, 'Unknown text unit')
                return units[v['$text']]
            if isinstance(v,dict):return {k:expand(x) for k,x in v.items()}
            if isinstance(v,list):return [expand(x) for x in v]
            if isinstance(v,str):
                def lookup(match):
                    require(match[1] in units,'Unknown text unit')
                    return units[match[1]]
                return re.sub(r'\[\[TEXT:([^]]+)\]\]',lookup,v)
            return v
        value=expand(group);group.clear();group.update(value)
    return result


def derive_locations(group):
    import re
    headings=re.findall(r'^#{3,4}\s+(\d+)\.[^\n]*',group['text'],re.M)
    for row in group['delivery']['delivery_map']:
        from review_integrity import normalize_section
        section=normalize_section(row.get('report_section',group['section']))
        require(section==group['section'],'Map section differs from owning group')
        row['report_section']=section
        ref=row.get('comment_ref')
        if ref:
            require(ref in group['text'],'Comment reference outside group')
            match=re.fullmatch(r'#{3,4}\s+(\d+)\.[^\n]*',ref)
            require(match,'Comment reference must be the exact numbered heading')
            number=int(match[1])
            require('display_number' not in row or row['display_number']==number,'Stale display number')
            row['display_number']=number
        elif 'display_number' not in row and len(headings)==1:row['display_number']=int(headings[0])
        # Some historical synthetic records are unnumbered. Real delivery preparation
        # already requires a resolvable display map; never invent its number here.


def validate_related(group):
    d=group['delivery'];labels={r['draft_label'] for r in d['revision_actions']}
    require({r['draft_label'] for r in d['draft_checks']}==labels, 'Group check ownership differs')
    require({r['draft_label'] for r in d['language_realizations']}==labels, 'Group realization ownership differs')
    require({r['verified_id'] for r in d['revision_attribution']}<=set(group['verified_ids']), 'Group attribution ownership differs')
    for row in d['revision_attribution']:
        require(row.get('report_excerpt') and row['report_excerpt'] in group['text'], 'Stale attribution excerpt')
    for row in d['language_realizations']:
        require(set(row['verified_ids'])<=set(group['verified_ids']), 'Foreign realization owner')
        for passage in row.get('passages',[]):
            require(passage.get('text') and passage['text'] in group['text'], 'Stale realized passage')
        for decision in row.get('feature_decisions',[]):
            quote=decision.get('target_quote')
            require(not quote or quote in group['text'], 'Stale feature target quote')


def validate_action_bindings(group):
    components={r['component_id'] for r in group['delivery']['requirement_delivery']}
    for row in group['delivery']['revision_actions']:
        bindings=row.get('action_bindings',[])
        require(sorted(b.get('action_index',-1) for b in bindings)==list(range(len(row['actions']))), 'Action conditions incomplete')
        for b in bindings:
            require(isinstance(b.get('applies_when'),str) and b['applies_when'].strip(), 'Action condition missing')
            require(isinstance(b.get('requirement_ids'),list) and set(b['requirement_ids'])<=components, 'Action requirement binding invalid')
            require(isinstance(b.get('new_assertions'),list), 'Changed assertion inventory missing')
            for claim in b['new_assertions']:
                require(claim.get('claim') and claim.get('source_support'), 'Changed assertion lacks evidence')


def inventory(response):
    keys={'delivery_map':'verified_id','revision_actions':'draft_label','draft_checks':'draft_label',
          'requirement_delivery':'component_id','candidate_delivery_map':'candidate_id',
          'language_realizations':'draft_label','revision_attribution':'verified_id'}
    return {g['group_id']:{'items':{k:sorted(r[keys[k]] for r in g['delivery'][k]) for k in fields_for(response.get('canonical_draft',1))},
            'verified_ids':sorted(g['verified_ids']),'candidate_ids':sorted(g.get('candidate_ids',[])),
            'action_owners':{r['draft_label']:sorted(r['verified_ids']) for r in g['delivery']['revision_actions']}}
            for g in response['report_fragments']}


def adopt(response):
    """Lossless legacy import; no inferred conditions or new semantic verdicts."""
    result=copy.deepcopy(response)
    groups=result['report_fragments']
    for g in groups:g['delivery']={k:[] for k in FIELDS_V2}
    owners={}
    for field in ('revision_actions','language_realizations','draft_checks','delivery_map','revision_attribution','requirement_delivery','candidate_delivery_map'):
        for row in result.get(field,[]):
            vids=set(row.get('verified_ids',[]))|({row['verified_id']} if 'verified_id' in row else set())
            label=row.get('draft_label')
            if label in owners:candidates=[g for g in groups if g['group_id']==owners[label]]
            else:candidates=[g for g in groups if label and g['group_id']==label]
            if not candidates and field in {'requirement_delivery','revision_attribution','candidate_delivery_map'}:
                quotes=row.get('report_quotes') or [row.get('report_excerpt')]
                candidates=[g for g in groups if all(q and q in g['text'] for q in quotes)]
            if not candidates and field=='requirement_delivery':
                quote_groups=[]
                for quote in row['report_quotes']:
                    matches=[g['group_id'] for g in groups if quote in g['text']]
                    require(len(matches)==1,'Ambiguous cross-group requirement quote')
                    quote_groups.append(matches[0])
                row={**row,'quote_group_ids':quote_groups}
                candidates=[g for g in groups if g['group_id']==quote_groups[0]]
            if not candidates:
                candidates=[g for g in groups if vids and vids<=set(g['verified_ids'])]
            if len(candidates)>1 and field!='delivery_map' and vids:
                candidates=[g for g in candidates if vids<=set(g['verified_ids'])]
            if len(candidates)>1 and field=='delivery_map':
                candidates=[g for g in candidates if g['section']==row.get('report_section')]
            require(len(candidates)==1,'Ambiguous legacy ownership: '+field)
            chosen=candidates[0]
            chosen['verified_ids']=list(dict.fromkeys(chosen['verified_ids']+sorted(vids)))
            chosen['delivery'][field].append(copy.deepcopy(row))
            if label:owners[label]=chosen['group_id']
    result['canonical_draft']=2
    # Legacy order is retained in each group; exported views use document ownership order.
    for field in FIELDS_V2:result.pop(field,None)
    result.pop('canonical_groups_sha256',None)
    return compile(result)


def compact_wire(response):
    """Exact inverse representation; measurements are offline output estimates only."""
    validate(response)
    result=copy.deepcopy(response)
    for field in (*fields_for(response['canonical_draft']),'report_markdown','canonical_groups_sha256'):
        result.pop(field,None)
    def strings(v):
        if isinstance(v,str):yield v
        elif isinstance(v,list):
            for x in v:yield from strings(x)
        elif isinstance(v,dict):
            for x in v.values():yield from strings(x)
    for group in result['report_fragments']:
        candidates=sorted({v for v in strings(group['delivery']) if len(v)>=80 and v in group['text']},key=len,reverse=True)
        units={};reverse={}
        for value in candidates:
            if value not in group['text']:continue
            key='t'+str(len(units)+1);units[key]=value;reverse[value]=key
            group['text']=group['text'].replace(value,'[[TEXT:'+key+']]')
        def pack(v):
            if isinstance(v,str) and v in reverse:return {'$text':reverse[v]}
            if isinstance(v,dict):return {k:pack(x) for k,x in v.items()}
            if isinstance(v,list):return [pack(x) for x in v]
            return v
        group['delivery']=pack(group['delivery'])
        if units:group['text_units']=units
    return result


if __name__ == '__main__':
    import argparse
    from pathlib import Path
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--response', type=Path, required=True)
    parser.add_argument('--replacements', type=Path, required=True)
    parser.add_argument('--expected-sha256', required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    value = replace_groups(json.loads(args.response.read_text(encoding='utf-8-sig')),
                           json.loads(args.replacements.read_text(encoding='utf-8-sig')), args.expected_sha256)
    with args.out.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
