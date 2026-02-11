import pytest
from fastapi import HTTPException

from app.models.schemas import NormalizedNetworkRequest
from app.routers.generate import _validate_filename
from app.services.pkt_file_generator import build_links_config


def test_build_links_config_contains_expected_links():
    links = build_links_config(num_routers=1, num_switches=2, num_pcs=3)
    assert len(links) == 5
    assert links[0]["from"] == "Router0"
    assert any(link["to"].startswith("PC") for link in links)


def test_invalid_download_filename_rejected():
    with pytest.raises(HTTPException):
        _validate_filename("../../etc/passwd")


def test_encoded_path_traversal_rejected():
    with pytest.raises(HTTPException):
        _validate_filename("..%2F..%2Fetc%2Fpasswd")


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
