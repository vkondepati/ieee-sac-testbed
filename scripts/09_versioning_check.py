#!/usr/bin/env python3
import argparse
from pathlib import Path
from saccloud.contract import load_yaml
from saccloud.versioning import compare_contracts
from _common import CONTRACT

ap=argparse.ArgumentParser();ap.add_argument("head",help="mutated/new contract YAML");args=ap.parse_args()
r=compare_contracts(load_yaml(CONTRACT),load_yaml(Path(args.head)))
for k,v in r.items(): print(f"{k}: {v}")
