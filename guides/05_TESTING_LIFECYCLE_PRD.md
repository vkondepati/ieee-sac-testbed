# PRD: Semantic Testing Lifecycle Completion

## 1. Purpose

Complete the remaining empirical testing lifecycle for the semantics-as-code kit after the Microsoft Fabric runtime baseline has passed.

The lifecycle must produce reproducible evidence for:

1. Cross-platform comparison.
2. Semantic drift detection.
3. Access governance.
4. Observability and versioning.
5. Paper-results export.

The test program must preserve observed states. `NOT_RUN`, `UNSUPPORTED`, deployment failure, and runtime-query failure are valid results and must not be replaced with inferred values.

## 2. Current Baseline

Microsoft Fabric has a successful baseline for the eight requested probes:

- Overall Fill Rate: `0.64`
- Gross Margin: `500`
- Fill Rate by region: `East 0.848485; North 0.736842; West 0.458333`
- Monthly Fill Rate: `Dec 0.625; Jan 0.62; Feb 0.80`
- ISO week buckets: `W52:1; W01:4; W02:3; W05:2; W06:1`
- Empty Revenue: `NULL`
- Inventory Turnover: `1.76102088`
- Unique Customers: `6`

Baseline evidence:

- `results/fabric.json`
- `results/fabric_raw.json`
- `results/fabric_deployment.json`
- `observability/events.ndjson`

## 3. Preconditions

- Python virtual environment is active.
- `.env` contains valid credentials for each platform under test.
- Azure CLI is installed and authenticated for Fabric.
- The canonical fixture is unchanged at `data/fixture.csv`.
- Each platform preflight passes before deployment.
- Tests that mutate contracts or permissions use an isolated schema, model, identity, or a documented restore step.

Run the local contract and unit checks first:

```powershell
.\.venv\Scripts\python.exe scripts\01_validate_definition.py
.\.venv\Scripts\python.exe scripts\03_compile_artifacts.py
.\.venv\Scripts\python.exe scripts\04_run_reference.py
.\.venv\Scripts\python.exe -m pytest
```

## 4. Workstream A: Cross-Platform Comparison

### Objective

Measure whether Databricks, Snowflake, and Fabric preserve the same observable results as the independent reference evaluator.

### Execution

Run preflight and runtime validation only for platforms with configured credentials:

```powershell
.\.venv\Scripts\python.exe scripts\00_preflight.py databricks
.\.venv\Scripts\python.exe scripts\05_run_platform.py databricks --deploy
.\.venv\Scripts\python.exe scripts\11_runtime_query_validation.py databricks

.\.venv\Scripts\python.exe scripts\00_preflight.py snowflake
.\.venv\Scripts\python.exe scripts\05_run_platform.py snowflake --deploy
.\.venv\Scripts\python.exe scripts\11_runtime_query_validation.py snowflake

.\.venv\Scripts\python.exe scripts\00_preflight.py fabric
.\.venv\Scripts\python.exe scripts\05_run_platform.py fabric --deploy
.\.venv\Scripts\python.exe scripts\11_runtime_query_validation.py fabric
```

Then compare all available platform results:

```powershell
.\.venv\Scripts\python.exe scripts\06_compare_results.py
```

### Evidence

- `results/reference.json`
- `results/databricks.json`
- `results/snowflake.json`
- `results/fabric.json`
- `results/conformance_summary.json`
- `results/conformance_summary.csv`
- `results/*_raw.json`
- `results/*_deployment.json`

### Acceptance criteria

- Every executed supported probe has a comparator verdict.
- `CONFORM` means the normalized platform result is within contract tolerance.
- Deployment and query failures are recorded separately from numeric divergence.
- Unsupported probes include a capability explanation.

## 5. Workstream B: Semantic Drift Tests

### Objective

Verify that intentional contract changes are detected, versioned, and not silently accepted as equivalent semantics.

### Required scenarios

At minimum, execute these end to end on every available platform:

- `empty_set_zero`
- `calendar_gregorian`
- `fill_rate_formula_change`

For complete coverage, also execute:

- `fill_rate_avg_rollup`
- `revoke_reader`
- `source_ordered_quantity_decimal`

Generate each mutation:

```powershell
.\.venv\Scripts\python.exe scripts\07_inject_semantic_drift.py empty_set_zero
.\.venv\Scripts\python.exe scripts\07_inject_semantic_drift.py calendar_gregorian
.\.venv\Scripts\python.exe scripts\07_inject_semantic_drift.py fill_rate_formula_change
.\.venv\Scripts\python.exe scripts\07_inject_semantic_drift.py fill_rate_avg_rollup
.\.venv\Scripts\python.exe scripts\07_inject_semantic_drift.py revoke_reader
.\.venv\Scripts\python.exe scripts\07_inject_semantic_drift.py source_ordered_quantity_decimal
```

