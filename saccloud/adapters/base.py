from __future__ import annotations

from pathlib import Path
from typing import Any, Dict


class PlatformAdapter:
    name = "base"
    adapter_version = "0.1.0-draft"

    def __init__(self, contract: Dict[str, Any], fixture_path: Path):
        self.contract = contract
        self.fixture_path = Path(fixture_path)

    def capabilities(self) -> Dict[str, str]:
        raise NotImplementedError

    def compile(self, output_dir: Path) -> Dict[str, Path]:
        raise NotImplementedError

    def provision_and_deploy(self) -> Dict[str, Any]:
        raise NotImplementedError

    def execute_queries(self, queries: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError
