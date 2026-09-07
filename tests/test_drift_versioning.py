from pathlib import Path

from saccloud.contract import load_yaml
from saccloud.drift import mutate
from saccloud.versioning import compare_contracts

ROOT = Path(__file__).resolve().parents[1]


def test_formula_change_is_major():
    base = load_yaml(ROOT / "contracts" / "semantic_contract.yaml")
    head = mutate(base, "fill_rate_formula_change")
    assert compare_contracts(base, head)["recommended_bump"] == "major"


def test_governance_access_change_is_major():
    base = load_yaml(ROOT / "contracts" / "semantic_contract.yaml")
    head = mutate(base, "revoke_reader")
    assert compare_contracts(base, head)["recommended_bump"] == "major"
