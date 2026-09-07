from __future__ import annotations

import base64
import json
import os
import re
import shutil
import time
import subprocess
from pathlib import Path
from typing import Any, Dict

import requests

from .base import PlatformAdapter
from ..compiler import compile_dax_metric


class FabricAdapter(PlatformAdapter):
    name = "fabric"

    def _cfg(self):
        return {
            "tenant": os.getenv("FABRIC_TENANT_ID", "YOUR_TENANT_ID"),
            "client": os.getenv("FABRIC_CLIENT_ID", "YOUR_CLIENT_ID"),
            "secret": os.getenv("FABRIC_CLIENT_SECRET", ""),
            "workspace": os.getenv("FABRIC_WORKSPACE_ID", "YOUR_WORKSPACE_ID"),
            "model": os.getenv("FABRIC_SEMANTIC_MODEL_ID", "YOUR_SEMANTIC_MODEL_ID"),
            "table": os.getenv("FABRIC_TABLE_NAME", "SaCFact"),
            "apply": os.getenv("FABRIC_APPLY_TMDL", "false").lower() == "true",
            "impersonated_upn": os.getenv("FABRIC_IMPERSONATED_UPN") or None,
        }

    def capabilities(self) -> Dict[str, str]:
        return {
            "vendor_native_semantic_model": "native",
            "metric_aggregation": "native_dax",
            "single_column_distinct": "native",
            "composite_distinct_include_nulls": "equivalent_lowering_possible",
            "iso_week_calendar": "equivalent_lowering_via_calculated_columns",
            "non_additive_rollup": "equivalent_lowering_via_measure",
            "runtime_query_api": "native_dax_api",
        }

    def _token(self, scope: str) -> str:
        c = self._cfg()
        auth_mode = os.getenv("FABRIC_AUTH_MODE", "azure_cli").lower()
        if auth_mode == "azure_cli":
            az_executable = shutil.which("az")
            if not az_executable:
                raise RuntimeError("Azure CLI not found; install it and run 'az login' first.")
            if scope.startswith("https://api.fabric.microsoft.com"):
                resource = "https://api.fabric.microsoft.com"
            elif scope.startswith("https://analysis.windows.net/powerbi/api"):
                resource = "https://analysis.windows.net/powerbi/api"
            else:
                resource = scope.replace("/.default", "")
            proc = subprocess.run(
                [az_executable, "account", "get-access-token", "--resource", resource, "--query", "accessToken", "-o", "tsv"],
                capture_output=True, text=True
            )
            if proc.returncode != 0:
                raise RuntimeError(
                    "Azure CLI authentication failed. Run 'az login' first or set FABRIC_AUTH_MODE=service_principal.\n"
                    + proc.stderr
                )
            return proc.stdout.strip()

        if auth_mode == "service_principal":
            import msal
            if not c["client"] or not c["secret"] or "YOUR_" in c["client"]:
                raise RuntimeError("FABRIC_CLIENT_ID and FABRIC_CLIENT_SECRET are required for service_principal auth")
            app = msal.ConfidentialClientApplication(
                c["client"], authority=f"https://login.microsoftonline.com/{c['tenant']}", client_credential=c["secret"]
            )
            result = app.acquire_token_for_client(scopes=[scope])
            if "access_token" not in result:
                raise RuntimeError(json.dumps(result, indent=2))
            return result["access_token"]

        raise RuntimeError("FABRIC_AUTH_MODE must be azure_cli or service_principal")

    def tmdl_fragment(self) -> str:
        table = self._cfg()["table"]
        lines = [f"ref table {table}"]
        lines += [
            "\tcolumn month",
            "\t\tdataType: dateTime",
            "\t\tsummarizeBy: none",
            "\t\tsourceColumn: month",
            "\tcolumn iso_week",
            "\t\tdataType: int64",
            "\t\tsummarizeBy: none",
            "\t\tsourceColumn: iso_week",
            "\tcolumn iso_week_year",
            "\t\tdataType: int64",
            "\t\tsummarizeBy: none",
            "\t\tsourceColumn: iso_week_year",
        ]
        for name, metric in self.contract["metrics"].items():
            dax = compile_dax_metric(metric, self.contract, table=table)
            lines += [
                f"\tmeasure {name} = {dax}",
                "\t\tformatString: 0.000000",
            ]
        return "\n".join(lines) + "\n"

    def compile(self, output_dir: Path) -> Dict[str, Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        tmdl = output_dir / "fabric_measures_patch.tmdl"
        tmdl.write_text("createOrReplace\n\n" + self.tmdl_fragment(), encoding="utf-8")
        dax_map = {name: compile_dax_metric(metric, self.contract, table=self._cfg()["table"]) for name, metric in self.contract["metrics"].items()}
        p = output_dir / "fabric_measure_map.json"
        p.write_text(json.dumps(dax_map, indent=2), encoding="utf-8")
        return {"tmdl": tmdl, "measure_map": p}

    def _fabric_headers(self):
        return {"Authorization": f"Bearer {self._token('https://api.fabric.microsoft.com/.default')}", "Content-Type": "application/json"}

    def _get_definition(self) -> Dict[str, Any]:
        c = self._cfg()
        url = f"https://api.fabric.microsoft.com/v1/workspaces/{c['workspace']}/semanticModels/{c['model']}/getDefinition?format=TMDL"
        r = requests.post(url, headers=self._fabric_headers(), timeout=60)
        if r.status_code == 202:
            loc = r.headers["Location"]
            while True:
                time.sleep(int(r.headers.get("Retry-After", "2")))
                rr = requests.get(loc, headers=self._fabric_headers(), timeout=60)
                if rr.status_code == 200:
                    operation = rr.json()
                    if operation.get("status") == "Succeeded":
                        result_url = loc if loc.rstrip("/").endswith("/result") else loc.rstrip("/") + "/result"
                        result = requests.get(result_url, headers=self._fabric_headers(), timeout=60)
                        result.raise_for_status()
                        return result.json()
                    return operation
                if rr.status_code not in {202}:
                    rr.raise_for_status()
                r = rr
        r.raise_for_status()
        return r.json()

    def _update_definition(self, definition: Dict[str, Any]):
        c = self._cfg()
        url = f"https://api.fabric.microsoft.com/v1/workspaces/{c['workspace']}/semanticModels/{c['model']}/updateDefinition"
        r = requests.post(url, headers=self._fabric_headers(), json={"definition": definition}, timeout=60)
        if r.status_code not in {200, 202}:
            r.raise_for_status()
        operation_id = r.headers.get("x-ms-operation-id")
        if r.status_code == 202 and operation_id:
            operation_url = f"https://api.fabric.microsoft.com/v1/operations/{operation_id}"
            while True:
                time.sleep(int(r.headers.get("Retry-After", "2")))
                r = requests.get(operation_url, headers=self._fabric_headers(), timeout=60)
                r.raise_for_status()
                operation = r.json()
                if operation.get("status") == "Succeeded":
                    break
                if operation.get("status") in {"Failed", "Canceled"}:
                    raise RuntimeError(f"Fabric updateDefinition operation failed: {operation}")
        return {"status_code": r.status_code, "operation": operation_id}

    def provision_and_deploy(self) -> Dict[str, Any]:
        c = self._cfg()
        definition_response = self._get_definition()
        definition = definition_response.get("definition", definition_response)
        parts = definition.get("parts", [])
        target_suffix = f"/tables/{c['table']}.tmdl".lower()
        target = None
        for part in parts:
            if part["path"].lower().endswith(target_suffix):
                target = part
                break
        if not target:
            raise RuntimeError(
                f"Fabric semantic model does not contain definition/tables/{c['table']}.tmdl. "
                "Load data/fixture.csv into a semantic-model table with this exact name before deployment."
            )
        text = base64.b64decode(target["payload"]).decode("utf-8")
        # Remove the first `ref table` line and append only child objects that
        # are not already present, allowing recovery after a partial update.
        fragment_lines = self.tmdl_fragment().splitlines()[1:]
        blocks = []
        current = []
        for line in fragment_lines:
            if line.startswith("\t") and not line.startswith("\t\t"):
                if current:
                    blocks.append(current)
                current = [line]
            elif current:
                current.append(line)
        if current:
            blocks.append(current)
        missing_blocks = []
        metric_names = set(self.contract["metrics"])
        for block in blocks:
            match = re.match(r"\t(column|measure)\s+([^\s=]+)", block[0])
            if match and match.group(1) == "column" and not re.search(rf"(?im)^\s*column\s+'?{re.escape(match.group(2))}'?\s*$", text):
                missing_blocks.append(block)
        additions = [line for block in blocks if re.match(r"\tmeasure\s+([^\s=]+)", block[0]) for line in block]
        retained_lines = []
        current = []
        for line in text.rstrip().splitlines():
            if line.startswith("\t") and not line.startswith("\t\t"):
                if current:
                    retained_lines.extend(current)
                current = [line]
            else:
                current.append(line)
        if current:
            retained_lines.extend(current)
        retained_lines = [
            line for line in retained_lines
        ]
        # Rebuild the table while replacing generated measures in place.
        base_lines = text.rstrip().splitlines()
        filtered = []
        index = 0
        while index < len(base_lines):
            line = base_lines[index]
            if line.startswith("\tmeasure "):
                name = re.match(r"\tmeasure\s+([^\s=]+)", line).group(1)
                index += 1
                while index < len(base_lines) and not (base_lines[index].startswith("\t") and not base_lines[index].startswith("\t\t")):
                    index += 1
                if name in metric_names:
                    continue
                filtered.append(line)
                continue
            filtered.append(line)
            index += 1
        insert_at = next((i for i, line in enumerate(filtered) if line.startswith("\tpartition ")), len(filtered))
        filtered[insert_at:insert_at] = [*([line for block in missing_blocks for line in block]), *additions]
        patched = "\n".join(filtered) + "\n"
        target["payload"] = base64.b64encode(patched.encode("utf-8")).decode("ascii")
        preview_path = Path("generated") / "fabric_patched_table_preview.tmdl"
        preview_path.parent.mkdir(parents=True, exist_ok=True)
        preview_path.write_text(patched, encoding="utf-8")
        if not c["apply"]:
            return {
                "status": "PREVIEW_ONLY",
                "message": "Generated and validated a patch candidate. Review generated/fabric_patched_table_preview.tmdl, then set FABRIC_APPLY_TMDL=true.",
                "preview": str(preview_path),
            }
        result = self._update_definition(definition)
        result.update({"status": "APPLIED", "semantic_model_id": c["model"]})
        return result

    def _execute_dax(self, dax: str) -> Dict[str, Any]:
        c = self._cfg()
        token = self._token("https://analysis.windows.net/powerbi/api/.default")
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        body: Dict[str, Any] = {
            "queries": [{"query": dax}],
            "serializerSettings": {"includeNulls": True},
        }
        if c["impersonated_upn"]:
            body["impersonatedUserName"] = c["impersonated_upn"]
        url = f"https://api.powerbi.com/v1.0/myorg/groups/{c['workspace']}/datasets/{c['model']}/executeQueries"
        r = requests.post(url, headers=headers, json=body, timeout=60)
        if not r.ok:
            raise RuntimeError(f"Power BI Execute Queries failed ({r.status_code}): {r.text}")
        payload = r.json()
        result0 = payload.get("results", [{}])[0]
        tables = result0.get("tables", [])
        rows = tables[0].get("rows", []) if tables else []
        columns = sorted({k for row in rows for k in row.keys()})
        return {"columns": columns, "rows": [[row.get(c) for c in columns] for row in rows], "row_objects": rows, "raw": payload}

    def _metric_query(self, metric: str, dimensions: list[str], filters: list[dict]) -> str:
        table = self._cfg()["table"]
        group_cols = [f"'{table}'[{d}]" for d in dimensions]
        filter_args = []
        for f in filters:
            if f.get("op") != "eq":
                raise NotImplementedError("Fabric draft runner currently supports equality runtime filters")
            val = str(f["value"]).replace('"', '""')
            filter_args.append(f'TREATAS({{"{val}"}}, \'{table}\'[{f["column"]}])')
        args = group_cols + filter_args + [f'"value", [{metric}]']
        return "EVALUATE\nSUMMARIZECOLUMNS(\n    " + ",\n    ".join(args) + "\n)"

    def execute_queries(self, queries: Dict[str, Any]) -> Dict[str, Any]:
        out = {}
        table = self._cfg()["table"]
        for q in queries["queries"]:
            qid = q["id"]
            if "metric" in q:
                dax = self._metric_query(q["metric"], q.get("dimensions", []), q.get("filters", []))
                out[qid] = {"dax": dax, "result": self._execute_dax(dax)}
            elif q.get("probe") == "iso_week_partition":
                dax = f"""EVALUATE
SUMMARIZECOLUMNS(
    '{table}'[iso_week_year],
    '{table}'[iso_week],
    TREATAS({{"Completed"}}, '{table}'[order_status]),
    "value", COUNTROWS('{table}')
)
ORDER BY '{table}'[iso_week_year], '{table}'[iso_week]
"""
                out[qid] = {"dax": dax, "result": self._execute_dax(dax)}
            elif q.get("probe") == "fill_rate_rollup":
                dax = f"""EVALUATE
SUMMARIZECOLUMNS(
    '{table}'[order_date],
    TREATAS({{"Completed"}}, '{table}'[order_status]),
    "daily_fill_rate", [fill_rate]
)
ORDER BY '{table}'[order_date]
"""
                out[qid] = {"dax": dax, "result": self._execute_dax(dax)}
        return out
