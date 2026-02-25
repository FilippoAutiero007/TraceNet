"""Unit tests for pkt_generator package."""
import pytest
from app.services.pkt_generator.utils import safe_name, validate_name
from app.services.pkt_generator.layout import calculate_device_coordinates

def test_safe_name():
    assert safe_name("Router", 0) == "Router0"
    assert safe_name("PC", 99) == "PC99"

def test_validate_name_invalid():
    with pytest.raises(ValueError):
        validate_name("bad$name")

def test_layout_single_device():
    x, y = calculate_device_coordinates(0, 1)
    assert x == 200
    assert y in (200, 250)

def test_layout_zigzag():
    coords = [calculate_device_coordinates(i, 5) for i in range(5)]
    # Row 0 left-to-right, Row 1 right-to-left
    assert coords[0][0] < coords[1][0]
    assert coords[3][0] > coords[4][0]
