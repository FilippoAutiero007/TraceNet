from __future__ import annotations

import copy
import logging
from pathlib import Path
from typing import Any, Optional

import xml.etree.ElementTree as ET

from app.services.pkt_crypto import decrypt_pkt_data, encrypt_pkt_data
from .generator_components import PhysicalWorkspaceOps, build_device, create_link
from .utils import ensure_child, load_device_templates_config, rand_saveref, set_text

logger = logging.getLogger(__name__)

DEVICE_TEMPLATES = load_device_templates_config()
_BASE = Path(__file__).resolve().parent.parent.parent.parent
TEMPLATES_BASE_DIR = _BASE / "templates"
DEFAULT_LINK_TEMPLATE_XML = """
<LINK>
  <TYPE>eCopper</TYPE>
  <CABLE>
    <LENGTH>1</LENGTH>
    <FUNCTIONAL>true</FUNCTIONAL>
    <FROM>save-ref-id:0</FROM>
    <PORT>FastEthernet0/0</PORT>
    <TO>save-ref-id:1</TO>
    <PORT>FastEthernet0/1</PORT>
    <FROM_DEVICE_MEM_ADDR>1527445101552</FROM_DEVICE_MEM_ADDR>
    <TO_DEVICE_MEM_ADDR>1527585720040</TO_DEVICE_MEM_ADDR>
    <FROM_PORT_MEM_ADDR>1527596954728</FROM_PORT_MEM_ADDR>
    <TO_PORT_MEM_ADDR>1527593764088</TO_PORT_MEM_ADDR>
    <GEO_VIEW_COLOR>#6ba72e</GEO_VIEW_COLOR>
    <IS_MANAGED_IN_RACK_VIEW>false</IS_MANAGED_IN_RACK_VIEW>
    <TYPE>eStraightThrough</TYPE>
  </CABLE>
</LINK>
""".strip()


