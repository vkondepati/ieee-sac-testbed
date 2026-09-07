#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python scripts/01_validate_definition.py
python scripts/02_business_review_gate.py
python scripts/03_compile_artifacts.py
python scripts/04_run_reference.py
python scripts/10_access_governance.py
pytest -q
printf '\nLocal preparation complete. Next run one or more live platforms, for example:\n'
printf '  python scripts/05_run_platform.py databricks --deploy\n'
printf '  python scripts/05_run_platform.py snowflake --deploy\n'
printf '  python scripts/05_run_platform.py fabric --deploy   # preview first unless FABRIC_APPLY_TMDL=true\n'
printf 'Then run: python scripts/06_compare_results.py\n'
