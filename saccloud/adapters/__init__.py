from .databricks import DatabricksAdapter
from .snowflake import SnowflakeAdapter
from .fabric import FabricAdapter

ADAPTERS = {
    "databricks": DatabricksAdapter,
    "snowflake": SnowflakeAdapter,
    "fabric": FabricAdapter,
}
