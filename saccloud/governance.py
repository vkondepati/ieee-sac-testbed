from __future__ import annotations

from typing import Any, Dict


def expected_access(contract: Dict[str, Any], role: str, action: str) -> bool:
    mapping = {
        "discover": "discover_roles",
        "query": "query_roles",
        "administer": "administer_roles",
    }
    if action not in mapping:
        raise ValueError(action)
    return role in contract["governance"]["access"].get(mapping[action], [])


def governance_matrix(contract: Dict[str, Any], roles: list[str]) -> list[dict[str, Any]]:
    return [
        {"role": role, **{a: expected_access(contract, role, a) for a in ["discover", "query", "administer"]}}
        for role in roles
    ]
