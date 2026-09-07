#!/usr/bin/env python3
import argparse
from _common import load_contract
from saccloud.governance import expected_access, governance_matrix

ap=argparse.ArgumentParser();ap.add_argument("--role");ap.add_argument("--action",choices=["discover","query","administer"],default="query");ap.add_argument("--observed",choices=["allow","deny"],help="optional live result to compare with contract")
args=ap.parse_args();c=load_contract()
if not args.role:
    for row in governance_matrix(c,["semantic_reader","semantic_admin","sales_analyst"]): print(row)
else:
    exp=expected_access(c,args.role,args.action);print("expected:","allow" if exp else "deny")
    if args.observed:
        obs=args.observed=="allow";print("observed:",args.observed);print("verdict:","CONFORM" if obs==exp else "DIVERGENT")
        raise SystemExit(0 if obs==exp else 1)
