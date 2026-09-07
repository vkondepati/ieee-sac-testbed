from __future__ import annotations

import csv
import os
from pathlib import Path
from typing import Any, Dict


from .base import PlatformAdapter
from ..compiler import compile_sql_metric
from ..expressions import sql_filter


class SnowflakeAdapter(PlatformAdapter):
    name = "snowflake"

    def _cfg(self):
        account = os.getenv("SNOWFLAKE_ACCOUNT", "YOUR_ACCOUNT").strip()
        account = account.removeprefix("https://").removeprefix("http://")
        account = account.split("/", 1)[0].split(":", 1)[0]
        account = account.removesuffix(".snowflakecomputing.com")
        return {
            "account": account,
            "user": os.getenv("SNOWFLAKE_USER", "YOUR_USER"),
            "password": os.getenv("SNOWFLAKE_PASSWORD", ""),
            "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE", "YOUR_WAREHOUSE"),
            "database": os.getenv("SNOWFLAKE_DATABASE", "YOUR_DATABASE"),
            "schema": os.getenv("SNOWFLAKE_SCHEMA", "SAC_CONFORMANCE"),
            "table": os.getenv("SNOWFLAKE_TABLE", "SAC_FACT"),
            "view": os.getenv("SNOWFLAKE_SEMANTIC_VIEW", "SAC_METRICS"),
            "authenticator": os.getenv("SNOWFLAKE_AUTHENTICATOR", ""),
            "role": os.getenv("SNOWFLAKE_ROLE") or None,
        }

    def capabilities(self) -> Dict[str, str]:
        return {
            "vendor_native_semantic_model": "native",
            "metric_aggregation": "native",
            "single_column_distinct": "native",
            "composite_distinct_include_nulls": "unsupported_by_base_compiler",
            "iso_week_calendar": "native",
            "non_additive_rollup": "native_or_contract_guard",
            "runtime_query_api": "native",
        }

    def _conn(self):
        c = self._cfg()
        kw = dict(account=c["account"], user=c["user"], password=c["password"], warehouse=c["warehouse"], database=c["database"], schema=c["schema"])
        if c["authenticator"]:
            kw["authenticator"] = c["authenticator"]
        if c["role"]:
            kw["role"] = c["role"]
        import snowflake.connector
        return snowflake.connector.connect(**kw)

    def _table_name(self):
        c = self._cfg()
        return f'{c["database"]}.{c["schema"]}.{c["table"]}'

    def _view_name(self):
        c = self._cfg()
        return f'{c["database"]}.{c["schema"]}.{c["view"]}'

    def semantic_view_sql(self) -> str:
        table = self._table_name()
        dims = [
            "orders.order_date AS orders.order_date",
            "orders.region AS orders.region",
            "orders.warehouse_id AS orders.warehouse_id",
            "orders.product_id AS orders.product_id",
            "orders.order_status AS orders.order_status",
            "orders.month AS DATE_TRUNC('MONTH', orders.order_date)",
            "orders.iso_week_year AS YEAROFWEEKISO(orders.order_date)",
            "orders.iso_week AS WEEKISO(orders.order_date)",
        ]
        metrics = []
        for name, metric in self.contract["metrics"].items():
            expr = compile_sql_metric(metric, self.contract, dialect="snowflake", alias="orders")
            metrics.append(f"orders.{name} AS {expr}")
        metrics.append("orders.order_count AS COUNT(orders.order_id)")
        return f"""CREATE OR REPLACE SEMANTIC VIEW {self._view_name()}
TABLES (
  orders AS {table} PRIMARY KEY (order_id)
)
DIMENSIONS (
  {',\n  '.join(dims)}
)
METRICS (
  {',\n  '.join(metrics)}
)
COMMENT = 'Generated from vendor-neutral Semantics-as-Code conformance contract';
"""

    def compile(self, output_dir: Path) -> Dict[str, Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        p = output_dir / "snowflake_semantic_view.sql"
        p.write_text(self.semantic_view_sql(), encoding="utf-8")
        return {"sql": p}

    def provision_and_deploy(self) -> Dict[str, Any]:
        c = self._cfg()
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(f"CREATE SCHEMA IF NOT EXISTS {c['database']}.{c['schema']}")
            cur.execute(f"""
            CREATE OR REPLACE TABLE {self._table_name()} (
              order_id NUMBER(38,0), order_date DATE, customer_id VARCHAR, product_id VARCHAR,
              region VARCHAR, warehouse_id VARCHAR, order_status VARCHAR,
              ordered_quantity NUMBER(38,0), fulfilled_quantity NUMBER(38,0),
              net_sales_amount NUMBER(18,2), cost_of_goods_sold NUMBER(18,2), inventory_value NUMBER(18,2)
            )
            """)
            rows = list(csv.DictReader(self.fixture_path.open(encoding="utf-8")))
            sql = f"INSERT INTO {self._table_name()} VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            params = []
            for r in rows:
                params.append(tuple(None if r[k] == "" else r[k] for k in r))
            cur.executemany(sql, params)
            cur.execute(self.semantic_view_sql())
            return {"table": self._table_name(), "semantic_view": self._view_name(), "rows": len(rows)}
        finally:
            conn.close()

    def _execute(self, sql: str) -> Dict[str, Any]:
        conn = self._conn()
        try:
            cur = conn.cursor()
            cur.execute(sql)
            columns = [d[0] for d in cur.description] if cur.description else []
            rows = [list(r) for r in cur.fetchall()] if cur.description else []
            return {"columns": columns, "rows": rows}
        finally:
            conn.close()

    def _query_metric(self, metric: str, dimensions: list[str], filters: list[dict]) -> Dict[str, Any]:
        select = list(dimensions) + [f"AGG({metric}) AS value"]
        sql = f"SELECT {', '.join(select)} FROM {self._view_name()}"
        if filters:
            sql += " WHERE " + " AND ".join(sql_filter(f) for f in filters)
        if dimensions:
            sql += " GROUP BY " + ", ".join(dimensions) + " ORDER BY " + ", ".join(dimensions)
        return {"sql": sql, "result": self._execute(sql)}

    def execute_queries(self, queries: Dict[str, Any]) -> Dict[str, Any]:
        out = {}
        for q in queries["queries"]:
            qid = q["id"]
            if "metric" in q:
                out[qid] = self._query_metric(q["metric"], q.get("dimensions", []), q.get("filters", []))
            elif q.get("probe") == "iso_week_partition":
                sql = f"SELECT iso_week_year, iso_week, AGG(order_count) AS value FROM {self._view_name()} WHERE order_status='Completed' GROUP BY iso_week_year, iso_week ORDER BY iso_week_year, iso_week"
                out[qid] = {"sql": sql, "result": self._execute(sql)}
            elif q.get("probe") == "fill_rate_rollup":
                sql = f"SELECT order_date, AGG(fill_rate) AS daily_fill_rate FROM {self._view_name()} WHERE order_status='Completed' GROUP BY order_date ORDER BY order_date"
                out[qid] = {"sql": sql, "result": self._execute(sql)}
        return out
