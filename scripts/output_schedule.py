"""Conservative output-aware scheduling from source-bound observed calibration."""
import mentortrace_v1 as m


def choose(groups,build,policy,images,profile):
    """No profile means no split. Total token growth is capped at 10%, not hidden."""
    ref=profile['observation']
    m.require(m.sha(ref['path'])==ref['sha256'],'Timing profile observation changed')
    observed=m.read(ref['path'])
    m.require((observed['model'],observed['effort'],observed['service_tier'])==(policy['model'],policy['effort'],'default'),'Output profile settings differ')
    for k in ['targets','input_tokens','output_tokens','elapsed_seconds']:
        m.require(isinstance(observed.get(k),(int,float)) and observed[k]>0,'Incomplete observed timing profile')
    per_target=observed['output_tokens']/observed['targets']
    candidates=[]
    for n in range(1,min(3,len(groups))+1):
        buckets=[[] for _ in range(n)];loads=[0]*n
        for index in sorted(range(len(groups)),key=lambda i:len(groups[i]),reverse=True):
            k=min(range(n),key=lambda i:loads[i]);buckets[k].append(index);loads[k]+=len(groups[index])
        budgets=[build([r for i in bucket for r in groups[i]],k+1)[1] for k,bucket in enumerate(buckets)]
        if not all(b['fits'] for b in budgets):continue
        # Conservative input bounds include repeated page images. Output throughput
        # is an approximation, not a guarantee of concurrency or provider latency.
        ins=[b['reference_text_tokens']+len(images)*policy['image_reserve_each'] for b in budgets]
        outs=[load*per_target for load in loads]
        scale=observed['elapsed_seconds']/(observed['input_tokens']+observed['output_tokens'])
        candidates.append({'parts':n,'buckets':buckets,'estimated_total_tokens':sum(ins)+sum(outs),
            'estimated_critical_seconds':max(a+b for a,b in zip(ins,outs))*scale,'input_bounds':ins,'output_estimates':outs})
    baseline=next(c for c in candidates if c['parts']==1)
    eligible=[c for c in candidates if c['estimated_total_tokens']<=baseline['estimated_total_tokens']*1.10 and c['estimated_critical_seconds']<=baseline['estimated_critical_seconds']*.80]
    selected=min(eligible,key=lambda c:c['estimated_critical_seconds']) if eligible else baseline
    return {'mode':'observed_output_estimate','parallel_workers':selected['parts'],'buckets':selected['buckets'],
        'observation':ref,'comparison':candidates,'token_growth_limit':1.10,'minimum_predicted_wall_reduction':.20,
        'measured_speedup':False,'reason':'Complete groups only; all input/image repetition counted. Estimates require later live validation.'}
