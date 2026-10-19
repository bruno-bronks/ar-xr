"""Contrato HTTP (spec-first): specs/contracts/openapi.yaml <-> API real.

Requisitos: REQ-ENG-002, REQ-ENG-003.
"""

from pathlib import Path
from typing import Any

import pytest
import yaml
from app.main import create_app
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
from openapi_spec_validator import validate

ROOT = Path(__file__).resolve().parents[2]
SPEC: dict[str, Any] = yaml.safe_load((ROOT / "specs/contracts/openapi.yaml").read_text("utf-8"))
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


def _operations(status: str) -> set[tuple[str, str]]:
    return {
        (path, method)
        for path, item in SPEC["paths"].items()
        for method, op in item.items()
        if method in HTTP_METHODS and op["x-implementation"] == status
    }


def _app(db: bool = True) -> Any:
    return create_app(checks={"database": lambda: db, "broker": lambda: True})


def test_spec_is_valid_openapi_3_1() -> None:
    assert SPEC["openapi"].startswith("3.1")
    validate(SPEC)


def test_every_operation_declares_implementation_status() -> None:
    for path, item in SPEC["paths"].items():
        for method, op in item.items():
            if method in HTTP_METHODS:
                assert op["x-implementation"] in {"implemented", "planned"}, (path, method)


def test_mvp_contract_endpoints_are_all_declared() -> None:
    """Plano mestre, secao 7."""
    declared = _operations("implemented") | _operations("planned")

    assert declared == {
        ("/health/live", "get"),
        ("/health/ready", "get"),
        ("/api/v1/equipment", "get"),
        ("/api/v1/equipment/{equipment_id}", "get"),
        ("/api/v1/equipment/{equipment_id}/telemetry/latest", "get"),
        ("/api/v1/equipment/{equipment_id}/twin", "get"),
        ("/api/v1/equipment/{equipment_id}/alerts", "get"),
        ("/api/v1/assistant/questions", "post"),
        ("/api/v1/spatial/markers/{marker_id}", "get"),
    }


def test_implemented_operations_exist_in_the_api() -> None:
    api = {
        (path, method)
        for path, item in _app().openapi()["paths"].items()
        for method in item
        if method in HTTP_METHODS
    }

    assert api == _operations("implemented")


def test_api_has_no_route_outside_the_contract() -> None:
    routes = {
        (route.path, method.lower())
        for route in _app().routes
        if isinstance(route, APIRoute)
        for method in route.methods or set()
    }

    assert routes <= _operations("implemented")


@pytest.mark.parametrize(
    ("path", "db_ok", "status", "schema"),
    [
        ("/health/live", True, "200", "Live"),
        ("/health/ready", True, "200", "Ready"),
        ("/health/ready", False, "503", "Ready"),
    ],
)
def test_responses_conform_to_contract_schemas(
    path: str, db_ok: bool, status: str, schema: str
) -> None:
    response = TestClient(_app(db_ok)).get(path)

    assert str(response.status_code) == status
    assert status in SPEC["paths"][path]["get"]["responses"]
    validator = Draft202012Validator(
        {"$ref": f"#/components/schemas/{schema}", "components": SPEC["components"]}
    )
    validator.validate(response.json())


def test_contract_documents_correlation_header_on_every_health_response() -> None:
    for path in ("/health/live", "/health/ready"):
        for response in SPEC["paths"][path]["get"]["responses"].values():
            assert "X-Correlation-ID" in response["headers"]
