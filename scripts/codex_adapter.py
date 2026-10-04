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

def invoke(folder,prompt,images=(),*,model='gpt-6-sol',reasoning_effort='xhigh'):
 folder=Path(folder).resolve();folder.mkdir(parents=True,exist_ok=True)
 m.require(not (folder/'START.json').exists(),'Existing attempt; inspect before rerun')
 binary=shutil.which('codex');m.require(binary,'Codex executable unavailable')
 empty=Path(tempfile.mkdtemp(prefix='mentortrace-isolated-'))
 cmd=[binary,'exec','--ignore-user-config','--ephemeral','--skip-git-repo-check','-C',str(empty),'-s','read-only','-m',model,
      '-c','model_reasoning_effort='+m.dump(reasoning_effort),'-c','project_doc_max_bytes=0','-c','web_search="disabled"',
      '-c','agents.enabled=false','--enable','skip_host_skill_discovery','--json','-o',str(folder/'final_text.json')]
 for feature in ['shell_tool','unified_exec','apps','plugins','multi_agent','multi_agent_v2','code_mode_host','browser_use','computer_use','image_generation','skill_search','memories','hooks','sleep_tool','goals','workspace_dependencies','in_app_browser','tool_suggest','view_image','shell_snapshot']:
  cmd+=['--disable',feature]
 folders=list((Path.home()/'.agents/skills').glob('*/SKILL.md'))
 cmd+=['-c','skills.config=['+','.join('{path='+m.dump(str(p).replace('\\','/'))+',enabled=false}' for p in folders)+']']
 for image in images:cmd+=['--image',str(image)]
 cmd+=['--','-'];env=os.environ.copy()
 for name in ['CODEX_APP_TOOLS_PIPE_PATH','CODEX_SESSION_ID','CODEX_THREAD_ID','CODEX_INTERNAL_ORIGINATOR_OVERRIDE']:env.pop(name,None)
 (folder/'prompt.txt').write_text(prompt,encoding='utf-8')
 m.save(folder/'START.json',{'time':datetime.datetime.now(datetime.timezone.utc).isoformat(),'command':cmd,'prompt_sha256':m.sha(folder/'prompt.txt'),'images':[{'path':str(p),'sha256':m.sha(p)} for p in images]})
 with (folder/'events.jsonl').open('w',encoding='utf-8') as out,(folder/'stderr.txt').open('w',encoding='utf-8') as err:
  proc=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=out,stderr=err,text=True,encoding='utf-8',env=env)
  m.save(folder/'process.json',{'pid':proc.pid})
  try:proc.communicate(prompt,timeout=1800)
  except subprocess.TimeoutExpired:proc.kill();proc.wait();m.save(folder/'UNCERTAIN.json',{'timeout':True});raise
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
  'model':model,'reasoning_effort':reasoning_effort,'prompt_sha256':m.sha(folder/'prompt.txt'),
  'images':[{'sha256':m.sha(p)} for p in images]})
 return folder/'final_text.json',usage
