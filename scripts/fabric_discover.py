#!/usr/bin/env python3
import json, os, subprocess, requests
from _common import load_dotenv
load_dotenv()

def token(resource):
    p=subprocess.run(['az','account','get-access-token','--resource',resource,'--query','accessToken','-o','tsv'],capture_output=True,text=True)
    if p.returncode: raise SystemExit(p.stderr)
    return p.stdout.strip()
headers={'Authorization':'Bearer '+token('https://api.fabric.microsoft.com')}
ws=requests.get('https://api.fabric.microsoft.com/v1/workspaces',headers=headers,timeout=60); ws.raise_for_status()
print('WORKSPACES')
for w in ws.json().get('value',[]): print(f"{w['id']}\t{w.get('displayName')}\t{w.get('type')}")
wid=os.getenv('FABRIC_WORKSPACE_ID')
if wid:
    r=requests.get(f'https://api.fabric.microsoft.com/v1/workspaces/{wid}/semanticModels',headers=headers,timeout=60); r.raise_for_status()
    print('\nSEMANTIC MODELS IN FABRIC_WORKSPACE_ID')
    for m in r.json().get('value',[]): print(f"{m['id']}\t{m.get('displayName')}")
else:
    print('\nSet FABRIC_WORKSPACE_ID in .env, then rerun to list semantic models.')
