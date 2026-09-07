from __future__ import annotations

import csv
import json
import os
import time
from pathlib import Path
from typing import Any, Dict

import requests
import yaml

from .base import PlatformAdapter
from ..compiler import compile_sql_metric
from ..expressions import sql_filter


class DatabricksAdapter(PlatformAdapter):
    name = "databricks"

    def __init__(self, contract: Dict[str, Any], fixture_path: Path):
        super().__init__(contract, fixture_path)
        self._oauth_token = None
        self._oauth_expires_at = 0.0

    def _cfg(self):
        host = os.getenv("DATABRICKS_SERVER_HOSTNAME", "https://YOUR-DATABRICKS-HOST").rstrip("/")
        if not host.startswith("http"):
            host = "https://" + host
        http_path = os.getenv("DATABRICKS_HTTP_PATH", "/sql/1.0/warehouses/YOUR_WAREHOUSE_ID")
        warehouse_id = http_path.rstrip("/").split("/")[-1]
        return {
            "host": host,
            "warehouse_id": warehouse_id,
            "token": os.getenv("DATABRICKS_ACCESS_TOKEN", ""),
            "client_id": os.getenv("DATABRICKS_CLIENT_ID", ""),
            "client_secret": os.getenv("DATABRICKS_CLIENT_SECRET", ""),
            "catalog": os.getenv("DATABRICKS_CATALOG", "main"),
            "schema": os.getenv("DATABRICKS_SCHEMA", "sac_conformance"),
            "table": os.getenv("DATABRICKS_TABLE", "sac_fact"),
            "view": os.getenv("DATABRICKS_METRIC_VIEW", "sac_metrics"),
        }

    def _access_token(self) -> str:
        c = self._cfg()
        if c["token"]:
            return c["token"]
        if not c["client_id"] or not c["client_secret"]:
            raise RuntimeError(
                "Set DATABRICKS_ACCESS_TOKEN or both DATABRICKS_CLIENT_ID and "
                "DATABRICKS_CLIENT_SECRET"
            )
        if self._oauth_token and time.time() < self._oauth_expires_at:
            return self._oauth_token
        response = requests.post(
            f"{c['host']}/oidc/v1/token",
            auth=(c["client_id"], c["client_secret"]),
            data={"grant_type": "client_credentials", "scope": "all-apis"},
            timeout=30,
        )
        response.raise_for_status()
        body = response.json()
        token = body.get("access_token")
        if not token:
            raise RuntimeError("Databricks OAuth response did not contain access_token")
        self._oauth_token = token
        self._oauth_expires_at = time.time() + max(60, int(body.get("expires_in", 3600)) - 60)
        return token

    def capabilities(self) -> Dict[str, str]:
        return {
            "vendor_native_semantic_model": "native",
            "metric_aggregation": "native",
            "single_column_distinct": "native",
            "composite_distinct_include_nulls": "unsupported_by_base_compiler",
            "iso_week_calendar": "equivalent_lowering",
            "non_additive_rollup": "contract_guard",
            "runtime_query_api": "native",
        }

    @staticmethod
    def _lit(v: str) -> str:
        if v == "":
            return "NULL"
        return "'" + v.replace("'", "''") + "'"

    def _statement(self, sql: str) -> Dict[str, Any]:
        c = self._cfg()
        headers = {"Authorization": f"Bearer {self._access_token()}", "Content-Type": "application/json"}
        payload = {
            "warehouse_id": c["warehouse_id"],
            "statement": sql,
            "wait_timeout": "50s",
            "on_wait_timeout": "CONTINUE",
        }
        r = requests.post(f"{c['host']}/api/2.0/sql/statements", headers=headers, json=payload, timeout=60)
        r.raise_for_status()
        body = r.json()
        statement_id = body.get("statement_id")
        while body.get("status", {}).get("state") in {"PENDING", "RUNNING"}:
            time.sleep(1)
            rr = requests.get(f"{c['host']}/api/2.0/sql/statements/{statement_id}", headers=headers, timeout=30)
            rr.raise_for_status()
            body = rr.json()
        state = body.get("status", {}).get("state")
        if state not in {"SUCCEEDED", None}:
            raise RuntimeError(json.dumps(body, indent=2))
        columns = [x.get("name") for x in body.get("manifest", {}).get("schema", {}).get("columns", [])]
        rows = body.get("result", {}).get("data_array", [])
        return {"columns": columns, "rows": rows, "raw": body}

    def _table_name(self) -> str:
        c = self._cfg()
        return ".".join(f"`{part.replace('`', '``')}`" for part in (c["catalog"], c["schema"], c["table"]))

    def _view_name(self) -> str:
        c = self._cfg()
        return ".".join(f"`{part.replace('`', '``')}`" for part in (c["catalog"], c["schema"], c["view"]))

    def metric_yaml(self) -> str:
        source = self._table_name()
        fields = [
            {"name": "order_date", "expr": "order_date"},
            {"name": "region", "expr": "region"},
            {"name": "warehouse_id", "expr": "warehouse_id"},
            {"name": "product_id", "expr": "product_id"},
            {"name": "order_status", "expr": "order_status"},
            {"name": "month", "expr": "DATE_TRUNC('MONTH', order_date)"},
            {"name": "iso_week_year", "expr": "EXTRACT(YEAROFWEEK FROM order_date)"},
            {"name": "iso_week", "expr": "EXTRACT(WEEK FROM order_date)"},
        ]
        measures = []
        for name, metric in self.contract["metrics"].items():
            measures.append({
                "name": name,
                "expr": compile_sql_metric(metric, self.contract, dialect="databricks"),
                "comment": metric.get("description", ""),
            })
        payload = {
            "version": "1.1",
            "comment": "Generated from vendor-neutral Semantics-as-Code conformance contract",
            "source": source,
            "fields": fields,
            "measures": measures,
        }
        return yaml.safe_dump(payload, sort_keys=False)

    def compile(self, output_dir: Path) -> Dict[str, Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        yml = output_dir / "databricks_metric_view.yaml"
        sql = output_dir / "databricks_deploy.sql"
        yml.write_text(self.metric_yaml(), encoding="utf-8")
        sql.write_text(
            f"CREATE OR REPLACE VIEW {self._view_name()} WITH METRICS LANGUAGE YAML AS\n$$\n{self.metric_yaml()}$$;\n",
            encoding="utf-8",
        )
        return {"yaml": yml, "sql": sql}

    def provision_and_deploy(self) -> Dict[str, Any]:
        c = self._cfg()
        catalog = f"`{c['catalog'].replace('`', '``')}`"
        schema = f"`{c['schema'].replace('`', '``')}`"
        self._statement(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{schema}")
        table = self._table_name()
        self._statement(f"""
        CREATE OR REPLACE TABLE {table} (
          order_id BIGINT,
          order_date DATE,
          customer_id STRING,
          product_id STRING,
          region STRING,
          warehouse_id STRING,
          order_status STRING,
          ordered_quantity BIGINT,
          fulfilled_quantity BIGINT,
          net_sales_amount DECIMAL(18,2),
          cost_of_goods_sold DECIMAL(18,2),
          inventory_value DECIMAL(18,2)
        ) USING DELTA
        """)
        rows = list(csv.DictReader(self.fixture_path.open(encoding="utf-8")))
        vals = []
        numeric = {"order_id", "ordered_quantity", "fulfilled_quantity", "net_sales_amount", "cost_of_goods_sold", "inventory_value"}
        for row in rows:
            parts = []
            for k in row:
                v = row[k]
                if v == "":
                    parts.append("NULL")
                elif k in numeric:
                    parts.append(v)
                else:
                    parts.append(self._lit(v))
            vals.append("(" + ",".join(parts) + ")")
        self._statement(f"INSERT INTO {table} VALUES " + ",\n".join(vals))
        self._statement(f"CREATE OR REPLACE VIEW {self._view_name()} WITH METRICS LANGUAGE YAML AS $$\n{self.metric_yaml()}$$")
        return {"table": table, "metric_view": self._view_name(), "rows": len(rows)}

    def _query_metric(self, metric: str, dimensions: list[str], filters: list[dict]) -> Dict[str, Any]:
        view = self._view_name()
        select = []
        group = []
        for d in dimensions:
            select.append(d)
            group.append(d)
        select.append(f"MEASURE({metric}) AS value")
        sql = f"SELECT {', '.join(select)} FROM {view}"
        if filters:
            sql += " WHERE " + " AND ".join(sql_filter(f) for f in filters)
        if group:
            sql += " GROUP BY " + ", ".join(group)
        sql += " ORDER BY " + ", ".join(group) if group else ""
        return {"sql": sql, "result": self._statement(sql)}

    def execute_queries(self, queries: Dict[str, Any]) -> Dict[str, Any]:
        out = {}
        for q in queries["queries"]:
            qid = q["id"]
            if "metric" in q:
                out[qid] = self._query_metric(q["metric"], q.get("dimensions", []), q.get("filters", []))
            elif q.get("probe") == "iso_week_partition":
                sql = f"""
                SELECT iso_week_year, iso_week, COUNT(*) AS value
                FROM {self._view_name()}
                WHERE order_status = 'Completed'
                GROUP BY iso_week_year, iso_week
                ORDER BY iso_week_year, iso_week
                """
                out[qid] = {"sql": sql, "result": self._statement(sql)}
            elif q.get("probe") == "fill_rate_rollup":
                sql = f"""
                SELECT order_date,
                       MEASURE(fill_rate) AS daily_fill_rate
                FROM {self._view_name()}
                WHERE order_status = 'Completed'
                GROUP BY order_date
                ORDER BY order_date
                """
                out[qid] = {"sql": sql, "result": self._statement(sql)}
        return out
