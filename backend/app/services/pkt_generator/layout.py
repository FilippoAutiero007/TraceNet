"""
Layout logic for PKT generator.
Calculates device coordinates using a zig-zag pattern to avoid cable overlap.
"""
from typing import Tuple


def calculate_device_coordinates(
    index: int, 
    total_devices: int, 
    start_x: int = 200, 
    start_y: int = 200, 
    col_spacing: int = 250, 
    row_spacing: int = 200
) -> Tuple[int, int]:
    """
    Calculate (x, y) coordinates for a device based on its index.
    
    Args:
        index: The 0-based index of the device.
        total_devices: Total number of devices to layout.
        start_x: X coordinate of the first device.
        start_y: Y coordinate of the first device.
        col_spacing: Horizontal spacing between columns.
        row_spacing: Vertical spacing between rows.
        
    Returns:
        Tuple[int, int]: (x, y) coordinates.
    """
    # Determine columns based on total devices to keep aspect ratio reasonable
    if total_devices <= 4:
        cols = 2
    elif total_devices <= 9:
        cols = 3
    else:
        cols = 4

    # Grid position
    row = index // cols
    col = index % cols
    
    # Zig-zag pattern:
    # default_x: base grid position
    default_x = start_x + (col * col_spacing)
    default_y = start_y + (row * row_spacing)

    # Offsets to prevent perfect alignment (cable overlap)
    # x_offset: 0 or 30 (alternates every device)
    # y_offset: 0 or 50 (alternates every device)
    x_offset = (index % 2) * 30
    y_offset = (index % 2) * 50

    return (default_x + x_offset, default_y + y_offset)
