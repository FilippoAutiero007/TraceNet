from fastapi.testclient import TestClient

from app.main import app
from app.models.manual_schemas import ManualNetworkRequest
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


def test_manual_network_request_accepts_nat_configuration():
    request = ManualNetworkRequest(
        base_network="10.0.0.0/24",
        subnets=[{"name": "LAN", "required_hosts": 20}],
        devices={"routers": 1, "switches": 1, "pcs": 5},
        routing_protocol="static",
        nat={
            "type": "pat",
            "acl": "10",
            "inside_network": "10.0.0.0",
            "inside_wildcard": "0.0.0.255",
            "outside_interface": "FastEthernet0/1",
        },
    )

    assert request.nat is not None
    assert request.nat.type == "pat"


def test_generate_pkt_manual_forwards_nat_to_pkt_generation(monkeypatch):
    captured = {}

    def _fake_save_pkt_file(subnets, config, output_dir):
        captured["subnets"] = subnets
        captured["config"] = config
        captured["output_dir"] = output_dir
        return {
            "success": True,
            "pkt_path": "/tmp/tracenet/fake.pkt",
            "xml_path": "/tmp/tracenet/fake.xml",
            "encoding_used": "template_based",
            "file_size": 123,
        }

    monkeypatch.setattr("app.routers.generate.save_pkt_file", _fake_save_pkt_file)

    response = client.post(
        "/api/generate-pkt-manual",
        json={
            "base_network": "10.0.0.0/24",
            "subnets": [{"name": "LAN", "required_hosts": 20}],
            "devices": {"routers": 1, "switches": 1, "pcs": 5},
            "routing_protocol": "static",
            "nat": {
                "type": "pat",
                "acl": "10",
                "inside_network": "10.0.0.0",
                "inside_wildcard": "0.0.0.255",
                "outside_interface": "FastEthernet0/1",
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert captured["config"]["nat"] == {
        "type": "pat",
        "acl": "10",
        "inside_network": "10.0.0.0",
        "inside_wildcard": "0.0.0.255",
        "outside_interface": "FastEthernet0/1",
    }
