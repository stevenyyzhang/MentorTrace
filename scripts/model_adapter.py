"""One-stage OpenAI Responses adapter. Live execution is explicitly disabled by default."""
import argparse
import base64
import json
import os
from pathlib import Path
from urllib import error, request
import mentortrace_v1 as m

def post(path, payload):
    key = os.environ.get('OPENAI_API_KEY')
    m.require(bool(key), 'OPENAI_API_KEY is not set')
    req = request.Request('https://api.openai.com/v1' + path,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
    with request.urlopen(req, timeout=60) as response:
        return json.load(response)

def make_payload(run, req, settings):
    m.require(isinstance(settings.get('model'), str) and settings['model'], 'Set an explicit model')
    m.require(isinstance(settings.get('max_output_tokens'), int) and settings['max_output_tokens'] > 0, 'Set output budget')
    m.require(isinstance(settings.get('context_window'), int) and settings['context_window'] > settings['max_output_tokens'], 'Set verified model context limit')
    content = [{'type': 'input_text', 'text': req['prompt']}]
    for image in req['images']:
        p = m.safe_path(run, image['path'])
        m.require(m.sha(p) == image['sha256'], 'Image hash changed')
        content.append({'type': 'input_image', 'image_url': 'data:image/png;base64,' + base64.b64encode(p.read_bytes()).decode(), 'detail': 'high'})
    return {**({'reasoning': {'effort': settings['reasoning_effort']}} if settings.get('reasoning_effort') else {}), 'model': settings['model'], 'input': [{'role': 'user', 'content': content}],
            'tools': [], 'tool_choice': 'none', 'store': False, 'truncation': 'disabled',
            'max_output_tokens': settings['max_output_tokens'], 'text': {'format': {'type': 'json_object'}}}

def run_one(run, settings, *, project, sender=post):
    m.require(project.get('model_calls_enabled') is True and settings.get('enabled') is True,
              'Live model calls are disabled; no request was sent')
    run = Path(run).resolve()
    m.require(str(run) not in [str(Path(p).resolve()) for p in project.get('paused_run_paths', [])], 'This run is paused')
    req = m.next_request(run)
    m.require(req is not None, 'Run complete')
    folder = run / 'calls' / req['stage']
    m.require(not (folder / 'provider_started.json').exists(), 'Previous provider attempt exists; inspect before retry')
    m.require(not (folder / 'raw_response.json').exists(), 'Response exists; use explicit failed-attempt retry')
    payload = make_payload(run, req, settings)
    pinned = run / 'provider_settings.json'
    if pinned.exists():
        m.require(m.read(pinned) == settings, 'Provider settings changed during run')
    else:
        m.save(pinned, settings)
    m.save(folder / 'provider_payload.json', payload)
    m.save(folder / 'provider_started.json', {'request_sha256': m.sha(folder / 'request.json'), 'status': 'started'})
    try:
        count_payload = {k: payload[k] for k in ['model', 'input', 'tools', 'tool_choice', 'text']}
        count = sender('/responses/input_tokens', count_payload)
        m.save(folder / 'preflight.json', count)
        m.require(isinstance(count.get('input_tokens'), int) and count['input_tokens'] >= 0, 'Invalid token count')
        m.require(count['input_tokens'] + settings['max_output_tokens'] + settings.get('safety_margin_tokens', 1024) <= settings['context_window'], 'Context budget exceeded; no generation sent')
        response = sender('/responses', payload)
        m.save(folder / 'provider_response.json', response)
        m.require(response.get('status') == 'completed', 'Provider response incomplete or failed')
        blocks = [b for item in response.get('output', []) if item.get('type') == 'message' for b in item.get('content', [])]
        m.require(not any(b.get('type') == 'refusal' for b in blocks), 'Provider refused')
        text = ''.join(b['text'] for b in blocks if b.get('type') == 'output_text')
        m.require(bool(text.strip()), 'Provider returned no text')
        raw = folder / 'provider_text.json'
        raw.write_text(text, encoding='utf-8')
        m.accept_response(run, raw, {'kind': 'openai_responses', 'model': response.get('model', settings['model']),
            'response_id': response.get('id'), 'usage': response.get('usage'), 'input_tokens_preflight': count['input_tokens'],
            'fresh_context': True, 'tools': [], 'request_sha256': m.sha(folder / 'provider_payload.json')})
    except (ValueError, KeyError, error.HTTPError) as exc:
        m.save(folder / 'rejected.json', {'error': str(exc), 'type': type(exc).__name__})
        raise
    except Exception as exc:
        m.save(folder / 'provider_uncertain.json', {'type': type(exc).__name__, 'automatic_retry': False})
        raise
    return {'stage': req['stage'], 'accepted': True}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--settings', type=Path, default=m.ROOT / 'config/provider.json')
    args = parser.parse_args()
    print(m.dump(run_one(args.run, m.read(args.settings), project=m.read(m.ROOT / 'config/project.json'))))

if __name__ == '__main__':
    main()
