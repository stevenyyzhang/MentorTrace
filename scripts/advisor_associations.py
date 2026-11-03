"""Project explicit uses of already-confirmed target links into bookkeeping records.

Concern target links are authoritative and immutable during projection. A source
pair and an Expression's assertion cannot create a missing Concern target link.
Structural consistency is not evidence of semantic validity. Raw output stays raw.
"""
import copy


class AssociationConflict(ValueError):
    """Recoverable semantic disagreement, with both original declarations intact."""
    def __init__(self, raw, issues):
        self.raw = copy.deepcopy(raw)
        self.issues = copy.deepcopy(issues)
        super().__init__('; '.join('Unconfirmed Concern target link: '+i['concern_id']+' lacks '+
            ', '.join(i['analysis_ids']) if i['kind']=='missing_target' else
            'Target support conflicts with the independent Concern decision: '+i['id'] for i in issues))


def conflicts(raw, context):
    """Collect only resolvable target disagreements; malformed source IDs still fail."""
    concerns = {cid: row for row in raw['concern_results'] for cid in row['source_ids']}
    exceptions={r.get('use_id') for r in raw.get('association_exceptions',[]) if r.get('status') in {'conflict','uncertain'}}
    issues = []
    for group in raw['expression_results']:
        for index, row in enumerate(group.get('actions', [group])):
            if row.get('decision') not in {'required_repair','optional_improvement'}:
                continue
            for ref in row.get('supporting_associations', []):
                ident=ref.get('use_id');uses=context['source_uses']
                if type(ident) is not int or not 1 <= ident <= len(uses):continue
                use=uses[ident-1]
                if len(group['source_ids'])!=1 or use['expression_id']!=group['source_ids'][0] or use['target_kind']!='concern':continue
                concern=concerns.get(use['target_id'])
                if concern is None or concern['state']!='linked' or not set(row['analysis_ids'])<=set(concern['analysis_ids']) or ident in exceptions:
                    issues.append({'id':group['source_ids'][0]+':'+str(index)+':'+str(ident),
                        'expression_id':group['source_ids'][0],'action_index':index,'use_id':ident,
                        'concern_id':use['target_id'],'analysis_ids':list(row['analysis_ids']),
                        'kind':'explicit_conflict' if ident in exceptions else 'missing_target' if concern and concern['state']=='linked' else 'conflicting_or_absent_concern'})
    return issues

INSTRUCTIONS = '''TARGET ASSOCIATIONS v2:
The supplied source_uses already defines Expression–Concern library relationships.
Do not recreate those pairs or audit their historical admission. Their applicability to
this manuscript still needs your judgment; a library link is not a target defect.
On each actionable Expression replace supporting_concern_ids with supporting_associations:
[{use_id,reason}]. use_id is the EXACT 1-based index in supplied source_uses; it must bind
this Expression to a supplied Concern. reason states why that Concern supports this action
on the row's analysis_ids under its actual conditions. Empty [] is valid for an independent
Expression operation. A missing library pair must not be invented to force support.
Do not return adopted_uses for v2; the adapter derives it from these explicit target uses.
Concern results own the explicit current-manuscript applicability judgment and analysis_ids.
The Expression action may reference only analyses ALREADY linked by that Concern. The adapter
derives supporting IDs and adopted-use bookkeeping; it NEVER adds Concern analysis_ids,
changes its state, or appends Expression reasons to the Concern's explanation. Omitted target
links are unconfirmed, not automatically clerical omissions. Keep a missing/conflicting link
as an explicit error for scoped evidence-based reassessment; never relabel a judgment just
to pass validation. A sufficient/not_applicable/unknown/unfinished Concern cannot support an
action through this association. An independent Expression operation can use [] only when
that is its actual assessed role, not as a mechanical way to suppress a support conflict.
Preserve source/target conditions and counterevidence in the existing semantic review.
Consistent IDs and nonempty reasons do not certify that a relationship is actually valid.
This projection preserves all analyses and findings; it creates no target judgment.
'''


def project(raw, context):
    if not context.get('advisor_target_links'):
        return raw
    issues=conflicts(raw,context)
    if issues:
        raise AssociationConflict(raw,issues)
    result = copy.deepcopy(raw)
    if result.get('adopted_uses'):
        raise ValueError('v2 adopts associations only through explicit target uses')
    concerns = result['concern_results']
    by_concern = {cid: row for row in concerns for cid in row['source_ids']}
    # Do not hide duplicate source declarations while projecting.
    if len(by_concern) != sum(len(row['source_ids']) for row in concerns):
        raise ValueError('Duplicate Concern source')
    adopted = {}
    for group in result['expression_results']:
        for row in group.get('actions', [group]):
            if row.get('decision') not in {'required_repair', 'optional_improvement'}:
                if row.get('supporting_associations'):
                    raise ValueError('Non-action Expression cannot assert an adopted association')
                continue
            if 'supporting_concern_ids' in row:
                raise ValueError('v2 must not duplicate derived supporting_concern_ids')
            if len(group['source_ids']) != 1 or not row.get('analysis_ids'):
                raise ValueError('Target association requires one Expression and actual analyses')
            refs = row.pop('supporting_associations', None)
            if not isinstance(refs, list):
                raise ValueError('Missing explicit supporting_associations (empty allowed)')
            supporting = []
            seen = set()
            for ref in refs:
                use_id = ref.get('use_id')
                uses = context['source_uses']
                if type(use_id) is not int or not 1 <= use_id <= len(uses) or use_id in seen:
                    raise ValueError('Unknown/duplicate frozen association index')
                seen.add(use_id)
                use = uses[use_id - 1]
                if use['expression_id'] != group['source_ids'][0] or use['target_kind'] != 'concern':
                    raise ValueError('Association does not bind the declared Expression/Concern')
                reason = ref.get('reason')
                if not isinstance(reason, str) or not reason.strip():
                    raise ValueError('Target association needs an explicit applicability reason')
                cid = use['target_id']
                concern = by_concern.get(cid)
                if concern is None or concern['state'] != 'linked':
                    raise ValueError('Target support conflicts with the independent Concern decision')
                missing = set(row['analysis_ids']) - set(concern['analysis_ids'])
                if missing:
                    raise ValueError('Unconfirmed Concern target link: '+cid+' lacks '+
                        ', '.join(sorted(missing))+'; preserve both records for scoped reassessment')
                supporting.append(cid)
                if use_id in adopted:
                    adopted[use_id]['reason'] += '\n' + reason
                else:
                    adopted[use_id] = {'use_id': use_id, 'expression_id': use['expression_id'], 'reason': reason}
            row['supporting_concern_ids'] = sorted(set(supporting))
    result['adopted_uses'] = list(adopted.values())
    return result
