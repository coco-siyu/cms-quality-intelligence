from pathlib import Path

import yaml
from openapi_spec_validator import validate


def test_root_openapi_contract_is_valid() -> None:
    contract_path = Path(__file__).parents[2] / "openapi.yaml"
    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))

    validate(contract)
