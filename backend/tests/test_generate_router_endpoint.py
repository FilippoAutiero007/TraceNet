from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.models.manual_schemas import ManualNetworkRequest
from app.services.pkt_crypto import encrypt_pkt_data
from app.services.auth import AuthContext, get_optional_auth_context, require_pro_user
from app.services.generation_quota import reset_generation_quota_state
from app.services.nlp_parser import ParserServiceError
from app.utils.errors import api_error


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
    payload = response.json()
    assert payload["error"] == "Parser service unavailable."
    assert payload["code"] == "PARSER_BACKEND_FAILURE"
    assert payload["request_id"]
    assert response.headers["X-Request-ID"] == payload["request_id"]


def test_parse_network_request_endpoint_exposes_partial_json_and_defaults(monkeypatch):
    async def _fake_parse(user_input, current_state):
        from app.models.schemas import ParseNetworkResponse, ParseIntent

        return ParseNetworkResponse(
            intent=ParseIntent.INCOMPLETE,
            missing=["pcs", "routing_protocol"],
            json={"base_network": "10.0.0.0/24", "routers": 1, "switches": 1},
            suggestedDefaults={"pcs": 4, "routing_protocol": "STATIC"},
        )

    monkeypatch.setattr("app.routers.generate.parse_network_request", _fake_parse)

    response = client.post(
        "/api/parse-network-request",
        json={"user_input": "crea una rete 10.0.0.0/24", "current_state": {}},
    )

    assert response.status_code == 200
    assert response.json() == {
        "intent": "incomplete",
        "missing": ["pcs", "routing_protocol"],
        "json": {"base_network": "10.0.0.0/24", "routers": 1, "switches": 1},
        "suggestedDefaults": {"pcs": 4, "routing_protocol": "STATIC"},
        "error": None,
    }


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


