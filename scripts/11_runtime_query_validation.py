#!/usr/bin/env python3
import argparse, json
from _common import RESULTS, load_queries

ap=argparse.ArgumentParser();ap.add_argument("platform",choices=["databricks","snowflake","fabric"]);args=ap.parse_args()
raw_path=RESULTS/f"{args.platform}_raw.json"
if not raw_path.exists(): raise SystemExit(f"Run scripts/05_run_platform.py {args.platform} first")
raw=json.loads(raw_path.read_text());defs={q['id']:q for q in load_queries()['queries']}
failed=0
for qid,p in raw.items():
    text=p.get('sql') or p.get('dax') or ''
    result=p.get('result',{})
    ok=bool(text.strip()) and 'rows' in result
    print(qid, 'VALID' if ok else 'INVALID', 'rows=',len(result.get('rows',[])))
    if not ok: failed+=1
raise SystemExit(1 if failed else 0)
