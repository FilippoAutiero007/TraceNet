import pytest

from app.models.schemas import ParseIntent
from app.services.nlp_parser import ParserServiceError, parse_network_request


@pytest.mark.asyncio
async def test_parse_network_request_not_network_intent():
    response = await parse_network_request("scrivimi una poesia", {})
    assert response.intent == ParseIntent.NOT_NETWORK
    assert response.json_payload == {}
    assert response.suggested_defaults == {}


@pytest.mark.asyncio
async def test_parse_network_request_incomplete_without_required_fields(monkeypatch):
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)

    response = await parse_network_request("crea una rete aziendale", {"base_network": "10.0.0.0/24"})

    assert response.intent == ParseIntent.INCOMPLETE
    assert set(response.missing) == {"routers", "switches", "pcs"}
    assert response.json_payload["base_network"] == "10.0.0.0/24"
    assert response.json_payload["routing_protocol"] == "STATIC"
    assert response.suggested_defaults == {
        "routers": 1,
        "switches": 1,
        "pcs": 4,
    }


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
    assert response.suggested_defaults == {}


@pytest.mark.asyncio
async def test_parse_network_request_does_not_retry_deterministic_parser_errors(monkeypatch):
    attempts = {"count": 0}

    class _FakeChat:
        def complete(self, **kwargs):
            attempts["count"] += 1
            return type(
                "FakeResponse",
                (),
                {
                    "choices": [
                        type(
                            "FakeChoice",
                            (),
                            {"message": type("FakeMessage", (), {"content": '{"intent": "complete", "json": '})()},
                        )()
                    ]
                },
            )()

    class _FakeMistral:
        def __init__(self, api_key):
            self.chat = _FakeChat()

    monkeypatch.setenv("MISTRAL_API_KEY", "test-key")
    monkeypatch.setattr("app.services.nlp_parser.Mistral", _FakeMistral)
    monkeypatch.setattr("app.services.nlp_parser.retrieve_relevant_documents", lambda *args, **kwargs: [])

    with pytest.raises(ParserServiceError, match="invalid or malformed JSON"):
        await parse_network_request("create a network with router", {})

    assert attempts["count"] == 1


@pytest.mark.asyncio
async def test_parse_network_request_detects_network_context_from_cidr_and_nat(monkeypatch):
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)

    response = await parse_network_request("Configura 10.0.0.0/24 con NAT e gateway centrale", {})

    assert response.intent == ParseIntent.INCOMPLETE
    assert "base_network" not in response.missing
    assert response.json_payload["base_network"] == "10.0.0.0/24"


@pytest.mark.asyncio
async def test_parse_network_request_heuristically_extracts_counts_and_protocol(monkeypatch):
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)

    response = await parse_network_request(
        "Crea una rete 192.168.10.0/24 con 2 router, 3 switch, 25 pc e OSPF",
        {},
    )

    assert response.intent == ParseIntent.COMPLETE
    assert response.json_payload["base_network"] == "192.168.10.0/24"
    assert response.json_payload["routers"] == 2
    assert response.json_payload["switches"] == 3
    assert response.json_payload["pcs"] == 25
    assert response.json_payload["routing_protocol"] == "OSPF"


@pytest.mark.asyncio
async def test_parse_network_request_defaults_to_static_for_simple_single_network(monkeypatch):
    monkeypatch.delenv("MISTRAL_API_KEY", raising=False)

    response = await parse_network_request(
        "Crea una rete 192.168.10.0/24 con 1 router, 1 switch e 12 pc",
        {},
    )

    assert response.intent == ParseIntent.COMPLETE
    assert response.json_payload["routing_protocol"] == "STATIC"
