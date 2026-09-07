#!/usr/bin/env python3
import argparse
from _common import load_contract
from saccloud.contract import business_review_status

ap = argparse.ArgumentParser()
ap.add_argument("--enforce", action="store_true", help="exit 1 unless the contract is fully approved")
args = ap.parse_args()
status = business_review_status(load_contract())
for k, v in status.items():
    print(f"{k}: {v}")
if args.enforce and not status["gate_pass"]:
    raise SystemExit(1)
