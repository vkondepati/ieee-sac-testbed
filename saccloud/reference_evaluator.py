from __future__ import annotations

import csv
from collections import defaultdict
from datetime import date
from decimal import Decimal, getcontext
from pathlib import Path
from typing import Any, Dict, Iterable

getcontext().prec = 38


def _dec(v: Any) -> Decimal | None:
    if v in (None, ""):
        return None
    return Decimal(str(v))


def load_fixture(path: str | Path) -> list[dict[str, Any]]:
    rows = []
    for raw in csv.DictReader(Path(path).open(encoding="utf-8")):
        r: dict[str, Any] = dict(raw)
        r["order_id"] = int(raw["order_id"])
        r["order_date"] = date.fromisoformat(raw["order_date"])
        for c in ["ordered_quantity", "fulfilled_quantity"]:
            r[c] = int(raw[c]) if raw[c] != "" else None
        for c in ["net_sales_amount", "cost_of_goods_sold", "inventory_value"]:
            r[c] = _dec(raw[c])
        for c in ["customer_id", "product_id", "region", "warehouse_id", "order_status"]:
            r[c] = raw[c] if raw[c] != "" else None
        rows.append(r)
    return rows


def _matches_filter(row: dict[str, Any], f: dict[str, Any]) -> bool:
    op = f.get("op", "eq")
    v = row.get(f["column"])
    target = f.get("value")
    if op == "eq":
        return v == target
    if op == "ne":
        return v != target
    if op == "is_null":
        return v is None
    if op == "not_null":
        return v is not None
    raise ValueError(op)


