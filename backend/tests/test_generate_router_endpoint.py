from fastapi.testclient import TestClient

from app.main import app
from app.services.nlp_parser import ParserServiceError


client = TestClient(app)


def test_parse_network_request_endpoint_returns_502_for_parser_internal_errors(monkeypatch):
    async def _boom(user_input, current_state):
        raise ParserServiceError("upstream parser timeout")

    monkeypatch.setattr("app.routers.generate.parse_network_request", _boom)

    response = client.post(
        "/api/parse-network-request",
        json={"user_input": "crea una rete 10.0.0.0/24", "current_state": {}},
    )

    assert response.status_code == 502
    assert response.json()["detail"] == "Parser internal error: upstream parser timeout"
