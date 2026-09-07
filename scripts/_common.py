from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from saccloud.contract import load_yaml  # noqa: E402

CONTRACT = ROOT / "contracts" / "semantic_contract.yaml"
FIXTURE = ROOT / "data" / "fixture.csv"
QUERIES = ROOT / "queries" / "query_intents.yaml"
RESULTS = ROOT / "results"
GENERATED = ROOT / "generated"
OBS = ROOT / "observability" / "events.ndjson"


def load_contract():
    return load_yaml(CONTRACT)


def load_queries():
    return load_yaml(QUERIES)


def write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str, sort_keys=True), encoding="utf-8")


def load_dotenv(path: Path | None = None):
    p = path or ROOT / ".env"
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())
