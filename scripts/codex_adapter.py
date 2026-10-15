"""Isolated Codex transport for an explicitly authorized manuscript request."""
import argparse
import datetime
import os
import shutil
import subprocess
import tempfile
import sys
import time
from pathlib import Path
import mentortrace_v1 as m
from execution_policy import validate_authorization

def invoke(folder,prompt,images=(),*,model='gpt-6-sol',reasoning_effort='xhigh',service_tier='default',settings_authorization=None,transport='default',timeout_seconds=1800):
 authorization_sha256=validate_authorization(settings_authorization,model,reasoning_effort,service_tier)
 folder=Path(folder).resolve();folder.mkdir(parents=True,exist_ok=True)
 m.require(not (folder/'START.json').exists(),'Existing attempt; inspect before rerun')
 binary=shutil.which('codex');m.require(binary,'Codex executable unavailable')
 empty=Path(tempfile.mkdtemp(prefix='mentortrace-isolated-'))
 cmd=[binary,'exec','--ignore-user-config','--ephemeral','--skip-git-repo-check','-C',str(empty),'-s','read-only','-m',model,
      '-c','service_tier='+m.dump(service_tier),'-c','model_reasoning_effort='+m.dump(reasoning_effort),'-c','project_doc_max_bytes=0','-c','web_search="disabled"',
      '-c','agents.enabled=false','--enable','skip_host_skill_discovery','--json','-o',str(folder/'final_text.json')]
 m.require(transport in ['default','http_sse'],'Unsupported transport')
 m.require(isinstance(timeout_seconds,int) and timeout_seconds>0,'Invalid client timeout')
 if transport=='http_sse':
  # Per-request provider configuration only. Keep the existing OpenAI credential,
  # authorized endpoint, model, effort and tier; do not edit user configuration.
  overrides={'model_provider':'mentortrace_openai',
   'model_providers.mentortrace_openai.name':'OpenAI authorized transport',
   'model_providers.mentortrace_openai.base_url':'https://api.openai.com/v1',
   'model_providers.mentortrace_openai.wire_api':'responses',
   'model_providers.mentortrace_openai.requires_openai_auth':True,
   'model_providers.mentortrace_openai.supports_websockets':False,
   'model_providers.mentortrace_openai.stream_idle_timeout_ms':1200000,
   'model_providers.mentortrace_openai.stream_max_retries':0,
   'model_providers.mentortrace_openai.request_max_retries':1}
  for name,value in overrides.items():cmd+=['-c',name+'='+m.dump(value)]
 for feature in ['shell_tool','unified_exec','apps','plugins','multi_agent','multi_agent_v2','code_mode_host','browser_use','computer_use','image_generation','skill_search','memories','hooks','sleep_tool','goals','workspace_dependencies','in_app_browser','tool_suggest','view_image','shell_snapshot']:
  cmd+=['--disable',feature]
 folders=list((Path.home()/'.agents/skills').glob('*/SKILL.md'))
 cmd+=['-c','skills.config=['+','.join('{path='+m.dump(str(p).replace('\\','/'))+',enabled=false}' for p in folders)+']']
 for image in images:cmd+=['--image',str(image)]
 cmd+=['--','-'];env=os.environ.copy()
 for name in ['CODEX_APP_TOOLS_PIPE_PATH','CODEX_SESSION_ID','CODEX_THREAD_ID','CODEX_INTERNAL_ORIGINATOR_OVERRIDE']:env.pop(name,None)
 (folder/'prompt.txt').write_text(prompt,encoding='utf-8')
 m.save(folder/'settings_authorization.json',settings_authorization)
 m.save(folder/'START.json',{'time':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':cmd,'transport':transport,'timeout_seconds':timeout_seconds,'settings_authorization_sha256':authorization_sha256,'prompt_sha256':m.sha(folder/'prompt.txt'),'images':[{'path':str(p),'sha256':m.sha(p)} for p in images]})
 with (folder/'events.jsonl').open('w',encoding='utf-8') as out,(folder/'stderr.txt').open('w',encoding='utf-8') as err:
  proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=out,stderr=err,text=True,encoding='utf-8',env=env)
  m.save(folder/'process.json',{'pid':proc.pid})
  try:proc.communicate(prompt,timeout=timeout_seconds)
  except subprocess.TimeoutExpired:proc.kill();proc.wait();m.save(folder/'UNCERTAIN.json',{'timeout':True,'timeout_seconds':timeout_seconds,'consumption':'Unreported; not assumed zero.'});raise
 events=[]
 for line in (folder/'events.jsonl').read_text(encoding='utf-8').splitlines():
  if line.strip():
   try:events.append(__import__('json').loads(line))
   except ValueError:pass
 m.require(proc.returncode==0,'Codex failed; inspect stderr/events')
 m.require(not any(e.get('item',{}).get('type') not in [None,'agent_message','reasoning','error'] for e in events),'Unexpected tool or action in isolated review')
 m.require(any(e.get('type')=='turn.completed' for e in events),'No completed turn')
 m.require((folder/'final_text.json').exists(),'Missing model output')
 usage=[e.get('usage') for e in events if e.get('type')=='turn.completed']
 m.save(folder/'audit.json',{'returncode':proc.returncode,'usage':usage,'tool_events':0,'fresh_ephemeral_context':True,
  'model':model,'reasoning_effort':reasoning_effort,'requested_service_tier':service_tier,'transport':transport,'timeout_seconds':timeout_seconds,'settings_authorization_sha256':authorization_sha256,'output_sha256':m.sha(folder/'final_text.json'),'prompt_sha256':m.sha(folder/'prompt.txt'),
  'images':[{'sha256':m.sha(p)} for p in images]})
 return folder/'final_text.json',usage
