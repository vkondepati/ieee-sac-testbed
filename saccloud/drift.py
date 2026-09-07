from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict

from .contract import sha256_obj


def fingerprint(contract: Dict[str, Any], compiled_artifact_hashes: Dict[str, str] | None = None, source_schema: Dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "contract_hash": sha256_obj(contract),
        "source_schema_hash": sha256_obj(source_schema or contract.get("source", {}).get("columns", {})),
        "artifacts": compiled_artifact_hashes or {},
    }


def classify_change(path: str) -> str:
    semantic_prefixes = (
        "metrics.", "execution.null_policy", "execution.empty_set", "execution.divide_by_zero",
        "execution.distinct", "execution.time", "governance.access",
    )
    if path.startswith(semantic_prefixes):
        return "semantic"
    if path.startswith(("source.columns",)):
        return "source_schema"
    if path.startswith(("review", "governance.owner", "governance.steward")):
        return "governance_metadata"
    return "metadata"


def mutate(contract: Dict[str, Any], scenario: str) -> Dict[str, Any]:
    c = deepcopy(contract)
    if scenario == "empty_set_zero":
        c["execution"]["empty_set"] = "zero"
    elif scenario == "calendar_gregorian":
        c["execution"]["time"]["calendar"] = "gregorian"
    elif scenario == "fill_rate_avg_rollup":
        c["metrics"]["fill_rate"]["aggregation"]["rollup"] = "average"
    elif scenario == "fill_rate_formula_change":
        c["metrics"]["fill_rate"]["expression"]["denominator"]["expr"]["name"] = "fulfilled_quantity"
    elif scenario == "revoke_reader":
        c["governance"]["access"]["query_roles"] = ["semantic_admin"]
    elif scenario == "source_ordered_quantity_decimal":
        c["source"]["columns"]["ordered_quantity"] = "decimal"
    else:
        raise ValueError(scenario)
    return c
