# Databricks authenticated runtime test

## What this proves

The same vendor-neutral contract is compiled into a Unity Catalog Metric View, the canonical fixture is loaded into a Delta table, and the ten query intents are executed through the native Metric View runtime using `MEASURE()`.

## Prerequisites

- Unity Catalog-enabled Databricks workspace.
- SQL warehouse/runtime that supports Metric Views.
- A catalog where your user can create a schema/table/view.
- Personal access token (or compatible bearer token).

Official docs:

- https://docs.databricks.com/aws/en/uc-semantics/metric-views/create
- https://docs.databricks.com/aws/en/uc-semantics/metric-views/query

## 1. Collect connection values

In Databricks SQL, open the SQL Warehouse > Connection details and copy:

- Server hostname
- HTTP path

Create a PAT from User Settings > Developer > Access tokens (or use your organization's approved auth method).

## 2. Configure `.env`

Copy `.env.example` to `.env` and set:

```text
DATABRICKS_SERVER_HOSTNAME=https://<workspace-host>
DATABRICKS_HTTP_PATH=/sql/1.0/warehouses/<warehouse-id>
# Use either a PAT...
DATABRICKS_ACCESS_TOKEN=<token>
# ...or OAuth M2M credentials (leave the PAT empty).
DATABRICKS_CLIENT_ID=<service-principal-client-id>
DATABRICKS_CLIENT_SECRET=<service-principal-client-secret>
DATABRICKS_CATALOG=<catalog>
DATABRICKS_SCHEMA=sac_conformance
DATABRICKS_TABLE=sac_fact
DATABRICKS_METRIC_VIEW=sac_metrics
```

## 3. Preflight

```bash
python scripts/00_preflight.py databricks
```

This must finish with `PRECHECK PASSED`.

## 4. Compile and inspect the artifact

```bash
python scripts/03_compile_artifacts.py
```

Inspect:

- `generated/databricks/databricks_metric_view.yaml`
- `generated/databricks/databricks_deploy.sql`

## 5. Deploy and run all queries

```bash
python scripts/05_run_platform.py databricks --deploy
python scripts/11_runtime_query_validation.py databricks
```

The deploy command creates/replaces only the configured `sac_fact` table and `sac_metrics` Metric View in the configured schema.

## 6. Evidence produced

- `results/databricks_deployment.json`
- `results/databricks_raw.json` — exact native SQL + raw responses
- `results/databricks.json` — normalized observations
- `observability/events.ndjson`

## 7. Compare against reference contract

After Snowflake/Fabric are run too (or independently at any time):

```bash
python scripts/06_compare_results.py
```

## If Metric View creation fails

Record the full error. Also record:

```sql
SELECT current_version();
SELECT current_catalog(), current_schema(), current_user();
```

A deployment rejection is evidence; do not replace it with equivalent hand-written SQL for the paper's primary test.
