# Results to transfer into the draft paper

After running live tests, fill these items before submission:

1. **Deployment portability:** Did the generated Databricks Metric View, Snowflake Semantic View, and Fabric TMDL patch deploy without manual semantic changes? Record compile/deploy errors separately from runtime divergence.
2. **Conformance matrix:** Copy values/verdicts from `results/conformance_summary.csv` and platform JSON files into the paper's primary results table.
3. **Capability negotiation:** For every unsupported test, state whether the platform lacks a native representation, the base adapter lacks a safe lowering, or the contract is under-specified.
4. **Semantic drift:** Run every mutation in `templates/drift_results.csv`; record detection stage and whether the release gate blocked the change.
5. **Observability:** Copy `conformance_rate`, divergence count, and run metadata coverage from `results/observability_summary.json`.
6. **Versioning:** Record whether each injected semantic change produced the expected major/minor/patch recommendation.
7. **Access governance:** Execute the same query under allowed and denied principals/roles on each platform and populate `templates/governance_results.csv`.
8. **Runtime query validation:** Record native SQL/DAX text, row counts, and execution errors from `*_raw.json`.
9. **Environment:** Record platform editions/runtime versions, region, timestamps, adapter commit/hash, and fixture SHA-256.
10. **Do not replace unsupported or failed cells with inferred values.** `UNSUPPORTED`, `N/A`, `NOT_RUN`, and deployment failure are valid empirical results.
