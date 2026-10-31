"""Exact schema/string interning for large delivery payloads; no summary or verdict."""
import json,copy,re
from collections import Counter

INSTRUCTIONS='''LOSSLESS INPUT schema_values_v4/v5/v6 supersedes exact_shared_values_v1 for this input only. schemas[N] is an ordered key list. First reconstruct strings[N]: it is literal text, or {$c:[literal text,{$f:F},...]} concatenating literal chunks and fragments[F]; fragments are literal and never recursively decoded. Within data, ~N denotes reconstructed strings[N] and ~~ escapes literal leading ~. ["@N",v1,...] denotes an object with schemas[N] keys and decoded values. ["#N",[[v1,...],...]] denotes an array of those objects. {$a:[...]} is an ordinary array with decoded members, not an outer record marker. {$p:[poolID,start,end]} is an exact Unicode substring of that reconstructed string, end-exclusive. {$j:object} is standard-spaced JSON serialization of the decoded object, ensure_ascii=false, sort_keys=true. {$d:N} denotes definitions[N], recursively decoded by the same rules; definitions form an acyclic graph of exact repeated subtrees. Other containers decode recursively. Reconstruct complete facts, conditions and evidence before judging. Output uses the ordinary delivery contract, never this input encoding.'''

def dump(v):return json.dumps(v,ensure_ascii=False,separators=(',',':'))
def pack(value):
 strings=Counter();shapes=Counter();json_strings={}
 def count(v):
  if isinstance(v,str):
   strings[v]+=1
   if v.startswith('{'):
    try:
     parsed=json.loads(v)
     if isinstance(parsed,dict) and set(parsed)=={'id','field','value'} and json.dumps(parsed,ensure_ascii=False,sort_keys=True)==v:
      json_strings[v]=parsed;count(parsed)
    except (ValueError,TypeError):pass
  elif isinstance(v,dict):
   if any(k in v for k in ['$s','$r','$t','$a','$p','$j','$d']):raise ValueError('Reserved schema-wire key in input')
   shapes[tuple(sorted(v))]+=1
   for a in v.values():count(a)
  elif isinstance(v,list):
   for a in v:count(a)
 count(value);schemas=[];schemaids={};pool=[];stringids={}
 masters=[]
 for candidate in sorted([s for s in strings if len(s)>800 and s not in json_strings],key=len,reverse=True):
  if not any(candidate in master for master in masters):masters.append(candidate)
  if len(masters)>=96:break
 for master in masters:stringids[master]=len(pool);pool.append(master)
 def sid(keys):
  if keys not in schemaids:schemaids[keys]=len(schemas);schemas.append(list(keys))
  return schemaids[keys]
 def enc(v):
  if isinstance(v,str):
   if v in json_strings:return {'$j':enc(json_strings[v])}
   if v in stringids:return '~'+str(stringids[v])
   if len(v)>=60:
    for master in masters:
     start=master.find(v)
     if start>=0:return {'$p':[stringids[master],start,start+len(v)]}
   raw=dump(v);n=strings[v]
   if n>1 and len(raw)>=9 and (n-1)*len(raw)>n*7+4:
    if v not in stringids:stringids[v]=len(pool);pool.append(v)
    return '~'+str(stringids[v])
   return '~'+v if v.startswith('~') else v
  if isinstance(v,list):
   if len(v)>=3 and all(isinstance(a,dict) and set(a)==set(v[0]) for a in v):
    keys=tuple(sorted(v[0]));return ['#'+str(sid(keys)),[[enc(a[k]) for k in keys] for a in v]]
   values=[enc(a) for a in v]
   return {'$a':values} if values and isinstance(values[0],str) and re.fullmatch(r'[@#][0-9]+',values[0]) else values
  if isinstance(v,dict):
   keys=tuple(sorted(v));vals=[enc(v[k]) for k in keys]
   if shapes[keys]>=3 and sum(len(k)+3 for k in keys)>14:return ['@'+str(sid(keys)),*vals]
   return dict(zip(keys,vals))
  return v
 data=enc(value);wire={'encoding':'schema_values_v4','schemas':schemas,'strings':pool,'data':data}
 if len(dump(wire))>900000:
  compact=fragment_pool(wire)
  if len(dump(compact))<len(dump(wire)):wire=compact
  compact=share_structures(wire)
  if len(dump(compact))<len(dump(wire)):wire=compact
 if unpack(wire)!=value:raise ValueError('Exact schema-wire roundtrip failed')
 return wire


