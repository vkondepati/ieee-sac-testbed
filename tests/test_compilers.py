from pathlib import Path

from saccloud.adapters.databricks import DatabricksAdapter
from saccloud.adapters.fabric import FabricAdapter
from saccloud.adapters.snowflake import SnowflakeAdapter
from saccloud.contract import load_yaml

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = load_yaml(ROOT / "contracts" / "semantic_contract.yaml")
FIXTURE = ROOT / "data" / "fixture.csv"


def test_databricks_compiles_metric_view():
    text = DatabricksAdapter(CONTRACT, FIXTURE).metric_yaml()
    assert "fill_rate" in text
    assert "YEAROFWEEK" in text
    assert "NULLIF" in text


def test_snowflake_compiles_semantic_view():
    text = SnowflakeAdapter(CONTRACT, FIXTURE).semantic_view_sql()
    assert "CREATE OR REPLACE SEMANTIC VIEW" in text
    assert "YEAROFWEEKISO" in text
    assert "orders.fill_rate" in text


def test_fabric_compiles_tmdl():
    text = FabricAdapter(CONTRACT, FIXTURE).tmdl_fragment()
    assert "measure fill_rate" in text
    assert "DIVIDE(" in text
    assert "column iso_week_year" in text
