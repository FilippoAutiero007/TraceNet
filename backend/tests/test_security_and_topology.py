import pytest
from fastapi import HTTPException

from app.models.schemas import NormalizedNetworkRequest, SubnetRequest
from app.routers.generate import _validate_filename, _default_subnet_for_base
from app.services.pkt_file_generator import build_links_config


def test_build_links_config_contains_expected_links():
    links = build_links_config(num_routers=1, num_switches=2, num_pcs=3)
    assert len(links) == 5
    assert links[0]["from"] == "Router0"
    assert any(link["to"].startswith("PC") for link in links)


def test_invalid_download_filename_rejected():
    with pytest.raises(HTTPException):
        _validate_filename("../../etc/passwd")


def test_normalized_network_request_rejects_invalid_cidr():
    with pytest.raises(ValueError):
        NormalizedNetworkRequest(
            base_network="999.999.1.0/99",
            routers=1,
            switches=1,
            pcs=10,
            routing_protocol="STATIC",
            subnets=[{"name": "LAN", "required_hosts": 10}],
        )


def test_subnet_request_allows_large_required_hosts():
    req = SubnetRequest(name="BIG_LAN", required_hosts=32000)
    assert req.required_hosts == 32000


def test_default_subnet_for_base_uses_full_base_network_capacity():
    subnet = _default_subnet_for_base("172.16.0.0/16")
    assert subnet.name == "LAN"
    assert subnet.required_hosts == 65534