def share_structures(wire):
 counts=Counter()
 def count(v):
  if isinstance(v,(dict,list)):
   key=dump(v)
   if len(key)>=50:counts[key]+=1
   for a in (v.values() if isinstance(v,dict) else v):count(a)
 count(wire['data']);ids={};definitions=[]
 def enc(v,root=True):
  if not isinstance(v,(dict,list)):return v
  key=dump(v);n=counts[key]
  if root and n>1 and (n-1)*len(key)>n*14+20:
   if key not in ids:
    ids[key]=len(definitions);definitions.append(None);definitions[ids[key]]=enc(v,False)
   return {'$d':ids[key]}
  if isinstance(v,dict):return {k:enc(a) for k,a in v.items()}
  return [enc(a) for a in v]
 data=enc(wire['data'])
 return {**wire,'encoding':'schema_values_v6','definitions':definitions,'data':data}


def fragment_pool(wire):
 """Intern repeated literal phrases inside the string pool; never summarize prose."""
 counts=Counter()
 for s in wire['strings']:
  words=list(re.finditer(r'\S+',s))
  for size in (3,5,8,12):
   for i in range(len(words)-size+1):
    phrase=s[words[i].start():words[i+size-1].end()]
    if 24<=len(phrase)<=180:counts[phrase]+=1
 ranked=sorted(((n-1)*len(s)-n*12-8,s) for s,n in counts.items() if n>=3)
 phrases=[s for score,s in reversed(ranked) if score>30][:1600]
 if not phrases:return wire
 phrases.sort(key=len,reverse=True);index={s:i for i,s in enumerate(phrases)}
 pattern=re.compile('|'.join(re.escape(s) for s in phrases));entries=[];used=set()
 for s in wire['strings']:
  parts=[];cursor=0;chosen=[]
  for match in pattern.finditer(s):
   if match.start()>cursor:parts.append(s[cursor:match.start()])
   ident=index[match.group()];parts.append({'$f':ident});chosen.append(ident);cursor=match.end()
  if cursor<len(s):parts.append(s[cursor:])
  value={'$c':parts}
  if parts and len(dump(value))<len(dump(s)):entries.append(value);used.update(chosen)
  else:entries.append(s)
 ordered=sorted(used);remap={old:new for new,old in enumerate(ordered)}
 for entry in entries:
  if isinstance(entry,dict):
   for part in entry['$c']:
    if isinstance(part,dict):part['$f']=remap[part['$f']]
 return {**wire,'encoding':'schema_values_v5','strings':entries,'fragments':[phrases[i] for i in ordered]}

def unpack(wire):
 schemas=wire['schemas'];fragments=wire.get('fragments',[])
 pool=[s if isinstance(s,str) else ''.join(p if isinstance(p,str) else fragments[p['$f']] for p in s['$c']) for s in wire['strings']]
 def unwrap(v):
  while isinstance(v,dict) and set(v)=={'$d'}:v=wire['definitions'][v['$d']]
  return v
 def dec(v):
  v=unwrap(v)
  if isinstance(v,str):
   if v.startswith('~~'):return v[1:]
   if re.fullmatch(r'~[0-9]+',v):return pool[int(v[1:])]
   return v
  if isinstance(v,list):
   if v and isinstance(v[0],str) and re.fullmatch(r'@[0-9]+',v[0]):
    keys=schemas[int(v[0][1:])];vals=v[1:]
    if len(keys)!=len(vals):raise ValueError('Bad schema record')
    return {k:dec(a) for k,a in zip(keys,vals)}
   if v and isinstance(v[0],str) and re.fullmatch(r'#[0-9]+',v[0]):
    keys=schemas[int(v[0][1:])];rows=[unwrap(row) for row in unwrap(v[1])]
    if any(len(row)!=len(keys) for row in rows):raise ValueError('Bad schema table')
    return [{k:dec(a) for k,a in zip(keys,row)} for row in rows]
   return [dec(a) for a in v]
  if isinstance(v,dict):
   if set(v)=={'$d'}:return dec(wire['definitions'][v['$d']])
   if set(v)=={'$p'}:
    ident,start,end=unwrap(v['$p']);return pool[ident][start:end]
   if set(v)=={'$j'}:return json.dumps(dec(v['$j']),ensure_ascii=False,sort_keys=True)
   if set(v)=={'$a'}:return [dec(a) for a in unwrap(v['$a'])]
   if set(v)=={'$s'}:return pool[v['$s']]
   if set(v)=={'$r'}:
    sid,*vals=v['$r'];keys=schemas[sid]
    if len(vals)!=len(keys):raise ValueError('Bad record width')
    return {k:dec(a) for k,a in zip(keys,vals)}
   if set(v)=={'$t'}:
    sid,rows=v['$t'];keys=schemas[sid]
    if any(len(row)!=len(keys) for row in rows):raise ValueError('Bad table width')
    return [{k:dec(a) for k,a in zip(keys,row)} for row in rows]
   return {k:dec(a) for k,a in v.items()}
  return v
 return dec(wire['data'])
