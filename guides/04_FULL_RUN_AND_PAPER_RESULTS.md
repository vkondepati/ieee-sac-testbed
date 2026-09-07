# Full three-platform run and paper-result workflow

## 1. Local environment
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env
```
Fill `.env` for Databricks, Snowflake and Fabric.

## 2. Validate the vendor-neutral contract
```bash
python scripts/01_validate_definition.py
python scripts/03_compile_artifacts.py
python scripts/04_run_reference.py
pytest -q
```

## 3. Run connectivity prechecks
```bash
python scripts/00_preflight.py databricks
python scripts/00_preflight.py snowflake
python scripts/00_preflight.py fabric
```
Do not proceed with a platform until its preflight passes.

## 4. Run the three authenticated native semantic runtimes
```bash
python scripts/05_run_platform.py databricks --deploy
python scripts/11_runtime_query_validation.py databricks

python scripts/05_run_platform.py snowflake --deploy
python scripts/11_runtime_query_validation.py snowflake

python scripts/05_run_platform.py fabric --deploy
python scripts/11_runtime_query_validation.py fabric
```

## 5. Calculate semantic conformance
```bash
python scripts/06_compare_results.py
python scripts/08_observability_report.py
python scripts/12_export_paper_results.py
```

Primary files for the paper:
- `results/reference.json`
- `results/databricks.json`
- `results/snowflake.json`
- `results/fabric.json`
- `results/conformance_summary.csv`
- `results/paper_runtime_results.csv`
- `results/*_deployment.json`
- `results/*_raw.json`
- `observability/events.ndjson`

## 6. Paper metrics
Calculate from `conformance_summary.csv`:
- **Native Conformance Rate** = CONFORM / executed supported probes
- **Effective Portability Rate** = (CONFORM + CONFORM_AFTER_LOWERING) / executed supported probes
- **Divergence Rate** = DIVERGENT / executed supported probes
- **Unsupported Rate** = UNSUPPORTED / all attempted probes

Do not count deployment or query failures as numeric divergences. Report them separately as deployability/runtime-query-validity results.

## 7. Drift tests
The baseline artifact includes six deterministic mutations. Generate them:
```bash
python scripts/07_inject_semantic_drift.py empty_set_zero
python scripts/07_inject_semantic_drift.py calendar_gregorian
python scripts/07_inject_semantic_drift.py fill_rate_avg_rollup
python scripts/07_inject_semantic_drift.py fill_rate_formula_change
python scripts/07_inject_semantic_drift.py revoke_reader
python scripts/07_inject_semantic_drift.py source_ordered_quantity_decimal
```

For the strongest paper evidence, execute at least these three end-to-end on all available platforms:
1. `empty_set_zero` — contract-only semantic change.
2. `calendar_gregorian` — time/calendar semantic change.
3. `fill_rate_formula_change` — business-definition change.

For each mutation, use an isolated schema/model or restore the baseline afterward. Record:
- contract hash before/after
- expected version bump
- deployment result
- runtime result change
- comparator verdict
- detection stage
- elapsed time to detection

## 8. Access-governance tests
Use the same query intent with an authorized and unauthorized principal/role per platform. Record only observable allow/deny outcomes, not vendor ACL syntax equivalence.

Databricks: grant/revoke `SELECT` on the Metric View or schema to a test principal.
Snowflake: grant/revoke `SELECT` on the Semantic View plus required database/schema usage.
Fabric: grant/remove semantic-model Build/read permission (or use a separate test identity); then execute the DAX query through the API.

## 9. Runtime observability evidence
For every platform retain:
- UTC run timestamp
- contract SHA-256
- fixture SHA-256
- generated artifact SHA-256
- platform/runtime version or service metadata available at run time
- exact native SQL/DAX
- raw result
- normalized result
- comparator verdict
- deployment/query error if any

These are necessary to make semantic drift diagnosable after managed services evolve.

## 10. What to send back for the final paper
Zip the following after all runs:
```text
results/
generated/
observability/
.env.example        (NOT your .env)
```
Never include access tokens, passwords or client secrets.
