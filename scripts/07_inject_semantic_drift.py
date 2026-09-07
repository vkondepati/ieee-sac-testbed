#!/usr/bin/env python3
import argparse
from copy import deepcopy

from _common import RESULTS, load_contract, write_json
from saccloud.contract import sha256_obj
from saccloud.drift import mutate
from saccloud.versioning import compare_contracts

ap=argparse.ArgumentParser()
ap.add_argument("scenario", choices=["empty_set_zero","calendar_gregorian","fill_rate_avg_rollup","fill_rate_formula_change","revoke_reader","source_ordered_quantity_decimal"])
args=ap.parse_args()
base=load_contract(); head=mutate(base,args.scenario)
report={"scenario":args.scenario,"base_hash":sha256_obj(base),"mutated_hash":sha256_obj(head),"versioning":compare_contracts(base,head)}
write_json(RESULTS/f"drift_{args.scenario}.json",report)
import yaml
(RESULTS/f"drift_{args.scenario}.yaml").write_text(yaml.safe_dump(head,sort_keys=False),encoding="utf-8")
print(report)
