"""
Compatibility wrapper exposing high-level PKT generation helpers.

Historically the project referenced `app.services.pkt_file_generator`.
The core implementation now lives under `app.services.pkt_generator.*`,
so this module re-exports the pieces that tests and callers rely on.
"""

from __future__ import annotations

from app.services.pkt_generator.topology import build_links_config

__all__ = ["build_links_config"]
