from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable

from .expressions import dax_filter_expr, sql_filter


@dataclass(frozen=True)
class CompileContext:
    contract: Dict[str, Any]
    table: str
    dialect: str

    @property
    def null_policy(self) -> str:
        return self.contract["execution"]["null_policy"]

    @property
    def divide_by_zero(self) -> str:
        return self.contract["execution"]["divide_by_zero"]


def _column_sql(name: str, alias: str | None) -> str:
    return f"{alias}.{name}" if alias else name


def compile_row_sql(expr: Dict[str, Any], *, alias: str | None = None, null_policy: str = "propagate") -> str:
    op = expr["op"]
    if op == "column":
        return _column_sql(expr["name"], alias)
    if op == "subtract":
        left = compile_row_sql(expr["left"], alias=alias, null_policy=null_policy)
        right = compile_row_sql(expr["right"], alias=alias, null_policy=null_policy)
        if null_policy == "coalesce_zero":
            return f"COALESCE({left}, 0) - COALESCE({right}, 0)"
        return f"({left} - {right})"
    if op == "add":
        left = compile_row_sql(expr["left"], alias=alias, null_policy=null_policy)
        right = compile_row_sql(expr["right"], alias=alias, null_policy=null_policy)
        if null_policy == "coalesce_zero":
            return f"COALESCE({left}, 0) + COALESCE({right}, 0)"
        return f"({left} + {right})"
    raise ValueError(f"unsupported row SQL op: {op}")


def _apply_metric_filter_sql(aggregate_expr: str, metric: Dict[str, Any], *, alias: str | None, dialect: str) -> str:
    filt = metric.get("filter")
    if not filt:
        return aggregate_expr
    cond = sql_filter(filt, alias or "")
    # Both target SQL dialects support FILTER on aggregate functions in the
    # metric-expression positions used here. For composed ratios the compiler
    # applies the filter inside each aggregate, not outside the metric view.
    return aggregate_expr.replace("__FILTER_CONDITION__", cond)


def compile_sql_metric(metric: Dict[str, Any], contract: Dict[str, Any], *, dialect: str, alias: str | None = None) -> str:
    null_policy = contract["execution"]["null_policy"]
    divide_policy = contract["execution"]["divide_by_zero"]
    filt = metric.get("filter")
    cond = sql_filter(filt, alias or "") if filt else None

    def agg(node: Dict[str, Any]) -> str:
        op = node["op"]
        if op in {"sum", "avg"}:
            row = compile_row_sql(node["expr"], alias=alias, null_policy=null_policy)
            fn = "SUM" if op == "sum" else "AVG"
            if cond:
                return f"{fn}(CASE WHEN {cond} THEN {row} END)"
            return f"{fn}({row})"
        if op == "count_distinct":
            cols = node["columns"]
            if len(cols) != 1:
                raise NotImplementedError("composite COUNT DISTINCT is a negotiated capability, not emitted by the base compiler")
            col = _column_sql(cols[0], alias)
            if cond:
                # Portable lowering for one-column distinct with a filter.
                return f"COUNT(DISTINCT CASE WHEN {cond} THEN {col} END)"
            return f"COUNT(DISTINCT {col})"
        if op == "divide":
            n = agg(node["numerator"])
            d = agg(node["denominator"])
            if divide_policy == "null":
                return f"({n}) / NULLIF(({d}), 0)"
            if divide_policy == "zero":
                return f"COALESCE(({n}) / NULLIF(({d}), 0), 0)"
            return f"({n}) / ({d})"
        raise ValueError(f"unsupported aggregate SQL op: {op}")

    return agg(metric["expression"])


def compile_dax_row(expr: Dict[str, Any], *, table: str, null_policy: str) -> str:
    op = expr["op"]
    if op == "column":
        return f"'{table}'[{expr['name']}]"
    if op in {"subtract", "add"}:
        left = compile_dax_row(expr["left"], table=table, null_policy=null_policy)
        right = compile_dax_row(expr["right"], table=table, null_policy=null_policy)
        symbol = "-" if op == "subtract" else "+"
        if null_policy == "propagate":
            # DAX arithmetic treats BLANK as zero. The explicit IF preserves
            # the vendor-neutral NULL propagation contract.
            return f"IF(ISBLANK({left}) || ISBLANK({right}), BLANK(), {left} {symbol} {right})"
        return f"COALESCE({left}, 0) {symbol} COALESCE({right}, 0)"
    raise ValueError(f"unsupported DAX row op: {op}")


def compile_dax_metric(metric: Dict[str, Any], contract: Dict[str, Any], *, table: str) -> str:
    null_policy = contract["execution"]["null_policy"]
    divide_policy = contract["execution"]["divide_by_zero"]
    filt = metric.get("filter")
    filter_clause = dax_filter_expr(filt, table) if filt else None

    def wrap_filter(expr: str) -> str:
        if not filter_clause:
            return expr
        return f"CALCULATE({expr}, KEEPFILTERS({filter_clause}))"

    def agg(node: Dict[str, Any]) -> str:
        op = node["op"]
        if op == "sum":
            inner = node["expr"]
            if inner["op"] == "column":
                base = f"SUM('{table}'[{inner['name']}])"
            else:
                row = compile_dax_row(inner, table=table, null_policy=null_policy)
                base = f"SUMX('{table}', {row})"
            return wrap_filter(base)
        if op == "avg":
            inner = node["expr"]
            if inner["op"] != "column":
                row = compile_dax_row(inner, table=table, null_policy=null_policy)
                base = f"AVERAGEX('{table}', {row})"
            else:
                base = f"AVERAGE('{table}'[{inner['name']}])"
            return wrap_filter(base)
        if op == "count_distinct":
            cols = node["columns"]
            if len(cols) != 1:
                raise NotImplementedError("composite distinct requires a platform capability strategy")
            column = f"'{table}'[{cols[0]}]"
            base = f"CALCULATE(DISTINCTCOUNT({column}), KEEPFILTERS({column} <> BLANK()))"
            return wrap_filter(base)
        if op == "divide":
            n = agg(node["numerator"])
            d = agg(node["denominator"])
            alternate = "BLANK()" if divide_policy == "null" else "0"
            if divide_policy == "error":
                return f"({n}) / ({d})"
            return f"DIVIDE({n}, {d}, {alternate})"
        raise ValueError(f"unsupported DAX aggregate op: {op}")

    return agg(metric["expression"])


def metric_names(contract: Dict[str, Any]) -> Iterable[str]:
    return contract.get("metrics", {}).keys()
