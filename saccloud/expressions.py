from __future__ import annotations

from typing import Any, Dict


def quote_sql_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def sql_filter(filter_def: Dict[str, Any], alias: str = "") -> str:
    col = f"{alias}.{filter_def['column']}" if alias else filter_def["column"]
    op = filter_def.get("op", "eq")
    value = filter_def.get("value")
    if op == "eq":
        return f"{col} = {quote_sql_string(str(value))}"
    if op == "ne":
        return f"{col} <> {quote_sql_string(str(value))}"
    if op == "is_null":
        return f"{col} IS NULL"
    if op == "not_null":
        return f"{col} IS NOT NULL"
    raise ValueError(f"unsupported filter op: {op}")


def dax_filter_expr(filter_def: Dict[str, Any], table: str) -> str:
    col = f"'{table}'[{filter_def['column']}]"
    op = filter_def.get("op", "eq")
    value = filter_def.get("value")
    if op == "eq":
        return f'{col} = "{str(value).replace(chr(34), chr(34)*2)}"'
    if op == "ne":
        return f'{col} <> "{str(value).replace(chr(34), chr(34)*2)}"'
    if op == "is_null":
        return f"ISBLANK({col})"
    if op == "not_null":
        return f"NOT ISBLANK({col})"
    raise ValueError(f"unsupported filter op: {op}")
