from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any


def _num(v: Any):
    if v is None:
        return None
    try:
        return Decimal(str(v))
    except (InvalidOperation, ValueError):
        return None


def equal_scalar(a: Any, b: Any, abs_tol: Decimal, rel_tol: Decimal) -> bool:
    if a is None or b is None:
        return a is b
    na, nb = _num(a), _num(b)
    if na is not None and nb is not None:
        diff = abs(na - nb)
        scale = max(abs(na), abs(nb))
        return diff <= max(abs_tol, rel_tol * scale)
    return str(a) == str(b)


def compare_rows(expected: list[dict[str, Any]], observed: list[dict[str, Any]], tolerance: dict[str, Any]) -> dict[str, Any]:
    abs_tol = Decimal(str(tolerance["abs"]))
    rel_tol = Decimal(str(tolerance["rel"]))
    if len(expected) != len(observed):
        return {"verdict": "DIVERGENT", "type": "structure", "detail": f"row_count {len(expected)} != {len(observed)}"}
    for i, (e, o) in enumerate(zip(expected, observed)):
        if set(e) != set(o):
            return {"verdict": "DIVERGENT", "type": "structure", "detail": f"row {i} columns {sorted(e)} != {sorted(o)}"}
        for k in e:
            if not equal_scalar(e[k], o[k], abs_tol, rel_tol):
                return {"verdict": "DIVERGENT", "type": "value", "detail": f"row {i} col {k}: expected={e[k]!r}, observed={o[k]!r}"}
    return {"verdict": "CONFORM", "type": "none", "detail": "normalized results equivalent"}
