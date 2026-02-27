"""Template loading and caching utilities for PKT generation."""
from __future__ import annotations

import copy
import logging
import threading
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Optional

from app.services.pkt_crypto import decrypt_pkt_data
from .paths import resolve_path

logger = logging.getLogger(__name__)


class TemplateRepository:
    """
    Handles loading/decrypting the base PKT template and caching device templates.
    """

    def __init__(self, template_path: str) -> None:
        resolved = resolve_path(template_path)
        if not resolved:
            raise FileNotFoundError(f"Template not found: {template_path}")

        self.default_template_root = self._load_template_file(resolved)
        self.link_template = self._extract_link_template(self.default_template_root)

        self._template_cache: Dict[str, ET.Element] = {}
        self._template_cache_lock = threading.Lock()

    # ------------------------ public API ------------------------

    def clone_default_root(self) -> ET.Element:
        """Deep copy of the decrypted base template root."""
        return copy.deepcopy(self.default_template_root)

    def get_device_template(self, base_template_path: str) -> ET.Element:
        """
        Return a deep-copied DEVICE element from cache, loading from disk if needed.
        Thread-safe via per-instance lock.
        """
        resolved = resolve_path(base_template_path)
        if not resolved:
            raise FileNotFoundError(f"Template not found: {base_template_path}")

        cache_key = str(resolved)
        with self._template_cache_lock:
            cached = self._template_cache.get(cache_key)
            if cached is not None:
                return copy.deepcopy(cached)

        root = self._load_template_file(resolved)
        device = self._extract_device(root, cache_key)

        with self._template_cache_lock:
            self._template_cache[cache_key] = device

        return copy.deepcopy(device)

    # ----------------------- internals --------------------------

    def _load_template_file(self, path: Path) -> ET.Element:
        template_bytes = path.read_bytes()
        xml_str = decrypt_pkt_data(template_bytes).decode("utf-8", errors="strict")
        return ET.fromstring(xml_str)

    @staticmethod
    def _extract_link_template(root: ET.Element) -> Optional[ET.Element]:
        network = root.find("NETWORK")
        if network is None:
            return None
        links_node = network.find("LINKS")
        link_list = links_node.findall("LINK") if links_node is not None else []
        return link_list[0] if link_list else None

    @staticmethod
    def _extract_device(root: ET.Element, base_template_path: str) -> ET.Element:
        network = root.find("NETWORK")
        if network is not None:
            devices_node = network.find("DEVICES")
            if devices_node is not None:
                device = devices_node.find("DEVICE")
                if device is not None:
                    return device

        raise ValueError(f"Could not find valid DEVICE node in template {base_template_path}")