def test_generate_pkt_uses_normalized_protocol_and_single_server_services_payload(monkeypatch):
    captured = {}

    def _fake_save_pkt_file(subnets, config, output_dir):
        captured["config"] = config
        return {
            "success": True,
            "pkt_path": "/tmp/tracenet/fake.pkt",
            "xml_path": "/tmp/tracenet/fake.xml",
            "encoding_used": "template_based",
            "file_size": 123,
        }

    monkeypatch.setattr("app.routers.generate.save_pkt_file", _fake_save_pkt_file)

    response = client.post(
        "/api/generate-pkt",
        json={
            "base_network": "10.0.0.0/24",
            "routers": 1,
            "switches": 1,
            "pcs": 5,
            "routing_protocol": "STATIC",
            "server_services": ["dns", "http"],
            "subnets": [{"name": "LAN", "required_hosts": 20}],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert captured["config"]["routing_protocol"] == "static"
    assert captured["config"]["server_services"] == ["dns", "http"]
    assert payload["config_summary"]["routing_protocol"] == "static"


def test_generate_pkt_tolerates_optional_auth_provider_unavailable(monkeypatch):
    def _fake_save_pkt_file(subnets, config, output_dir):
        return {
            "success": True,
            "pkt_path": "/tmp/tracenet/fake.pkt",
            "xml_path": "/tmp/tracenet/fake.xml",
            "encoding_used": "template_based",
            "file_size": 123,
        }

    async def _auth_down(request):
        raise api_error(503, "AUTH_PROVIDER_UNAVAILABLE", "Authentication service unavailable.")

    monkeypatch.setattr("app.routers.generate.save_pkt_file", _fake_save_pkt_file)
    monkeypatch.setattr("app.services.auth.verify_clerk_session_token", _auth_down)

    response = client.post(
        "/api/generate-pkt",
        headers={"Authorization": "Bearer maybe-valid-token"},
        json={
            "base_network": "10.0.0.0/24",
            "routers": 1,
            "switches": 1,
            "pcs": 5,
            "routing_protocol": "STATIC",
            "subnets": [{"name": "LAN", "required_hosts": 20}],
        },
    )

    assert response.status_code == 200
    assert response.json()["success"] is True


def test_generate_pkt_enforces_weekly_quota_for_free_users(monkeypatch):
    reset_generation_quota_state()
    monkeypatch.setattr(settings, "free_weekly_generation_limit", 2)

    app.dependency_overrides[get_optional_auth_context] = lambda: AuthContext(
        user_id="user_free",
        session_id="sess_free",
        plan="free",
        plan_scope="u",
        is_pro=False,
        claims={"sub": "user_free", "pla": "u:free"},
    )

    def _fake_save_pkt_file(subnets, config, output_dir):
        return {
            "success": True,
            "pkt_path": "/tmp/tracenet/free-limit.pkt",
            "xml_path": "/tmp/tracenet/free-limit.xml",
            "encoding_used": "template_based",
            "file_size": 123,
        }

    monkeypatch.setattr("app.routers.generate.save_pkt_file", _fake_save_pkt_file)

    request_payload = {
        "base_network": "10.0.0.0/24",
        "routers": 1,
        "switches": 1,
        "pcs": 5,
        "routing_protocol": "STATIC",
        "subnets": [{"name": "LAN", "required_hosts": 20}],
    }

    first = client.post("/api/generate-pkt", json=request_payload)
    second = client.post("/api/generate-pkt", json=request_payload)
    third = client.post("/api/generate-pkt", json=request_payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
    payload = third.json()
    assert payload["code"] == "SEC_RATE_LIMIT"
    assert payload["error"] == "Weekly network generation quota exceeded for your current plan."
    assert payload["request_id"]
    assert third.headers["X-Request-ID"] == payload["request_id"]
    app.dependency_overrides.clear()
    reset_generation_quota_state()


def test_analyze_pkt_endpoint_returns_diagnostic_report():
    app.dependency_overrides[require_pro_user] = lambda: AuthContext(
        user_id="user_123",
        session_id="sess_123",
        plan="professional",
        plan_scope="u",
        is_pro=True,
        claims={"sub": "user_123", "pla": "u:professional"},
    )
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
        data={"exercise_text": "Rete con gateway e addressing coerente"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["issue_count"] >= 1
    assert any(issue["code"] == "MISSING_DEFAULT_GATEWAY" for issue in payload["issues"])
    assert payload["exercise_text"] == "Rete con gateway e addressing coerente"
    assert payload["review"] is not None
    assert "things_to_fix" in payload["review"]
    app.dependency_overrides.clear()


def test_get_user_capabilities_endpoint_supports_anonymous_and_pro_users():
    reset_generation_quota_state()
    response = client.get("/api/me/capabilities")
    assert response.status_code == 200
    assert response.json() == {
        "is_authenticated": False,
        "user_id": None,
        "plan": None,
        "plan_scope": None,
        "is_pro": False,
        "can_use_pro_pkt_review": False,
        "weekly_generation_limit": settings.free_weekly_generation_limit,
        "weekly_generation_used": 0,
        "weekly_generation_remaining": settings.free_weekly_generation_limit,
    }

    app.dependency_overrides[get_optional_auth_context] = lambda: AuthContext(
        user_id="user_456",
        session_id="sess_456",
        plan="professional",
        plan_scope="u",
        is_pro=True,
        claims={"sub": "user_456", "pla": "u:professional"},
    )

    response = client.get("/api/me/capabilities")
    assert response.status_code == 200
    assert response.json() == {
        "is_authenticated": True,
        "user_id": "user_456",
        "plan": "professional",
        "plan_scope": "u",
        "is_pro": True,
        "can_use_pro_pkt_review": True,
        "weekly_generation_limit": None,
        "weekly_generation_used": 0,
        "weekly_generation_remaining": None,
    }
    app.dependency_overrides.clear()


def test_capabilities_rejects_invalid_auth_token_without_leaking_internal_details():
    response = client.get(
        "/api/me/capabilities",
        headers={"Authorization": "Bearer not-a-valid-jwt"},
    )

    assert response.status_code == 401
    payload = response.json()
    assert payload["error"] == "Invalid authentication token."
    assert payload["code"] == "AUTH_INVALID_TOKEN"
    assert payload["request_id"]
