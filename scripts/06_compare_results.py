#!/usr/bin/env python3
import csv
import json
from pathlib import Path

from _common import OBS, RESULTS, load_contract, load_queries, write_json
from saccloud.compare import compare_rows
from saccloud.observability import emit

contract = load_contract(); queries=load_queries(); tol=contract["execution"]["tolerance"]
reference=json.loads((RESULTS/"reference.json").read_text())
platforms=[p for p in ["databricks","snowflake","fabric"] if (RESULTS/f"{p}.json").exists()]
summary={}
rows=[]
for platform in platforms:
    observed=json.loads((RESULTS/f"{platform}.json").read_text())
    summary[platform]={}
    for q in queries["queries"]:
        qid=q["id"]
        if q.get("probe")=="fill_rate_rollup":
            # Platform file contains daily values. The paper should report the
            # derived monthly rollup separately after user validation.
            verdict={"verdict":"OBSERVED", "type":"rollup_series", "detail":"daily series captured; derive monthly recompute vs average in analysis"}
        elif qid not in observed:
            verdict={"verdict":"NOT_RUN", "type":"missing", "detail":"query not present"}
        else:
            verdict=compare_rows(reference[qid], observed[qid], tol)
        summary[platform][qid]=verdict
        rows.append({"platform":platform,"query_id":qid,**verdict})
        emit(OBS,{"event":"conformance_result","platform":platform,"query_id":qid,**verdict})
write_json(RESULTS/"conformance_summary.json",summary)
with (RESULTS/"conformance_summary.csv").open("w",newline="",encoding="utf-8") as f:
    w=csv.DictWriter(f,fieldnames=["platform","query_id","verdict","type","detail"]);w.writeheader();w.writerows(rows)
print("Compared platforms:", platforms or "none")
print("Wrote", RESULTS/"conformance_summary.csv")