def _apply_filters(rows: Iterable[dict[str, Any]], filters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [r for r in rows if all(_matches_filter(r, f) for f in filters)]


def _row_expr(node: dict[str, Any], row: dict[str, Any], null_policy: str):
    op = node["op"]
    if op == "column":
        return row.get(node["name"])
    if op in {"subtract", "add"}:
        a = _row_expr(node["left"], row, null_policy)
        b = _row_expr(node["right"], row, null_policy)
        if null_policy == "propagate" and (a is None or b is None):
            return None
        a = Decimal(0) if a is None else Decimal(str(a))
        b = Decimal(0) if b is None else Decimal(str(b))
        return a - b if op == "subtract" else a + b
    raise ValueError(f"unsupported row op {op}")


def _sum(values: list[Any], empty_set: str):
    nums = [Decimal(str(v)) for v in values if v is not None]
    if not nums:
        return None if empty_set == "null" else Decimal(0)
    return sum(nums, Decimal(0))


def _avg(values: list[Any], empty_set: str):
    nums = [Decimal(str(v)) for v in values if v is not None]
    if not nums:
        return None if empty_set == "null" else Decimal(0)
    return sum(nums, Decimal(0)) / Decimal(len(nums))


def _ratio(n, d, policy: str):
    if n is None or d is None:
        return None
    if Decimal(str(d)) == 0:
        if policy == "null":
            return None
        if policy == "zero":
            return Decimal(0)
        raise ZeroDivisionError("divide_by_zero=error")
    return Decimal(str(n)) / Decimal(str(d))


def evaluate_metric(metric: dict[str, Any], contract: dict[str, Any], rows: list[dict[str, Any]]):
    metric_rows = rows
    if metric.get("filter"):
        metric_rows = _apply_filters(metric_rows, [metric["filter"]])
    execution = contract["execution"]
    empty_set = execution["empty_set"]
    null_policy = execution["null_policy"]

    def agg(node: dict[str, Any]):
        op = node["op"]
        if op == "sum":
            return _sum([_row_expr(node["expr"], r, null_policy) for r in metric_rows], empty_set)
        if op == "avg":
            return _avg([_row_expr(node["expr"], r, null_policy) for r in metric_rows], empty_set)
        if op == "count_distinct":
            cols = node["columns"]
            vals = []
            for r in metric_rows:
                tup = tuple(r.get(c) for c in cols)
                if len(cols) == 1 and tup[0] is None:
                    continue
                if len(cols) > 1 and execution["distinct"].get("tuple_nulls") == "exclude" and any(x is None for x in tup):
                    continue
                vals.append(tup)
            return Decimal(len(set(vals)))
        if op == "divide":
            return _ratio(agg(node["numerator"]), agg(node["denominator"]), execution["divide_by_zero"])
        raise ValueError(f"unsupported aggregate op {op}")

    return agg(metric["expression"])


def _dimension_value(row: dict[str, Any], dim: str):
    if dim == "month":
        d = row["order_date"]
        return date(d.year, d.month, 1).isoformat()
    if dim == "day":
        return row["order_date"].isoformat()
    return row.get(dim)


def evaluate_metric_query(contract: dict[str, Any], rows: list[dict[str, Any]], q: dict[str, Any]) -> list[dict[str, Any]]:
    base = _apply_filters(rows, q.get("filters", []))
    dims = q.get("dimensions", [])
    metric = contract["metrics"][q["metric"]]
    if not dims:
        return [{"value": evaluate_metric(metric, contract, base)}]
    groups: dict[tuple, list[dict[str, Any]]] = defaultdict(list)
    for r in base:
        key = tuple(_dimension_value(r, d) for d in dims)
        groups[key].append(r)
    out = []
    for key in sorted(groups, key=lambda x: tuple("" if v is None else str(v) for v in x)):
        row = {d: v for d, v in zip(dims, key)}
        row["value"] = evaluate_metric(metric, contract, groups[key])
        out.append(row)
    return out


def iso_week_partition(rows: list[dict[str, Any]], filters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[tuple[int, int], int] = defaultdict(int)
    for r in _apply_filters(rows, filters):
        iso = r["order_date"].isocalendar()
        counts[(iso.year, iso.week)] += 1
    return [{"iso_week_year": y, "iso_week": w, "value": Decimal(c)} for (y, w), c in sorted(counts.items())]


def fill_rate_rollup(contract: dict[str, Any], rows: list[dict[str, Any]]) -> dict[str, Any]:
    metric = contract["metrics"]["fill_rate"]
    completed = _apply_filters(rows, [metric["filter"]]) if metric.get("filter") else rows
    daily: dict[date, list[dict[str, Any]]] = defaultdict(list)
    monthly: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    for r in completed:
        daily[r["order_date"]].append(r)
        monthly[(r["order_date"].year, r["order_date"].month)].append(r)
    daily_values = {d.isoformat(): evaluate_metric(metric, {**contract, "metrics": {"fill_rate": {**metric, "filter": None}}}, rs) for d, rs in sorted(daily.items())}
    direct_month = {}
    avg_daily = {}
    for ym, rs in sorted(monthly.items()):
        key = f"{ym[0]:04d}-{ym[1]:02d}"
        direct_month[key] = evaluate_metric(metric, {**contract, "metrics": {"fill_rate": {**metric, "filter": None}}}, rs)
        vals = [v for d, v in daily_values.items() if d.startswith(key) and v is not None]
        avg_daily[key] = sum(vals, Decimal(0)) / Decimal(len(vals)) if vals else None
    return {"daily": daily_values, "monthly_recompute": direct_month, "monthly_average_daily": avg_daily}


def evaluate_all(contract: dict[str, Any], fixture_path: str | Path, queries: dict[str, Any]) -> dict[str, Any]:
    rows = load_fixture(fixture_path)
    out: dict[str, Any] = {}
    for q in queries["queries"]:
        if "metric" in q:
            out[q["id"]] = evaluate_metric_query(contract, rows, q)
        elif q.get("probe") == "iso_week_partition":
            out[q["id"]] = iso_week_partition(rows, q.get("filters", []))
        elif q.get("probe") == "fill_rate_rollup":
            out[q["id"]] = fill_rate_rollup(contract, rows)
    return out
