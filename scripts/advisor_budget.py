"""Automatic planning budget and atomic logical-request reservations; no model calls."""
import copy
import hashlib
import json
from pathlib import Path


def require(ok, message):
    if not ok: raise ValueError(message)


class PlanningBudgetError(ValueError):
    def __init__(self,message,trials):
        super().__init__(message);self.trials=trials


def candidates(config):
    require(config.get('version') in {2,3,4}, 'Unsupported automatic Advisor budget policy')
    flexible=config['version']==4
    maximum=None if flexible else config.get('max_batches')
    target=config.get('preferred_max_batches') if flexible else config.get('target_batches',maximum)
    require(type(target) is int and target>0 and (flexible or (type(maximum) is int and target<=maximum)),
            'Invalid Advisor batch target/maximum')
    base={k:copy.deepcopy(v) for k,v in config.items() if k!='alternatives'}
    base['target_batches']=target
    base['max_batches']=maximum
    choices=[base]+[{**copy.deepcopy(base),**copy.deepcopy(x)} for x in config.get('alternatives',[])]
    require(len({x['name'] for x in choices})==len(choices), 'Duplicate Advisor workload profile')
    previous=None
    for choice in choices:
        limits=choice['limits']
        required={'concerns','operations','complexity'} | ({'uses'} if config['version']==2 else set())
        require(set(limits)<={'concerns','expressions','operations','uses','complexity'}
                and required<=set(limits)
                and all(type(v) in {int,float} and v>0 for v in limits.values()), 'Invalid workload limits')
        require(type(choice.get('standalone_expression_target')) is int and choice['standalone_expression_target']>0,
                'Invalid source distribution target')
        require(choice['target_batches']==target and choice['max_batches']==maximum,
                'Alternative must preserve Advisor execution budget')
        weight=choice.get('association_weight',1)
        require(type(weight) in {int,float} and 0<=weight<=1, 'Invalid association weight')
        if previous is not None:
            require(set(limits)==set(previous) and all(limits[k]>=previous[k] for k in limits),
                    'Workload alternatives must be ordered from lighter to broader')
        previous=limits
    return choices


def select(config, evaluate):
    """New policies minimize packets; legacy policies retain their early target exit."""
    trials=[];best=None
    for choice in candidates(config):
        packets,reason=evaluate(choice)
        trial=dict(name=choice['name'],limits=choice['limits'],
                   batches=len(packets) if packets is not None else None,reason=reason)
        trials.append(trial)
        if packets is None:continue
        if config.get('max_batches') is not None:
            require(len(packets)<=config['max_batches'], 'Planner returned an over-budget candidate')
        if best is None or len(packets)<len(best[0]):best=(packets,choice)
        if config['version']==2 and len(packets)<=config['target_batches']:break
    if best is None:
        detail='; '.join(x['name']+': '+x['reason'] for x in trials)
        bound=(f"the {config['max_batches']}-request budget and " if config.get('max_batches') is not None else '')
        raise PlanningBudgetError(f"Could not construct a complete Advisor plan within {bound}capacity/workload limits. No review submitted; no sources removed. {detail}",trials)
    packets,choice=best
    target=config['preferred_max_batches'] if config['version']==4 else config.get('target_batches',config['max_batches'])
    maximum=max(target,len(packets)) if config['version']==4 else config['max_batches']
    budget=dict(version=1,target_batches=target,max_batches=maximum,
                planned_batches=len(packets),target_met=len(packets)<=target,
                selected_profile=choice['name'],user_confirmation_required=False,
                scope='Advisor logical submissions including explicit retries/follow-ups; cached results do not consume a new slot')
    if config['version']==4:
        budget.update(preferred_max_batches=target,automatic_overflow=len(packets)>target,
                      overflow_reason='Complete packing under unchanged capacity/workload bounds requires more packets than preferred.' if len(packets)>target else '')
    return packets,choice,budget,trials


def check_plan(run, stage=None):
    import mentortrace_v1 as m
    run=Path(run);protocol=m.read(run/'inputs/protocol.json')
    if not protocol.get('advisor_batch_budget'):return None
    plan=m.read(run/'inputs/advisor_plan.json');budget=plan.get('execution_budget',{})
    pinned=m.read(run/'inputs/advisor_planning_policy.json')
    count=len(plan['groups'])
    target=pinned['preferred_max_batches'] if pinned['version']==4 else pinned.get('target_batches',pinned['max_batches'])
    maximum=max(target,count) if pinned['version']==4 else pinned['max_batches']
    require(budget.get('max_batches')==maximum and budget.get('target_batches')==target,
            'Frozen Advisor budget differs from planning policy')
    require(count==budget.get('planned_batches') and count<=budget['max_batches'], 'Frozen Advisor plan exceeds submission budget')
    require(protocol.get('advisor_request_budget')==budget, 'Frozen Advisor protocol budget differs')
    if stage and stage.startswith('supplement_'):
        require(stage in {g['stage'] for g in plan['groups']}, 'Advisor request is absent from the frozen plan')
    return budget


def reserve_request(run, request, attempt_name):
    """Reserve before dispatch, atomically across concurrent stages/processes.

    Uncertain/failed attempts retain their slots; no silent resubmission. This counts
    workflow-level adapter invocations, not hidden retries inside a provider/client.
    """
    import mentortrace_v1 as m
    run=Path(run);stage=request['stage']
    if not stage.startswith(('supplement_','evidence_')):return None
    budget=check_plan(run,stage)
    if budget is None:return None
    folder=run/'advisor_request_slots';folder.mkdir(exist_ok=True)
    key=(stage,str(attempt_name))
    for p in folder.glob('*.json'):
        try: old=json.loads(p.read_text(encoding='utf-8'))
        except (ValueError,OSError):continue  # An in-flight reservation still occupies its filename.
        require((old.get('stage'),old.get('attempt_name'))!=key,
                'Advisor attempt already reserved; inspect saved outcome before explicit retry')
    row=dict(stage=stage,attempt_name=str(attempt_name),
             prompt_sha256=hashlib.sha256(request['prompt'].encode()).hexdigest(),status='reserved_before_dispatch')
    attempts=folder/'attempts';attempts.mkdir(exist_ok=True)
    claim=attempts/(hashlib.sha256(json.dumps(key).encode()).hexdigest()+'.json')
    try:
        with claim.open('x',encoding='utf-8') as f:json.dump(row,f,ensure_ascii=False)
    except FileExistsError:
        raise ValueError('Advisor attempt already reserved; inspect saved outcome before explicit retry')
    for index in range(1,budget['max_batches']+1):
        path=folder/f'{index:03}.json'
        try:
            with path.open('x',encoding='utf-8') as f:json.dump(row,f,ensure_ascii=False)
        except FileExistsError:continue
        return path
    raise ValueError(f"Advisor submission budget exhausted ({budget['max_batches']}); no further model call sent. Inspect saved outcomes; never skip sources or silently extend the budget.")
