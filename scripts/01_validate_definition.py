#!/usr/bin/env python3
from _common import load_contract
from saccloud.contract import validate_contract, sha256_obj

c = load_contract()
errors = validate_contract(c)
print("contract_hash:", sha256_obj(c))
if errors:
    print("INVALID")
    for e in errors:
        print(" -", e)
    raise SystemExit(1)
print("VALID")
