from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def result_hash(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str, separators=(",", ":")).encode()).hexdigest()


def emit(path: str | Path, event: Dict[str, Any]):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    payload = {"timestamp_utc": utc_now(), **event}
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, default=str, sort_keys=True) + "\n")


def summarize(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    events = [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()] if p.exists() else []
    verdicts = [e.get("verdict") for e in events if e.get("event") == "conformance_result"]
    return {
        "event_count": len(events),
        "conformance_results": len(verdicts),
        "conform": sum(v == "CONFORM" for v in verdicts),
        "divergent": sum(v == "DIVERGENT" for v in verdicts),
        "unsupported": sum(v == "UNSUPPORTED" for v in verdicts),
        "conformance_rate": (sum(v == "CONFORM" for v in verdicts) / len(verdicts)) if verdicts else None,
    }
