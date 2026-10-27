"""Reversible in-packet references; narrowly separated local administration data."""
import copy
import json
from collections import Counter


def dump(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def separate(context):
    review = copy.deepcopy(context)
    administration = {'advisor_batching': review.pop('advisor_batching', None), 'expression_fields': {}}
    if 'historical_concern_links' in review:
        administration['historical_concern_links'] = review.pop('historical_concern_links')
    historical = {tuple(p) for p in administration.get('historical_concern_links', [])}
    for record in review.get('expression_sources', {}).get('records', []):
        if context.get('advisor_efficiency') == 1:
            import advisor_efficiency
            hidden={k:record.pop(k) for k in advisor_efficiency.LOCAL_FIELDS if k in record}
            administration['expression_fields'].setdefault(record['id'],{}).update(hidden)
        # Publication authorization is an audit field, not evidence of applicability.
        # Content/admission status, provenance, source limits and uncertainty stay visible.
        if 'publication_permission' in record:
            administration['expression_fields'].setdefault(record['id'],{}).update({'publication_permission': record.pop('publication_permission')})
        active = [cid for cid in record.get('concern_ids', []) if (record['id'], cid) not in historical]
        if active != record.get('concern_ids', []):
            administration['expression_fields'].setdefault(record['id'], {})['concern_ids'] = record['concern_ids']
            record['concern_ids'] = active
    review['advisor_batching'] = True
    if context.get('advisor_efficiency') == 1:
        import advisor_efficiency
        review['expression_operation_families']=advisor_efficiency.families(review.get('expression_sources',{}).get('records',[]))
    if context.get('advisor_guidance') == 1:
        import advisor_guidance
        advisor_guidance.separate(review,administration)
    if context.get("advisor_review_view") == 1:
        import advisor_views
        advisor_views.separate(review,administration)
    return review, administration


def restore(review, administration):
    result = copy.deepcopy(review)
    if result.get("advisor_review_view") == 1:
        import advisor_views
        advisor_views.restore(result,administration)
    if result.get('advisor_efficiency') == 1:result.pop('expression_operation_families',None)
    if result.get('advisor_guidance') == 1:
        import advisor_guidance
        advisor_guidance.restore(result,administration)
    result['advisor_batching'] = copy.deepcopy(administration['advisor_batching'])
    if 'historical_concern_links' in administration:
        result['historical_concern_links'] = copy.deepcopy(administration['historical_concern_links'])
    for record in result.get('expression_sources', {}).get('records', []):
        record.update(copy.deepcopy(administration['expression_fields'].get(record['id'], {})))
    return result


def pack(value):
    """Intern repeated long values, including exact subtrees. Definitions are flat."""
    counts = Counter()
    def count(v):
        encoded = dump(v)
        if len(encoded) >= 100:
            counts[encoded] += 1
        if isinstance(v, dict):
            if '$same' in v or '$rows' in v:
                raise ValueError('Reserved wire reference key in original data')
            for item in v.values(): count(item)
        elif isinstance(v, list):
            for item in v: count(item)
    count(value)
    definitions, ids = {}, {}
    def encode(v):
        key = dump(v)
        # Reference overhead + definition overhead must be cheaper than duplication.
        if counts[key] > 1 and (counts[key]-1)*len(key) > counts[key]*28+20:
            if key not in ids:
                ident = 'D'+str(len(ids)+1)
                ids[key] = ident; definitions[ident] = copy.deepcopy(v)
            return {'$same': ids[key]}
        if isinstance(v, dict): return {k: encode(x) for k,x in v.items()}
        if isinstance(v, list):
            if len(v) >= 3 and all(isinstance(x, dict) and set(x) == set(v[0]) for x in v):
                columns = list(v[0])
                table = {'$rows': {'columns': columns, 'values': [[encode(x[k]) for k in columns] for x in v]}}
                plain = [{k: encode(x[k]) for k in x} for x in v]
                return table if len(dump(table)) < len(dump(plain)) else plain
            return [encode(x) for x in v]
        return v
    data = encode(value)
    wire = {'encoding': 'exact_shared_values_v1', 'definitions': definitions, 'data': data}
    if unpack(wire) != value: raise ValueError('Shared-value reconstruction failed')
    return wire if len(dump(wire)) < len(dump(value)) else value


def unpack(wire):
    if wire.get('encoding') != 'exact_shared_values_v1': return copy.deepcopy(wire)
    definitions = wire['definitions']
    def decode(v):
        if isinstance(v, dict):
            if set(v) == {'$same'}: return copy.deepcopy(definitions[v['$same']])
            if set(v) == {'$rows'}:
                table = v['$rows']; columns = table['columns']
                if any(len(row) != len(columns) for row in table['values']):
                    raise ValueError('Invalid table row length')
                return [{k: decode(x) for k,x in zip(columns,row)} for row in table['values']]
            return {k: decode(x) for k,x in v.items()}
        if isinstance(v, list): return [decode(x) for x in v]
        return v
    return decode(wire['data'])


def prepare(context):
    review, admin = separate(context)
    wire = pack(review)
    if restore(unpack(wire), admin) != context:
        raise ValueError('Review/administration reconstruction failed')
    return wire, admin
