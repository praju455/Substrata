"""Public contracts for the initial API scaffold."""

from fastapi.testclient import TestClient

from substrata.app import create_app


def test_health_reports_process_liveness_and_synthetic_mode() -> None:
    """The health response must be successful and visibly identify synthetic mode."""
    with TestClient(create_app()) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.json() == {
        "status": "ok",
        "service": "substrata-api",
        "data_mode": "synthetic",
    }


def test_openapi_publishes_the_typed_health_contract() -> None:
    """Clients can discover the route and its response schema through OpenAPI."""
    with TestClient(create_app()) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200
    specification = response.json()
    health_schema = specification["paths"]["/health"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]
    assert health_schema["$ref"] == "#/components/schemas/HealthResponse"
    properties = specification["components"]["schemas"]["HealthResponse"]["properties"]
    assert properties["data_mode"]["const"] == "synthetic"
