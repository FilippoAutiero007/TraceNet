from fastapi.testclient import TestClient

from app.main import app
from app.models.manual_schemas import ManualNetworkRequest
from app.services.pkt_crypto import encrypt_pkt_data
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


def test_analyze_pkt_endpoint_returns_diagnostic_report():
    xml = """
    <PACKETTRACER5>
      <VERSION>8.2.2.0400</VERSION>
      <NETWORK>
        <DEVICES>
          <DEVICE>
            <ENGINE>
              <TYPE>Router</TYPE>
              <NAME>Router0</NAME>
              <SAVE_REF_ID>save-ref-id:r0</SAVE_REF_ID>
              <MODULE>
                <SLOT><MODULE><PORT><TYPE>eCopperFastEthernet</TYPE><IP>192.168.1.1</IP><SUBNET>255.255.255.0</SUBNET><PORT_GATEWAY /></PORT></MODULE></SLOT>
              </MODULE>
              <RUNNINGCONFIG>
                <LINE>interface FastEthernet0/0</LINE>
                <LINE> ip address 192.168.1.1 255.255.255.0</LINE>
                <LINE>!</LINE>
              </RUNNINGCONFIG>
            </ENGINE>
            <WORKSPACE><LOGICAL><DEV_ADDR>1</DEV_ADDR><MEM_ADDR>2</MEM_ADDR></LOGICAL></WORKSPACE>
          </DEVICE>
          <DEVICE>
            <ENGINE>
              <TYPE>Pc</TYPE>
              <NAME>PC0</NAME>
              <SAVE_REF_ID>save-ref-id:pc0</SAVE_REF_ID>
              <MODULE>
                <SLOT><MODULE><PORT><TYPE>eCopperFastEthernet</TYPE><IP>192.168.1.10</IP><SUBNET>255.255.255.0</SUBNET><PORT_GATEWAY /></PORT></MODULE></SLOT>
              </MODULE>
            </ENGINE>
            <WORKSPACE><LOGICAL><DEV_ADDR>3</DEV_ADDR><MEM_ADDR>4</MEM_ADDR></LOGICAL></WORKSPACE>
          </DEVICE>
        </DEVICES>
        <LINKS>
          <LINK>
            <CABLE>
              <FROM>save-ref-id:r0</FROM>
              <PORT>FastEthernet0/0</PORT>
              <TO>save-ref-id:pc0</TO>
              <PORT>FastEthernet0</PORT>
            </CABLE>
          </LINK>
        </LINKS>
      </NETWORK>
    </PACKETTRACER5>
    """
    pkt_bytes = encrypt_pkt_data(xml.encode("utf-8"))

    response = client.post(
        "/api/analyze-pkt",
        files={"file": ("broken.pkt", pkt_bytes, "application/octet-stream")},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["issue_count"] >= 1
    assert any(issue["code"] == "MISSING_DEFAULT_GATEWAY" for issue in payload["issues"])
