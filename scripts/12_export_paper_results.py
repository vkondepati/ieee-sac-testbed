#!/usr/bin/env python3
import csv,json
from pathlib import Path
from _common import RESULTS, load_queries
platforms=['databricks','snowflake','fabric']
queries=[q['id'] for q in load_queries()['queries']]
summary={}
p=RESULTS/'conformance_summary.json'
if p.exists(): summary=json.loads(p.read_text())
ref=json.loads((RESULTS/'reference.json').read_text())
out=RESULTS/'paper_runtime_results.csv'
with out.open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=['query_id','reference','databricks','databricks_verdict','snowflake','snowflake_verdict','fabric','fabric_verdict'])
    w.writeheader()
    for qid in queries:
        row={'query_id':qid,'reference':json.dumps(ref.get(qid),sort_keys=True)}
        for plat in platforms:
            obs=RESULTS/f'{plat}.json'
            data=json.loads(obs.read_text()) if obs.exists() else {}
            row[plat]=json.dumps(data.get(qid),sort_keys=True) if qid in data else ''
            row[plat+'_verdict']=summary.get(plat,{}).get(qid,{}).get('verdict','NOT_RUN')
        w.writerow(row)
print('Wrote',out)
