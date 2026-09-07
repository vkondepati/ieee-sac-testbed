#!/usr/bin/env python3
from _common import GENERATED, FIXTURE, load_contract, write_json
from saccloud.adapters import ADAPTERS
from saccloud.contract import sha256_text

contract = load_contract()
summary = {}
for platform, cls in ADAPTERS.items():
    adapter = cls(contract, FIXTURE)
    out = adapter.compile(GENERATED / platform)
    hashes = {k: sha256_text(p.read_text(encoding="utf-8")) for k, p in out.items()}
    summary[platform] = {"capabilities": adapter.capabilities(), "files": {k: str(p) for k, p in out.items()}, "hashes": hashes}
write_json(GENERATED / "compile_manifest.json", summary)
print("Generated artifacts in", GENERATED)
for p, x in summary.items():
    print(p, x["files"])
