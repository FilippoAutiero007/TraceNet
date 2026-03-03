"""Backwards-compatible re-exports for topology helpers.

Historically, some code/tests imported `build_links_config` from this module.
The implementation lives in `app.services.pkt_generator.topology`.
"""

from app.services.pkt_generator.topology import build_links_config

__all__ = ["build_links_config"]

