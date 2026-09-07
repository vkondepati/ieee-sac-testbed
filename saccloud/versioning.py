from __future__ import annotations

from typing import Any, Dict


def _flatten(obj: Any, prefix: str = "") -> dict[str, Any]:
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{prefix}.{k}" if prefix else str(k)
            out.update(_flatten(v, p))
    elif isinstance(obj, list):
        out[prefix] = obj
    else:
        out[prefix] = obj
    return out


def compare_contracts(base: Dict[str, Any], head: Dict[str, Any]) -> dict[str, Any]:
    a, b = _flatten(base), _flatten(head)
    changed = sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))
    breaking_roots = [
        "metrics.", "execution.null_policy", "execution.empty_set", "execution.divide_by_zero",
        "execution.distinct", "execution.time", "governance.access",
    ]
    major = [p for p in changed if p.startswith(tuple(breaking_roots)) and not p.endswith(("description", "display_name"))]
    if major:
        bump = "major"
    elif any(p.startswith(("metrics.", "source.columns")) for p in changed):
        bump = "minor"
    else:
        bump = "patch"
    return {"changed_paths": changed, "breaking_paths": major, "recommended_bump": bump}
