"""Validate a post-freeze historical comparison without changing the source run.

Judgments are supplied by a reviewer. This program verifies provenance and links,
not whether an omission or rejection is scientifically correct. It invokes no model.
"""
import argparse
from pathlib import Path
import audit_merge_obligations as audit
import mentortrace_v1 as m

STATES={'covered','rejected_with_evidence','confirmed_omission','unresolved'}

def prepare(run, historical_report, out):
    run=Path(run).resolve(); historical_report=Path(historical_report).resolve()
    m.require(m.read(run/'state.json')['status']=='complete', 'Independent diagnosis must finish first')
    m.require((run/'RESULT_FREEZE.json').is_file(), 'Independent result freeze required')
    snapshot=audit.load_run(run)
    packet={'schema':'mentortrace.history-comparison.v1', 'run':str(run),
        'result_freeze_sha256':m.sha(run/'RESULT_FREEZE.json'),
        'final_sha256':m.sha(run/'final.json'),
        'historical_report':str(historical_report),'historical_sha256':m.sha(historical_report),
        'final_targets':snapshot['final_targets'],'manuscript':snapshot['manuscript'],
        'instructions':'Read the historical report only after this independent-result freeze. '
        'Return rows with id, historical_excerpt, disposition, final_ids, reason, evidence. '
        'Account for independently answerable historical requirements and declare coverage limits. '
        'Confirmed omissions are post-comparison discoveries; do not edit or relabel the initial run.'}
    audit.save_new(out,packet)
    return packet

def validate(packet, review):
    run=Path(packet['run'])
    m.require(m.sha(run/'RESULT_FREEZE.json')==packet['result_freeze_sha256'] and
              m.sha(run/'final.json')==packet['final_sha256'], 'Independent result changed')
    report=Path(packet['historical_report'])
    m.require(m.sha(report)==packet['historical_sha256'],'Historical source changed')
    source=report.read_text(encoding='utf-8-sig')
    pages={p['page']:p['text'] for p in packet['manuscript']}
    m.require(review.get('discovery_origin')=='post_freeze_historical_comparison', 'Discovery provenance missing')
    m.require(isinstance(review.get('coverage_limits'),list), 'Historical comparison coverage limits missing')
    rows=review.get('rows');audit.rows_by_id(rows,'Historical requirement rows')
    for row in rows:
        m.require(row.get('historical_excerpt') and row['historical_excerpt'] in source,'Historical excerpt absent')
        m.require(row.get('disposition') in STATES and isinstance(row.get('reason'),str) and row['reason'].strip(), 'Historical judgment incomplete')
        targets=row.get('final_ids')
        m.require(isinstance(targets,list) and len(targets)==len(set(targets)) and
                  set(targets)<=set(packet['final_targets']), 'Historical target invalid')
        m.require(bool(targets)==(row['disposition']=='covered'), 'Historical disposition/target mismatch')
        evidence=row.get('evidence')
        m.require(isinstance(evidence,list) and (evidence or row['disposition']=='unresolved'), 'Historical evidence missing')
        for item in evidence:m.anchor(item,pages)
    return {'valid_records':True,'semantic_correctness_verified':False,
            'initial_result_modified':False,'rows':len(rows),
            'confirmed_omissions':[r['id'] for r in rows if r['disposition']=='confirmed_omission']}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('prepare');a.add_argument('--run',required=True);a.add_argument('--historical-report',required=True);a.add_argument('--out',required=True)
    a=sub.add_parser('validate');a.add_argument('--packet',required=True);a.add_argument('--review',required=True)
    args=p.parse_args()
    if args.command=='prepare':prepare(args.run,args.historical_report,args.out)
    else:print(m.dump(validate(m.read(args.packet),m.read(args.review))))
