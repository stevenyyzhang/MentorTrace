"""Read Codex model metadata and budget complete requests; no model generation."""
import hashlib
import json
import math
import shutil
import subprocess
from functools import lru_cache


def require(ok, message):
    if not ok:
        raise ValueError(message)


def discover(model, effort):
    binary = shutil.which('codex')
    require(binary, 'Codex CLI unavailable; cannot automatically detect capacity')
    result = subprocess.run([binary, 'debug', 'models', '-c', 'model_provider="openai"'],
                            capture_output=True, text=True, encoding='utf-8', timeout=60)
    require(result.returncode == 0, 'Model catalog detection failed; update/login to Codex. No guessed capacity or model call.')
    catalog = json.loads(result.stdout)
    matches = [r for r in catalog.get('models', []) if r.get('slug') == model]
    require(len(matches) == 1, 'Selected model absent/ambiguous in Codex catalog')
    item = matches[0]
    require(effort in {r['effort'] for r in item.get('supported_reasoning_levels', [])},
            'Selected effort unavailable; never substitute model or effort')
    window, percent = item.get('context_window'), item.get('effective_context_window_percent')
    require(type(window) is int and window > 0 and type(percent) is int and 0 < percent <= 100,
            'Catalog lacks usable capacity; no guessed fallback')
    effective = window * percent // 100
    encodings = tokenizer()
    return dict(version=3, model=model, effort=effort, context_window=window,
                effective_context=effective, effective_percent=percent,
                output_reserve=64000, image_reserve_each=6000,
                system_reserve=8000, text_multiplier=1.10,
                max_prompt_chars=1048576,
                character_limit_source='Codex turn/start input_too_large response observed 2026-10-27; independent of token capacity',
                token_method='max_cl100k_o200k' if encodings else 'utf8_upper_bound',
                catalog_sha256=hashlib.sha256(result.stdout.encode()).hexdigest(),
                source='codex debug models (current catalog, not --bundled or max_context_window)',
                server_capacity_verified=False, exact_provider_token_count=False,
                reserve_basis='Planning estimates: 64000 output including reasoning, 6000 per page image, 8000 system and 10% text headroom. Calibrated against saved Sol paper-page trials, not measured provider limits or an output truncation setting.')


@lru_cache(maxsize=1)
def tokenizer():
    try:
        import tiktoken
        return tuple(tiktoken.get_encoding(n) for n in ('cl100k_base', 'o200k_base'))
    except Exception:
        # Tokenizer downloads may fail offline; byte counting preserves a conservative fallback.
        return ()


def estimate(prompt, image_count, policy):
    require(policy['effective_context'] > 0 and policy['output_reserve'] > 0,
            'Invalid capacity policy')
    size = len(prompt.encode('utf-8'))
    if policy['token_method'] == 'max_cl100k_o200k':
        encodings = tokenizer()
        require(encodings, 'Pinned tokenizer unavailable; do not change a frozen capacity plan')
        text = max(len(e.encode(prompt, disallowed_special=())) for e in encodings)
    else:
        require(policy['token_method'] == 'utf8_upper_bound', 'Unknown token estimate method')
        text = size
    total = (math.ceil(text * policy['text_multiplier']) + image_count * policy['image_reserve_each']
             + policy['system_reserve'] + policy['output_reserve'])
    chars = len(prompt.encode('utf-16-le')) // 2
    char_limit = policy.get('max_prompt_chars')
    require(char_limit is None or (type(char_limit) is int and char_limit > 0), 'Invalid transport character limit')
    char_fits = char_limit is None or chars <= char_limit
    return dict(utf8_bytes=size, reference_text_tokens=text, total_reserved=total,
                prompt_chars=chars, transport_character_fit=char_fits,
                effective_context=policy['effective_context'], fits=total <= policy['effective_context'] and char_fits,
                exact_provider_token_count=False, policy=policy)


def check_capacity(prompt, image_count, policy):
    result = estimate(prompt, image_count, policy)
    require(result['transport_character_fit'], 'Complete request exceeds Codex transport character limit; replan, never truncate')
    require(result['fits'], 'Complete request exceeds detected capacity budget; replan, never truncate')
    return result