For each scenario, record:

- Base and mutated contract hashes.
- Version recommendation.
- Deployment outcome.
- Runtime result change.
- Comparator verdict.
- Detection stage.
- Time to detection.

### Acceptance criteria

- Every mutation produces a distinct mutated contract hash.
- The versioning recommendation matches the semantic impact.
- A deliberate semantic change is either detected as divergent or rejected at the appropriate deployment/governance gate.
- No mutated run overwrites the baseline evidence.

Evidence files are `results/drift_<scenario>.json` and `results/drift_<scenario>.yaml`, plus isolated platform result and observability records.

## 6. Workstream C: Access Governance

### Objective

Verify that authorized principals can execute semantic queries and unauthorized principals are denied.

First print the contract governance matrix:

```powershell
.\.venv\Scripts\python.exe scripts\10_access_governance.py
```

Validate the contract expectation for representative roles:

```powershell
.\.venv\Scripts\python.exe scripts\10_access_governance.py --role semantic_reader --action query --observed allow
.\.venv\Scripts\python.exe scripts\10_access_governance.py --role sales_analyst --action query --observed deny
```

Then perform live tests:

- Databricks: grant and revoke access to the Metric View or schema.
- Snowflake: grant and revoke access to the Semantic View and required database/schema objects.
- Fabric: grant and remove semantic-model Build/read permission, or use a separate test identity.

Run the same query intent for each authorized and unauthorized state. Record only allow/deny outcomes and the platform error status; do not store credentials or access tokens.

### Acceptance criteria

- Authorized access is `allow`.
- Unauthorized access is `deny`.
- Any mismatch is reported as `DIVERGENT`.
- Governance failures are not counted as metric divergences.

Record results in `templates/governance_results.csv`.

## 7. Workstream D: Observability and Versioning

### Objective

Demonstrate that each run can be reproduced and that contract changes have an auditable version recommendation.

Generate the observability summary:

```powershell
.\.venv\Scripts\python.exe scripts\08_observability_report.py
```

Check each mutation explicitly when needed:

```powershell
.\.venv\Scripts\python.exe scripts\09_versioning_check.py results/drift_empty_set_zero.yaml
.\.venv\Scripts\python.exe scripts\09_versioning_check.py results/drift_calendar_gregorian.yaml
.\.venv\Scripts\python.exe scripts\09_versioning_check.py results/drift_fill_rate_formula_change.yaml
```

### Required run metadata

For every platform and scenario retain:

- UTC timestamp.
- Contract SHA-256.
- Fixture SHA-256.
- Generated artifact SHA-256.
- Platform and runtime metadata.
- Exact SQL or DAX.
- Raw and normalized results.
- Deployment and query errors.
- Comparator verdict.

### Acceptance criteria

- `results/observability_summary.json` is generated.
- `observability/events.ndjson` contains run, deployment, result, and error events as applicable.
- Version recommendations are recorded for every injected scenario.
- No secret value appears in results, generated artifacts, or observability logs.

## 8. Workstream E: Paper-Results Export

### Objective

Create the paper-ready conformance table without filling missing evidence with assumptions.

Run after comparison, drift, governance, and observability work is complete:

```powershell
.\.venv\Scripts\python.exe scripts\12_export_paper_results.py
```

### Outputs

- `results/paper_runtime_results.csv`
- `results/conformance_summary.csv`
- `results/observability_summary.json`
- `templates/drift_results.csv`
- `templates/governance_results.csv`

### Acceptance criteria

- The export contains reference values, available platform values, and verdicts.
- Missing platform runs remain blank or `NOT_RUN`.
- Unsupported capability results remain `UNSUPPORTED`.
- Deployment and runtime failures are reported separately from metric divergence.
- The export can be traced back to the raw platform result files.

## 9. Final Evidence Package

Before sharing results, confirm that the package contains:

```text
results/
generated/
observability/
templates/drift_results.csv
templates/governance_results.csv
.env.example
```

Do not include `.env`, passwords, client secrets, access tokens, or other credentials.

The lifecycle is complete only when the cross-platform comparison, required drift scenarios, governance tests, observability/versioning checks, and paper export each have either accepted evidence or an explicitly documented `NOT_RUN`, `UNSUPPORTED`, or failure status.
