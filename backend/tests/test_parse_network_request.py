import pytest

from app.models.schemas import ParseIntent
from app.services.nlp_parser import parse_network_request


@pytest.mark.asyncio
async def test_parse_network_request_not_network_intent():
    response = await parse_network_request("scrivimi una poesia", {})
    assert response.intent == ParseIntent.NOT_NETWORK
    assert response.json_payload == {}


@pytest.mark.asyncio
async def test_parse_network_request_incomplete_without_required_fields(monkeypatch):
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)

    response = await parse_network_request("crea una rete aziendale", {"base_network": "10.0.0.0/24"})

    assert response.intent == ParseIntent.INCOMPLETE
    assert set(response.missing) == {"routers", "switches", "pcs", "routing_protocol"}


@pytest.mark.asyncio
async def test_parse_network_request_complete_from_state(monkeypatch):
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)

    response = await parse_network_request(
        "network con router e switch",
        {
            "base_network": "10.0.0.0/24",
            "routers": 1,
            "switches": 2,
            "pcs": 20,
            "routing_protocol": "static routing",
            "subnets": [{"name": "LAN", "required_hosts": 20}],
        },
    )

    assert response.intent == ParseIntent.COMPLETE
    assert response.json_payload["routing_protocol"] == "STATIC"


@pytest.mark.asyncio
async def test_parse_network_request_rejects_oversized_input(monkeypatch):
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)

    response = await parse_network_request("r" * 5000, {})

    assert response.intent == ParseIntent.INCOMPLETE
    assert response.missing == ["user_input"]
