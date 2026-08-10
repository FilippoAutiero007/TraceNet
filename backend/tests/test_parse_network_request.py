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
    monkeypatch.setattr("app.config.settings.mistral_api_key", None)

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
    monkeypatch.setattr("app.config.settings.mistral_api_key", None)

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

    from pydantic import SecretStr; monkeypatch.setattr("app.config.settings.mistral_api_key", SecretStr("test-key"))
    monkeypatch.setattr("app.services.nlp_parser.Mistral", _FakeMistral)
    monkeypatch.setattr("app.services.nlp_parser.retrieve_relevant_documents", lambda *args, **kwargs: [])

    with pytest.raises(ParserServiceError, match="invalid or malformed JSON"):
        await parse_network_request("create a network with router", {})

    assert attempts["count"] == 1


@pytest.mark.asyncio
async def test_parse_network_request_detects_network_context_from_cidr_and_nat(monkeypatch):
    monkeypatch.setattr("app.config.settings.mistral_api_key", None)

    response = await parse_network_request("Configura 10.0.0.0/24 con NAT e gateway centrale", {})

    assert response.intent == ParseIntent.INCOMPLETE
    assert "base_network" not in response.missing
    assert response.json_payload["base_network"] == "10.0.0.0/24"


@pytest.mark.asyncio
async def test_parse_network_request_heuristically_extracts_counts_and_protocol(monkeypatch):
    monkeypatch.setattr("app.config.settings.mistral_api_key", None)

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
    monkeypatch.setattr("app.config.settings.mistral_api_key", None)

    response = await parse_network_request(
        "Crea una rete 192.168.10.0/24 con 1 router, 1 switch e 12 pc",
        {},
    )

    assert response.intent == ParseIntent.COMPLETE
    assert response.json_payload["routing_protocol"] == "STATIC"


@pytest.mark.asyncio
async def test_parse_network_request_extracts_multi_site_networks_and_server_services(monkeypatch):
    monkeypatch.setattr("app.config.settings.mistral_api_key", None)

    exercise = """
    Sede di Bologna:
    Per la rete interna del primo piano si utilizzi la rete 192.168.1.0.
    Il router ha IP pubblico 82.15.44.10.
    Nel secondo piano il marketing dispone di 5 PC e di un server DHCP dedicato.
    Data Center di Firenze:
    La rete di Firenze deve essere impostata utilizzando come base la rete 172.16.0.0.
    Nel data center sono presenti due server pubblici:
    Server Web: 8.8.8.10
    AdGuard DNS: 8.8.8.8
    Per il servizio di posta l'azienda vuole gestirlo internamente.
    Ufficio di Mondragone:
    L'ufficio è composto da 3 PC e il router esce con IP pubblico 1.117.170.23.
    Richieste di configurazione:
    servizi NAT/PAT;
    configurazione del DNS;
    configurazione del servizio posta/mail;
    l'ufficio marketing non deve comunicare con l'Ufficio Tecnico;
    la sede di Mondragone deve accedere solo al server di posta;
    l'Ufficio Tecnico non deve avere accesso al server web.
    """

    response = await parse_network_request(exercise, {})

    assert response.intent == ParseIntent.INCOMPLETE
    assert response.json_payload["base_network"] == "192.168.1.0/24"
    assert response.json_payload["routing_protocol"] == "STATIC"
    assert response.json_payload["servers"] >= 4

    network_sites = response.json_payload["network_sites"]
    assert any(site["name"] == "Bologna" and site["base_network"] == "192.168.1.0/24" for site in network_sites)
    assert any(site["name"] == "Firenze" and site["base_network"] == "172.16.0.0/16" for site in network_sites)
    assert any(site["name"] == "Mondragone" and site["public_ip"] == "1.117.170.23" for site in network_sites)

    server_configs = response.json_payload["servers_config"]
    services_by_host = {cfg["hostname"]: set(cfg["services"]) for cfg in server_configs}
    assert "marketing-dhcp.local" in services_by_host
    assert "dhcp" in services_by_host["marketing-dhcp.local"]
    assert "web.horizon.local" in services_by_host
    assert "http" in services_by_host["web.horizon.local"]
    assert "dns.horizon.local" in services_by_host
    assert "dns" in services_by_host["dns.horizon.local"]
    assert "mail.horizon.local" in services_by_host
    assert {"email", "smtp", "pop3"}.issubset(services_by_host["mail.horizon.local"])

    requirements = set(response.json_payload["requirements"])
    assert "Enable NAT/PAT" in requirements
    assert "Block Marketing to Technical office communication" in requirements
    assert "Allow Mondragone access only to the mail server" in requirements
