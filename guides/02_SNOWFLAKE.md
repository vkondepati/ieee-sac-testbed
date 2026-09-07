# Snowflake authenticated runtime test

## What this proves
The vendor-neutral contract is compiled into a native Snowflake Semantic View over the identical canonical fixture, then queried through the Semantic View runtime using `AGG(metric)`.

Official docs:
- https://docs.snowflake.com/en/sql-reference/sql/create-semantic-view
- https://docs.snowflake.com/en/user-guide/views-semantic/querying

## 1. Prepare isolated test objects
You may use existing objects or run `platform_setup/snowflake_bootstrap.sql` with an appropriately privileged role.

Suggested names:
- warehouse: `SAC_TEST_WH`
- database: `SAC_TEST_DB`
- schema: `SAC_CONFORMANCE`

## 2. Configure `.env`
```text
SNOWFLAKE_ACCOUNT=<account identifier>
SNOWFLAKE_USER=<username>
SNOWFLAKE_PASSWORD=<password>
SNOWFLAKE_WAREHOUSE=SAC_TEST_WH
SNOWFLAKE_DATABASE=SAC_TEST_DB
SNOWFLAKE_SCHEMA=SAC_CONFORMANCE
SNOWFLAKE_TABLE=SAC_FACT
SNOWFLAKE_SEMANTIC_VIEW=SAC_METRICS
SNOWFLAKE_ROLE=<optional role>
```

## 3. Preflight
```bash
python scripts/00_preflight.py snowflake
```

## 4. Compile and inspect
```bash
python scripts/03_compile_artifacts.py
```
Inspect `generated/snowflake/snowflake_semantic_view.sql`.

## 5. Deploy and execute
```bash
python scripts/05_run_platform.py snowflake --deploy
python scripts/11_runtime_query_validation.py snowflake
```

## 6. Evidence produced
- `results/snowflake_deployment.json`
- `results/snowflake_raw.json` — exact SQL and raw values
- `results/snowflake.json` — normalized observations
- `observability/events.ndjson`

## 7. Compare
```bash
python scripts/06_compare_results.py
```

## Record runtime metadata
Run this in Snowsight and save the output with the experiment:
```sql
SELECT CURRENT_VERSION(), CURRENT_ACCOUNT(), CURRENT_REGION(), CURRENT_USER(), CURRENT_ROLE(), CURRENT_WAREHOUSE();
```
If Semantic View creation or a query is rejected, retain the exact error as a portability result rather than replacing it with ordinary SQL.
