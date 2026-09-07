from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict


def scalar(v: Any):
    if v is None:
        return None
    if isinstance(v, Decimal):
        return format(v, "f")
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v)
    return s


def _clean_col(name: str) -> str:
    n = name.strip()
    if "[" in n and n.endswith("]"):
        n = n.rsplit("[", 1)[-1][:-1]
    if "." in n:
        n = n.split(".")[-1]
    return n.strip('"').lower()


def normalize_table(result: Dict[str, Any], expected_dims: list[str] | None = None) -> list[dict[str, Any]]:
    columns = [_clean_col(c) for c in result.get("columns", [])]
    rows = result.get("rows", [])
    out = []
    for raw in rows:
        obj = {_clean_col(k): v for k, v in raw.items()} if isinstance(raw, dict) else dict(zip(columns, raw))
        canon = {}
        for k, v in obj.items():
            ck = "value" if k in {"value", "agg(fill_rate)", "agg(revenue)", "agg(gross_margin)", "agg(inventory_turnover)", "agg(unique_customers)", "daily_fill_rate"} or k.startswith("measure(") else k
            sv = scalar(v)
            if ck in {"month", "order_date"} and isinstance(sv, str) and len(sv) >= 10 and sv[4:5] == "-" and sv[7:8] == "-":
                sv = sv[:10]
            canon[ck] = sv
        out.append(canon)
    dims = expected_dims or []
    out.sort(key=lambda r: tuple("" if r.get(d) is None else str(r.get(d)) for d in dims))
    return out


def normalize_platform_queries(raw_queries: Dict[str, Any], query_defs: Dict[str, Any]) -> Dict[str, Any]:
    defs = {q["id"]: q for q in query_defs["queries"]}
    out: Dict[str, Any] = {}
    for qid, payload in raw_queries.items():
        q = defs[qid]
        result = payload.get("result", {})
        if q.get("probe") == "fill_rate_rollup":
            # Store daily rows; monthly rollup is derived by comparison/report code.
            out[qid] = normalize_table(result, ["order_date"])
        else:
            out[qid] = normalize_table(result, q.get("dimensions", []))
            if not q.get("dimensions") and not out[qid]:
                out[qid] = [{"value": None}]
    return out
