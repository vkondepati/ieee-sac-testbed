#!/usr/bin/env python3
import argparse
import time
import uuid

from _common import FIXTURE, OBS, RESULTS, load_contract, load_dotenv, load_queries, write_json
from saccloud.adapters import ADAPTERS
from saccloud.contract import sha256_obj
from saccloud.normalize import normalize_platform_queries
from saccloud.observability import emit, result_hash

ap = argparse.ArgumentParser()
ap.add_argument("platform", choices=sorted(ADAPTERS))
ap.add_argument("--deploy", action="store_true", help="provision fixture and deploy native semantic artifact before queries")
ap.add_argument("--env", default=None, help="optional .env path")
args = ap.parse_args()
load_dotenv(None if args.env is None else __import__('pathlib').Path(args.env))
contract = load_contract(); queries = load_queries()
adapter = ADAPTERS[args.platform](contract, FIXTURE)
run_id = str(uuid.uuid4())
emit(OBS, {"event":"run_start", "run_id":run_id, "platform":args.platform, "semantic_version":contract["package"]["version"], "contract_hash":sha256_obj(contract), "adapter_version":adapter.adapter_version})
if args.deploy:
    t0=time.time(); deployment=adapter.provision_and_deploy();
    write_json(RESULTS / f"{args.platform}_deployment.json", deployment)
    emit(OBS, {"event":"deployment", "run_id":run_id, "platform":args.platform, "elapsed_ms":round((time.time()-t0)*1000,2), "detail":deployment})
    if deployment.get("status") == "PREVIEW_ONLY":
        print(deployment["message"])
        raise SystemExit(0)
raw = adapter.execute_queries(queries)
write_json(RESULTS / f"{args.platform}_raw.json", raw)
norm = normalize_platform_queries(raw, queries)
write_json(RESULTS / f"{args.platform}.json", norm)
emit(OBS, {"event":"platform_results", "run_id":run_id, "platform":args.platform, "result_hash":result_hash(norm), "query_count":len(norm)})
print("Wrote", RESULTS / f"{args.platform}.json")
