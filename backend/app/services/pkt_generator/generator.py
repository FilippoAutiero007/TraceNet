from __future__ import annotations

import copy
import logging
import re
from pathlib import Path
from typing import Any, Optional

import xml.etree.ElementTree as ET

from app.services.pkt_crypto import decrypt_pkt_data, encrypt_pkt_data
from .generator_components import PhysicalWorkspaceOps, build_device, create_link
from .utils import ensure_child, load_device_templates_config, rand_saveref, set_text
from .layout import apply_hierarchical_layout

logger = logging.getLogger(__name__)

DEVICE_TEMPLATES = load_device_templates_config()
_BASE = Path(__file__).resolve().parent.parent.parent.parent
TEMPLATES_BASE_DIR = _BASE / "templates"
SIMPLE_REF_PATH = TEMPLATES_BASE_DIR / "simple_ref.pkt"

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


def _expand_self_closing_tags(xml_str: str) -> str:
    """
    Converte tag self-closing <TAG /> in <TAG></TAG>.
    Packet Tracer 8.2.2 non accetta tag self-closing e li interpreta
    come dati corrotti nel Physical Workspace.
    """
    return re.sub(
        r'<([A-Za-z_][A-Za-z0-9_:\-]*)([^>]*?)\s*/>',
        lambda m: f'<{m.group(1)}{m.group(2)}></{m.group(1)}>',
        xml_str,
    )


