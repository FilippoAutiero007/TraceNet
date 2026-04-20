import pytest
from fastapi import HTTPException

from app.models.schemas import DeviceConfig, NormalizedNetworkRequest, SubnetRequest
from app.routers.generate import _validate_filename, _default_subnet_for_base, generate_network
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


def test_device_config_allows_large_pc_counts():
    cfg = DeviceConfig(routers=1, switches=1, pcs=5000)
    assert cfg.pcs == 5000


def test_normalized_network_request_does_not_force_subnet_hosts_to_match_pc_count():
    req = NormalizedNetworkRequest(
        base_network="10.0.0.0/16",
        routers=1,
        switches=1,
        pcs=5000,
        routing_protocol="STATIC",
        subnets=[{"name": "LAN", "required_hosts": 100}],
    )
    assert req.pcs == 5000
    assert req.subnets[0].required_hosts == 100


def test_default_subnet_for_base_uses_full_base_network_capacity():
    subnet = _default_subnet_for_base("172.16.0.0/16")
    assert subnet.name == "LAN"
    assert subnet.required_hosts == 65534


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("base_network", "expected_network"),
    [
        ("10.0.0.0/8", "10.0.0.0/8"),
        ("172.16.0.0/16", "172.16.0.0/16"),
        ("192.168.16.0/20", "192.168.16.0/20"),
    ],
)
async def test_generate_network_keeps_requested_base_prefix_when_subnets_are_omitted(
    base_network,
    expected_network,
):
    response = await generate_network(
        NormalizedNetworkRequest(
            base_network=base_network,
            routers=1,
            switches=1,
            pcs=5,
            routing_protocol="STATIC",
            subnets=[],
        )
    )

    assert response.success is True
    assert response.subnets is not None
    assert len(response.subnets) == 1
    assert response.subnets[0].network == expected_network
