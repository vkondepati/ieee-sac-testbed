from decimal import Decimal
from pathlib import Path

from saccloud.contract import load_yaml
from saccloud.reference_evaluator import evaluate_all

ROOT = Path(__file__).resolve().parents[1]


def test_reference_headline_values():
    c = load_yaml(ROOT / "contracts" / "semantic_contract.yaml")
    q = load_yaml(ROOT / "queries" / "query_intents.yaml")
    out = evaluate_all(c, ROOT / "data" / "fixture.csv", q)
    assert out["Q01_overall_fill_rate"][0]["value"] == Decimal("0.64")
    assert out["Q02_gross_margin"][0]["value"] == Decimal("500.00")
    assert out["Q06_empty_population_revenue"][0]["value"] is None
    assert out["Q08_unique_customers"][0]["value"] == Decimal("6")


def test_rollup_is_non_additive():
    c = load_yaml(ROOT / "contracts" / "semantic_contract.yaml")
    q = load_yaml(ROOT / "queries" / "query_intents.yaml")
    out = evaluate_all(c, ROOT / "data" / "fixture.csv", q)["Q10_nonadditive_rollup_check"]
    assert out["monthly_recompute"]["2026-01"] == Decimal("0.62")
    assert out["monthly_average_daily"]["2026-01"] == Decimal("0.66")