class PKTGenerator:
    def __init__(self, template_path: str | None = None) -> None:
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
            alias_path = TEMPLATES_BASE_DIR / relative_template.replace("FinalPoint/", "EndPoint/")
            if alias_path.exists():
                template_path = alias_path
        if not template_path.exists():
            raise FileNotFoundError(f"Device template not found: {template_path}")
        return template_path

    def _load_base_template(self) -> ET.Element:
        """
        Carica simple_ref.pkt come base strutturale.
        È l'unico template PKT apribile standalone in PT 8.2.2.
        Il suo PHYSICALWORKSPACE, OPTIONS, SCENARIOSET ecc. sono validi
        e vengono mantenuti intatti nel file finale.
        """
        if not SIMPLE_REF_PATH.exists():
            raise FileNotFoundError(f"Base template not found: {SIMPLE_REF_PATH}")
        xml_str = decrypt_pkt_data(SIMPLE_REF_PATH.read_bytes()).decode("utf-8", errors="strict")
        root = ET.fromstring(xml_str)
        if root.find("NETWORK") is None:
            raise ValueError("Invalid base template: missing NETWORK")
        return root

    def _load_template_root_for_device_type(self, device_type: str) -> ET.Element:
        """
        Carica il template specifico del device type.
        Usato solo per estrarre il link template prototype.
        """
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
        return ET.fromstring(DEFAULT_LINK_TEMPLATE_XML)

    def generate(
        self,
        devices_config: list[dict[str, Any]],
        links_config: Optional[list[dict[str, Any]]] = None,
        output_path: str = "output.pkt",
    ) -> str:
        # Usa sempre simple_ref.pkt come base strutturale
        root = self._load_base_template()
        self.template_root = root

        # Estrai il link template dal template specifico del primo device
        base_type = str(devices_config[0].get("type", "router-2port")) if devices_config else "router-2port"
        try:
            device_specific_root = self._load_template_root_for_device_type(base_type)
            self.link_template = self._extract_link_template(device_specific_root)
        except Exception:
            self.link_template = self._extract_link_template(root)

        # NON modificare il PHYSICALWORKSPACE — tenerlo esattamente come in simple_ref.pkt
        # PhysicalWorkspaceOps era la causa del "corrupted Physical Workspace"
        self._physical_ops = None

        network = root.find("NETWORK")
        if network is None:
            raise ValueError("Template clone error: missing NETWORK")

        devices_elem = ensure_child(network, "DEVICES")
        links_elem = ensure_child(network, "LINKS")
        devices_elem.clear()
        links_elem.clear()

        # Applica layout coordinato
        apply_hierarchical_layout(devices_config, links_config or [])

        self._device_types_by_name = {}

        num_devices = len(devices_config)
        cols = 2 if num_devices <= 4 else 3 if num_devices <= 9 else 4
        used_macs: set[str] = set()
        used_dev_addrs: set[str] = set()
        used_mem_addrs: set[str] = set()
        device_saverefs: dict[str, str] = {}
        device_dev_addrs: dict[str, str] = {}
        port_mem_addrs: dict[tuple[str, str], str] = {}

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
            except Exception as exc:
                logger.warning("Skipping device %s: %s", dev_cfg.get("name"), exc)
                continue

            devices_elem.append(new_device)
            device_saverefs[name] = saveref
            dev_addr = (new_device.findtext("WORKSPACE/LOGICAL/DEV_ADDR") or "").strip()
            if dev_addr:
                device_dev_addrs[name] = dev_addr
            self._device_types_by_name[name] = category

        requested_links = len(links_config or [])
        if links_config:
            for link_cfg in links_config:
                create_link(
                    links_elem=links_elem,
                    link_template=self.link_template,
                    link_cfg=link_cfg,
                    device_saverefs=device_saverefs,
                    get_device_type=self._get_device_type,
                    device_dev_addrs=device_dev_addrs,
                    port_mem_addrs=port_mem_addrs,
                )

        created_links = len(links_elem.findall("LINK"))
        if requested_links and created_links == 0:
            logger.warning("Requested %s links but generated 0 valid LINK nodes", requested_links)
        # ── PHYSICALWORKSPACE ──────────────────────────────────────────
        # Create unique physical nodes for each device to avoid conflicts.
        pw = root.find("PHYSICALWORKSPACE")
        if pw is not None:
            rack_node = pw.find(".//NODE[UUID_STR='{3c62e9ba-4250-4543-8361-a3e10dbc57c1}']")
            if rack_node is not None:
                # Get the base path from the rack up to the root
                parent_map = {c: p for p in pw.iter() for c in p}
                
                def get_path_to_node(node):
                    path = []
                    curr = node
                    while curr in parent_map:
                        path.insert(0, curr)
                        curr = parent_map[curr]
                    if path:
                        path.insert(0, curr) # add root
                    return path

                rack_path_nodes = get_path_to_node(rack_node)
                rack_path_uuids = [n.findtext('UUID_STR') for n in rack_path_nodes if n.findtext('UUID_STR')]

                for device_element in devices_elem.findall("DEVICE"):
                    import uuid
                    new_uuid = str(uuid.uuid4())
                    
                    # Create a new NODE for the device
                    new_node = ET.Element("NODE")
                    set_text(new_node, "TYPE", "6")
                    set_text(new_node, "NAME", device_element.findtext("ENGINE/NAME"))
                    set_text(new_node, "UUID_STR", f"{{{new_uuid}}}")
                    # Add other necessary fields for a device node if any
                    set_text(new_node, "X", "0")
                    set_text(new_node, "Y", "0")
                    set_text(new_node, "SX", "1")
                    set_text(new_node, "SY", "1")

                    children = rack_node.find("CHILDREN")
                    if children is None:
                        children = ET.SubElement(rack_node, "CHILDREN")
                    children.append(new_node)
                    
                    # Construct the full physical path
                    full_path_uuids = rack_path_uuids + [f'{{{new_uuid}}}']
                    physical_path_str = ",".join(full_path_uuids)

                    ws = device_element.find("WORKSPACE")
                    if ws is not None:
                        set_text(ws, "PHYSICAL", physical_path_str)

        # Serializza e correggi self-closing tags (PT non li accetta)
        xml_str = ET.tostring(root, encoding="unicode", method="xml")
        xml_str = _expand_self_closing_tags(xml_str)
        xml_bytes = xml_str.encode("utf-8")

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
        pass  # PhysicalWorkspaceOps disabilitato

    def _sync_physical_workspace(self, root: ET.Element, devices_elem: ET.Element) -> None:
        pass  # PhysicalWorkspaceOps disabilitato

    def _extract_base_physical_paths(self) -> dict[str, list[str]]:
        return {}

    def _extract_base_pw_nodes(self) -> dict[str, ET.Element]:
        return {}

    def _extract_pc_parent_node(self) -> Optional[ET.Element]:
        return None

    def _inject_power_distribution(self, devices_elem: ET.Element) -> None:
        pass  # Non iniettare PDU — non richiesto da PT
