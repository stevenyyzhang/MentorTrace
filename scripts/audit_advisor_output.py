"""Replay saved accepted Advisor results offline, without rewriting the old run."""
import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from unittest.mock import patch

import advisor_batching as batching
import advisor_capacity as capacity
import advisor_output as output
import mentortrace_v1 as m


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode('utf-8')).hexdigest()


def audit(saved_run, out):
    saved_run = Path(saved_run).resolve(); out = Path(out).resolve()
    m.require(not out.exists(), 'Use a new offline replay directory')
    m.require(not out.is_relative_to(saved_run), 'Do not write replay data inside the historical run')
    out.mkdir(parents=True)
    paths = [saved_run/'inputs/protocol.json', saved_run/'inputs/advisor_plan.json',
             saved_run/'inputs/expression/records.json']
    fingerprints = {p: m.sha(p) for p in paths}
    protocol = m.read(paths[0]); plan = m.read(paths[1]); rows = []
    cards, expressions, uses = [], [], []
    for group in plan['groups']:
        stage = group['stage']; original_path = saved_run/f'calls/{stage}/response.json'
        context_path = saved_run/f'inputs/advisor_packets/{stage}.json'
        paths.extend([original_path, context_path])
        fingerprints.update({p:m.sha(p) for p in [original_path,context_path]})
        original = m.read(original_path); context = batching.inflate(m.read(context_path))
        context['advisor_output_contract'] = output.VERSION
        wire = output.encode(original, context); restored = output.expand(wire, context)
        m.require(restored == original, 'Replay changed actual source/target judgments')
        # Accepted independent results already contain the documented relation->object adapter.
        validation_context = {**context, 'objects': []} if 'new_objects' in restored else context
        m.validate(stage, restored, validation_context)
        m.require(batching.inflate(batching.project(context)) == context, 'Input projection changed manuscript/source content')
        before = capacity.estimate(output.dump(original), 0, context['advisor_batching'])
        after = capacity.estimate(output.dump(wire), 0, context['advisor_batching'])
        cids = [d['card_id'] for d in restored['card_dispositions']]
        eids = {t['source_id'] for t in restored['writing_transfers'] if t['source_kind'] == 'mentor_expression'}
        expected = {r['id'] for r in context['expression_sources']['records']}
        m.require(Counter(cids) == Counter(context['primary_card_ids']) and eids == expected, 'Source coverage changed')
        edges = [(u['expression_id'], u['target_kind'], u['target_id']) for u in restored['source_use_dispositions']]
        expected_edges = [(u['expression_id'], u['target_kind'], u['target_id']) for u in context['source_uses']]
        m.require(Counter(edges) == Counter(expected_edges), 'Use coverage changed')
        cards += cids; expressions += sorted(eids); uses += edges
        item = dict(stage=stage, concerns=len(cids), expressions=len(eids), uses=len(edges),
                    before_bytes=before['utf8_bytes'], after_bytes=after['utf8_bytes'],
                    before_reference_tokens=before['reference_text_tokens'],
                    after_reference_tokens=after['reference_text_tokens'],
                    bytes_reduced_percent=round(100*(1-after['utf8_bytes']/before['utf8_bytes']),2),
                    tokens_reduced_percent=round(100*(1-after['reference_text_tokens']/before['reference_text_tokens']),2),
                    canonical_sha256=digest(original), restored_sha256=digest(restored),
                    all_fields_identical=True, original_validators_passed=True)
        rows.append(item)
        m.save(out/f'{stage}/native_output.json', wire)
        m.save(out/f'{stage}/restored_response.json', restored)
        m.save(out/f'{stage}/receipt.json', item)
    m.require(len(cards) == len(set(cards)) and len(expressions) == len(set(expressions)) and
              len(uses) == len(set(uses)), 'Replay source ownership duplicated')
    library = m.read(saved_run/'inputs/expression/records.json')
    unlinked = {r['id'] for r in library if not r['concern_ids']}
    m.require(unlinked <= set(expressions), 'Unlinked Expression omitted')
    summary = dict(scope='Offline exact transcoding of accepted results, including previously integrated supplemental work; not original paid output tokens.',
        model_calls=0, new_review=False, semantic_reassessment=False,
        coverage=dict(concerns=len(cards),expressions=len(expressions),active_uses=len(uses),originally_unlinked_expressions=len(unlinked)),
        output_contract_version=output.VERSION, saved_protocol_unchanged=True,
        capacity_policy=protocol['advisor_capacity'], capacity_allowances_changed=False,
        every_field_round_trips=True, every_original_validator_passed=True,
        sizes={key:sum(r[key] for r in rows) for key in
               ['before_bytes','after_bytes','before_reference_tokens','after_reference_tokens']}, batches=rows)
    size = summary['sizes']
    summary['bytes_reduced_percent'] = round(100*(1-size['after_bytes']/size['before_bytes']),2)
    summary['reference_tokens_reduced_percent'] = round(100*(1-size['after_reference_tokens']/size['before_reference_tokens']),2)
    # Retain the observed distinction between schema repairs and substantive new inspections.
    events = saved_run.parent/'timeline.jsonl'
    schema_fields = 0
    if events.is_file():
        paths.append(events)
        fingerprints[events] = m.sha(events)
        for line in events.read_text(encoding='utf-8').splitlines():
            event = json.loads(line)
            if event.get('kind') == 'schema_empty_output_lists_restored': schema_fields += event['fields']
    summary['repair_limits'] = dict(recorded_schema_empty_lists=schema_fields,
        schema_repair_was_already_local=True, historically_paid_calls_proven_avoidable=0,
        projected_reduction_only='Exact locations and references prevent copy/link bookkeeping defects when used correctly; no claim that correct location choice or missing semantic checks are automatically repaired.',
        still_requires_real_judgment=['missing Expression inspections','missing anchored KEEP comparisons',
                                    'incorrect target/page/paragraph interpretations','conditional/uncertain use reasoning'],
        network_retry_or_latency_reduction_measured=False)
    m.require(all(m.sha(p) == h for p,h in fingerprints.items()), 'Historical replay inputs changed')
    m.save(out/'source_files.json',[dict(path=str(p.relative_to(saved_run)) if p.is_relative_to(saved_run) else p.name,
                                      sha256=m.sha(p)) for p in paths])
    m.save(out/'summary.json',summary)
    with (out/'per-batch.csv').open('w',encoding='utf-8-sig',newline='') as file:
        writer=csv.DictWriter(file,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    return summary


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--saved-run',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True);args=parser.parse_args()
    # A missing cached tokenizer must fail offline; never download or start a child CLI.
    with patch('socket.socket',side_effect=RuntimeError('Offline audit: network disabled')), \
         patch('subprocess.Popen',side_effect=RuntimeError('Offline audit: subprocess disabled')):
        result=audit(args.saved_run,args.out)
    print(json.dumps({k:v for k,v in result.items() if k!='batches'},ensure_ascii=False))


if __name__=='__main__':main()