class PKTGenerator:
    def __init__(self, template_path: str | None = None) -> None:
        # template_path is accepted for backward compatibility but no longer used
        # as a fixed base reference. The real base template is selected in generate().
        _ = template_path
        self.template_root: Optional[ET.Element] = None
        self.link_template: Optional[ET.Element] = None
        self.catalog = DEVICE_TEMPLATES
        self._physical_ops: Optional[PhysicalWorkspaceOps] = None
        self._device_types_by_name: dict[str, str] = {}
        self._power_proto: Optional[ET.Element] = None

    def resolve_device_type(self, device_type: str) -> dict[str, Any]:
        device_key = (device_type or "").strip().lower()
        resolved = self.catalog.get(device_key)
        if resolved is not None:
            return resolved
        if "router" in device_key:
            return self.catalog.get("router-2port", self.catalog["router-1port"])
        return self.catalog["pc"]

    def _resolve_template_path_for_device_type(self, device_type: str) -> Path:
        resolved_meta = self.resolve_device_type(device_type)
        relative_template = str(resolved_meta.get("template_file", "")).strip()
        template_path = TEMPLATES_BASE_DIR / relative_template
        if not template_path.exists():
            raise FileNotFoundError(f"Device template not found: {template_path}")
        return template_path

    def _load_template_root_for_device_type(self, device_type: str) -> ET.Element:
        template_path = self._resolve_template_path_for_device_type(device_type)
        xml_str = decrypt_pkt_data(template_path.read_bytes()).decode("utf-8", errors="strict")
        root = ET.fromstring(xml_str)
        if root.find("NETWORK") is None:
            raise ValueError(f"Invalid template {template_path}: missing NETWORK")
        return root

    def _extract_link_template(self, root: ET.Element) -> ET.Element:
        links = root.findall("NETWORK/LINKS/LINK")
        if links:
            return copy.deepcopy(links[0])
        # Fallback if single-device templates have no LINK prototype.
        return ET.fromstring(DEFAULT_LINK_TEMPLATE_XML)

    def generate(
        self,
        devices_config: list[dict[str, Any]],
        links_config: Optional[list[dict[str, Any]]] = None,
        output_path: str = "output.pkt",
    ) -> str:
        base_type = str(devices_config[0].get("type", "router-1port")) if devices_config else "router-1port"
        root = self._load_template_root_for_device_type(base_type)
        self.template_root = root
        self.link_template = self._extract_link_template(root)
        self._physical_ops = PhysicalWorkspaceOps(root)

        network = root.find("NETWORK")
        if network is None:
            raise ValueError("Template clone error: missing NETWORK")

        devices_elem = ensure_child(network, "DEVICES")
        links_elem = ensure_child(network, "LINKS")
        devices_elem.clear()
        links_elem.clear()

        self._device_types_by_name = {}

        num_devices = len(devices_config)
        cols = 2 if num_devices <= 4 else 3 if num_devices <= 9 else 4
        used_macs: set[str] = set()
        used_dev_addrs: set[str] = set()
        used_mem_addrs: set[str] = set()
        device_saverefs: dict[str, str] = {}
        device_physical_hints: dict[str, dict[str, Any]] = {}

        for idx, dev_cfg in enumerate(devices_config):
            try:
                new_device, name, saveref, category, physical_hint = build_device(
                    dev_cfg=dev_cfg,
                    idx=idx,
                    cols=cols,
                    templates_base_dir=TEMPLATES_BASE_DIR,
                    device_templates=DEVICE_TEMPLATES,
                    used_macs=used_macs,
                    used_dev_addrs=used_dev_addrs,
                    used_mem_addrs=used_mem_addrs,
                )
            except Exception as exc:  # noqa: BLE001
                logger.warning("Skipping device %s: %s", dev_cfg.get("name"), exc)
                continue

            devices_elem.append(new_device)
            device_saverefs[name] = saveref
            self._device_types_by_name[name] = category
            if physical_hint:
                device_physical_hints[name] = physical_hint

        if self._physical_ops is not None:
            self._physical_ops.sync(root, devices_elem, device_physical_hints=device_physical_hints)

        requested_links = len(links_config or [])
        if links_config:
            for link_cfg in links_config:
                create_link(
                    links_elem=links_elem,
                    link_template=self.link_template,
                    link_cfg=link_cfg,
                    device_saverefs=device_saverefs,
                    get_device_type=self._get_device_type,
                )
        created_links = len(links_elem.findall("LINK"))
        if requested_links and created_links == 0:
            logger.warning("Requested %s links but generated 0 valid LINK nodes", requested_links)

        xml_bytes = (
            b'<?xml version="1.0" encoding="utf-8"?>\n'
            + ET.tostring(root, encoding="utf-8", method="xml")
        )
        Path(output_path).write_bytes(encrypt_pkt_data(xml_bytes))
        return output_path

    def _get_device_type(self, device_name: str) -> str:
        mapped = self._device_types_by_name.get(device_name, "")
        if "router" in mapped:
            return "router"
        if "switch" in mapped:
            return "switch"
        if "pc" in mapped or "server" in mapped or "endpoint" in mapped or "host" in mapped:
            return "pc"

        name_lower = device_name.lower()
        if "router" in name_lower or name_lower.startswith("r"):
            return "router"
        if "switch" in name_lower or "sw" in name_lower:
            return "switch"
        if "pc" in name_lower or "host" in name_lower or "end" in name_lower:
            return "pc"
        logger.warning("Cannot determine device type for %s, assuming router", device_name)
        return "router"

    def _cleanup_physical_workspace(self, root: ET.Element) -> None:
        if self._physical_ops is not None:
            self._physical_ops.cleanup(root)

    def _sync_physical_workspace(self, root: ET.Element, devices_elem: ET.Element) -> None:
        if self._physical_ops is not None:
            self._physical_ops.sync(root, devices_elem)

    def _extract_base_physical_paths(self) -> dict[str, list[str]]:
        if self._physical_ops is None:
            return {}
        self._physical_ops._ensure_cache()
        return dict(self._physical_ops._base_physical_paths or {})

    def _extract_base_pw_nodes(self) -> dict[str, ET.Element]:
        if self._physical_ops is None:
            return {}
        self._physical_ops._ensure_cache()
        return {k: copy.deepcopy(v) for k, v in (self._physical_ops._base_pw_nodes or {}).items()}

    def _extract_pc_parent_node(self) -> Optional[ET.Element]:
        if self._physical_ops is None:
            return None
        self._physical_ops._ensure_cache()
        parent = self._physical_ops._pc_parent_node
        return copy.deepcopy(parent) if parent is not None else None

    def _inject_power_distribution(self, devices_elem: ET.Element) -> None:
        if self._power_proto is None:
            return
        for existing in list(devices_elem.findall("DEVICE")):
            name = (existing.findtext("ENGINE/NAME") or "").lower()
            if "power distribution device" in name:
                devices_elem.remove(existing)

        pdu = copy.deepcopy(self._power_proto)
        engine = pdu.find("ENGINE")
        if engine is None:
            return
        set_text(engine, "NAME", "Power Distribution Device0", create=True)
        set_text(engine, "SYSNAME", "Power Distribution Device0", create=True)
        pdu_saveref = rand_saveref()
        set_text(engine, "SAVE_REF_ID", pdu_saveref, create=True)
        legacy = engine.find("SAVEREFID")
        if legacy is not None:
            legacy.text = pdu_saveref
        devices_elem.append(pdu)
