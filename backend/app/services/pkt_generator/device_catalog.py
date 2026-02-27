"""Device catalog loading and resolution logic."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


class DeviceCatalog:
    """Light wrapper around the JSON catalog with a small resolve policy."""

    def __init__(self, catalog_path: Path) -> None:
        self.catalog_path = catalog_path
        self.catalog: Dict[str, Any] = self._load_catalog(catalog_path)

    def resolve(self, device_type: str) -> Dict[str, Any]:
        device_type = device_type.lower().strip()
        if device_type in self.catalog:
            return self.catalog[device_type]

        if "router" in device_type:
            logger.warning(
                "Unknown device type '%s', falling back to 'router-2port'", device_type
            )
            return self.catalog.get("router-2port", {})

        logger.warning("Unknown device type '%s', falling back to 'pc'", device_type)
        return self.catalog.get("pc", {})

    # ----------------------- internals --------------------------

    def _load_catalog(self, path: Path) -> Dict[str, Any]:
        if not path.exists():
            logger.error("device_catalog.json not found at %s", path)
            return {}
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            logger.error("Failed to load device catalog: %s", exc)
            return {}
