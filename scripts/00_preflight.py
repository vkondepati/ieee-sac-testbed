#!/usr/bin/env python3
import argparse, json, os, shutil, sys
from pathlib import Path

from _common import FIXTURE, load_contract, load_dotenv
from saccloud.adapters import ADAPTERS

ap = argparse.ArgumentParser()
ap.add_argument('platform', choices=['databricks','snowflake','fabric'])
ap.add_argument('--env', default=None)
args = ap.parse_args()
load_dotenv(None if args.env is None else Path(args.env))
contract = load_contract()
errors=[]

print(f'Platform: {args.platform}')
print(f'Fixture: {FIXTURE} ({FIXTURE.stat().st_size} bytes)')

if args.platform == 'databricks':
    req=['DATABRICKS_SERVER_HOSTNAME','DATABRICKS_HTTP_PATH','DATABRICKS_CATALOG']
    for k in req:
        if not os.getenv(k): errors.append(f'missing {k}')
    if not os.getenv('DATABRICKS_ACCESS_TOKEN') and not (os.getenv('DATABRICKS_CLIENT_ID') and os.getenv('DATABRICKS_CLIENT_SECRET')):
        errors.append('set DATABRICKS_ACCESS_TOKEN or both DATABRICKS_CLIENT_ID and DATABRICKS_CLIENT_SECRET')
    if not errors:
        a=ADAPTERS['databricks'](contract,FIXTURE)
        try:
            r=a._statement('SELECT current_catalog() AS catalog, current_schema() AS schema, current_user() AS user')
            print(json.dumps(r.get('rows',[]),indent=2))
        except Exception as e: errors.append(f'connectivity: {e}')

elif args.platform == 'snowflake':
    req=['SNOWFLAKE_ACCOUNT','SNOWFLAKE_USER','SNOWFLAKE_WAREHOUSE','SNOWFLAKE_DATABASE']
    for k in req:
        if not os.getenv(k): errors.append(f'missing {k}')
    if not os.getenv('SNOWFLAKE_PASSWORD') and os.getenv('SNOWFLAKE_AUTHENTICATOR','').lower() != 'externalbrowser':
        errors.append('set SNOWFLAKE_PASSWORD or SNOWFLAKE_AUTHENTICATOR=externalbrowser')
    if not errors:
        a=ADAPTERS['snowflake'](contract,FIXTURE)
        try:
            r=a._execute('SELECT CURRENT_VERSION(), CURRENT_USER(), CURRENT_ROLE(), CURRENT_WAREHOUSE(), CURRENT_DATABASE()')
            print(json.dumps(r.get('rows',[]),indent=2,default=str))
        except Exception as e: errors.append(f'connectivity: {e}')

else:
    mode=os.getenv('FABRIC_AUTH_MODE','azure_cli').lower()
    if mode=='azure_cli':
        az_executable = shutil.which('az')
        if not az_executable: errors.append('Azure CLI not found; install it and run az login')
        else:
            import subprocess
            p=subprocess.run([az_executable,'account','show','-o','json'],capture_output=True,text=True)
            if p.returncode != 0: errors.append("Azure CLI is not logged in; run 'az login'")
            else:
                acct=json.loads(p.stdout); print('Azure account:',acct.get('name'),acct.get('user',{}).get('name'),acct.get('tenantId'))
    elif mode=='service_principal':
        for k in ['FABRIC_TENANT_ID','FABRIC_CLIENT_ID','FABRIC_CLIENT_SECRET']:
            if not os.getenv(k): errors.append(f'missing {k}')
    else: errors.append('FABRIC_AUTH_MODE must be azure_cli or service_principal')
    for k in ['FABRIC_WORKSPACE_ID','FABRIC_SEMANTIC_MODEL_ID']:
        if not os.getenv(k): errors.append(f'missing {k}')
    if not errors:
        a=ADAPTERS['fabric'](contract,FIXTURE)
        try:
            d=a._get_definition(); parts=len(d.get('definition',d).get('parts',[]))
            if not parts: errors.append('Fabric semantic model definition returned no parts')
            else: print('Fabric semantic model definition fetched; parts=',parts)
        except Exception as e: errors.append(f'connectivity: {e}')

if errors:
    print('\nPRECHECK FAILED')
    for e in errors: print(' -',e)
    raise SystemExit(1)
print('\nPRECHECK PASSED')
