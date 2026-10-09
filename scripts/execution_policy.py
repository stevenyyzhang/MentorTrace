"""Validate recorded explicit user settings; never infer permission from prose."""
import hashlib
import json


def validate_authorization(record, model, effort, service_tier='default'):
    if service_tier not in {'default', 'fast', 'priority'}:
        raise ValueError('Unsupported service tier')
    if not all(isinstance(value, str) and value.strip() for value in (model, effort)):
        raise ValueError('Explicit model and reasoning effort are required')
    if not isinstance(record, dict) or record.get('authorized_by') != 'user':
        raise ValueError('Explicit user settings authorization is required')
    if not isinstance(record.get('user_statement'), str) or not record['user_statement'].strip():
        raise ValueError('Record the exact explicit human settings instruction')
    for key, value in [('model', model), ('reasoning_effort', effort), ('service_tier', service_tier)]:
        if record.get(key) != value:
            raise ValueError('User authorization does not match requested ' + key)
    if service_tier != 'default' and record.get('accepts_additional_usage') is not True:
        raise ValueError('Fast/priority requires explicit acceptance of additional usage')
    # Structured declarations document an actual human instruction. This is
    # not a keyword classifier, an identity check, or permission to invent one.
    return hashlib.sha256(json.dumps(record, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':')).encode('utf-8')).hexdigest()
