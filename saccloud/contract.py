from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict

import yaml


def load_yaml(path: str | Path) -> Dict[str, Any]:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def sha256_obj(obj: Any) -> str:
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def validate_contract(contract: Dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key in ["package", "execution", "governance", "source", "metrics"]:
        if key not in contract:
            errors.append(f"missing top-level key: {key}")
    pkg = contract.get("package", {})
    if not pkg.get("id"):
        errors.append("package.id is required")
    if not pkg.get("version"):
        errors.append("package.version is required")
    execution = contract.get("execution", {})
    if execution.get("null_policy") not in {"propagate", "coalesce_zero"}:
        errors.append("execution.null_policy must be propagate or coalesce_zero")
    if execution.get("empty_set") not in {"null", "zero"}:
        errors.append("execution.empty_set must be null or zero")
    if execution.get("divide_by_zero") not in {"null", "zero", "error"}:
        errors.append("execution.divide_by_zero must be null, zero, or error")
    time = execution.get("time", {})
    if time.get("calendar") not in {"iso8601", "gregorian"}:
        errors.append("execution.time.calendar must be iso8601 or gregorian")
    tol = execution.get("tolerance", {})
    if "abs" not in tol or "rel" not in tol:
        errors.append("execution.tolerance.abs and .rel are required")
    metrics = contract.get("metrics", {})
    if not metrics:
        errors.append("at least one metric is required")
    for name, metric in metrics.items():
        for req in ["description", "grain", "expression", "aggregation"]:
            if req not in metric:
                errors.append(f"metric {name}: missing {req}")
    return errors


def business_review_status(contract: Dict[str, Any]) -> dict[str, Any]:
    review = contract.get("review", {})
    required = set(review.get("required_roles", []))
    approvals = {
        a.get("role"): a
        for a in review.get("approvals", [])
        if a.get("status") == "approved" and a.get("role")
    }
    missing = sorted(required - set(approvals))
    return {
        "status": review.get("status", "draft"),
        "required_roles": sorted(required),
        "approved_roles": sorted(approvals),
        "missing_roles": missing,
        "gate_pass": review.get("status") == "approved" and not missing,
    }
