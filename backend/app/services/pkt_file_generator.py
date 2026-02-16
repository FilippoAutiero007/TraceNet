"""
Final PKT Generator - optimized with caching, sanitization and link support.
- Template-based cloning of Packet Tracer PKT
- Device name sanitization
- Grid-based auto-layout to avoid overlaps
- Robust link creation (creates missing FROM/TO/PORT nodes if needed)
- Cached template loader via @lru_cache
"""

from __future__ import annotations

import copy
import logging
import os
import re
import secrets
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import xml.etree.ElementTree as ET

from app.services.pkt_crypto import decrypt_pkt_data, encrypt_pkt_data

logger = logging.getLogger(__name__)

_SAFE_DEVICE_NAME = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


# -----------------------
# Utility helpers
# -----------------------
def _validate_name(name: str) -> str:
    if not isinstance(name, str) or not _SAFE_DEVICE_NAME.fullmatch(name):
        raise ValueError(f"Unsafe device name: {name!r}")
    return name


def _safe_name(prefix: str, index: int) -> str:
    return _validate_name(f"{prefix}{index}")


def _rand_saveref() -> str:
    n = 10**18 + secrets.randbelow(9 * 10**18)
    return f"save-ref-id{n}"


def _rand_memaddr() -> str:
    return str(10**12 + secrets.randbelow(9 * 10**12))


def _ensure_child(parent: ET.Element, tag: str) -> ET.Element:
    child = parent.find(tag)
    if child is None:
        child = ET.SubElement(parent, tag)
    return child


def _set_text(parent: ET.Element, tag: str, value: str, *, create: bool = True) -> None:
    elem = parent.find(tag)
    if elem is None:
        if not create:
            return
        elem = ET.SubElement(parent, tag)
    elem.text = value


# -----------------------
# Generator
# -----------------------
class PKTGenerator:
    def __init__(self, template_path: str = "simple_ref.pkt") -> None:
        template_bytes = Path(template_path).read_bytes()
        xml_str = decrypt_pkt_data(template_bytes).decode("utf-8", errors="strict")
        self.template_root = ET.fromstring(xml_str)

        template_network = self.template_root.find("NETWORK")
        if template_network is None:
            raise ValueError("Invalid template: missing NETWORK node")

        template_devices_node = template_network.find("DEVICES")
        if template_devices_node is None:
            raise ValueError("Invalid template: missing NETWORK/DEVICES node")

        template_devices = template_devices_node.findall("DEVICE")

        self.device_templates: dict[str, ET.Element] = {}
        for device in template_devices:
            engine = device.find("ENGINE")
            if engine is None:
                continue
            dev_type = (engine.findtext("TYPE") or "").strip().lower()
            if dev_type:
                self.device_templates[dev_type] = device

        if "router" not in self.device_templates:
            raise ValueError("Invalid template: no router device template found")

        links_node = template_network.find("LINKS")
        template_links = links_node.findall("LINK") if links_node is not None else []
        self.link_template: Optional[ET.Element] = template_links[0] if template_links else None

    def generate(self, devices_config: list[dict[str, Any]], links_config: Optional[list[dict[str, Any]]] = None,
                 output_path: str = "output.pkt") -> str:
        root = copy.deepcopy(self.template_root)
        network = root.find("NETWORK")
        if network is None:
            raise ValueError("Template clone error: missing NETWORK")

        devices_elem = _ensure_child(network, "DEVICES")
        links_elem = _ensure_child(network, "LINKS")

        devices_elem.clear()
        links_elem.clear()

        # -----------------------
        # GRID layout parameters
        # -----------------------
        num_devices = len(devices_config)
        if num_devices <= 4:
            cols = 2
        elif num_devices <= 9:
            cols = 3
        else:
            cols = 4

        device_saverefs: dict[str, str] = {}

        # -----------------------
        # Devices
        # -----------------------
        for idx, dev_cfg in enumerate(devices_config):
            name = _validate_name(dev_cfg["name"])
            dev_type = str(dev_cfg.get("type", "router")).strip().lower() or "router"

            template = self.device_templates.get(dev_type) or self.device_templates["router"]
            new_device = copy.deepcopy(template)

            engine = new_device.find("ENGINE")
            if engine is None:
                logger.warning("Skipping device %s: missing ENGINE in template", name)
                continue

            _set_text(engine, "NAME", name, create=True)
            _set_text(engine, "SYSNAME", name, create=False)

            saveref = _rand_saveref()
            _set_text(engine, "SAVEREFID", saveref, create=True)
            device_saverefs[name] = saveref

            # Calcola coordinate griglia
            default_x = 200 + (idx % cols) * 250
            default_y = 200 + (idx // cols) * 200

            x = int(dev_cfg.get("x", default_x))
            y = int(dev_cfg.get("y", default_y))

            # Trova o crea COORDSETTINGS
            coords = engine.find("COORDSETTINGS")
            if coords is None:
                coords = ET.SubElement(engine, "COORDSETTINGS")
            _set_text(coords, "XCOORD", str(x), create=True)
            _set_text(coords, "YCOORD", str(y), create=True)

            # Trova o crea WORKSPACE e aggiorna coordinate
            workspace = engine.find("WORKSPACE")
            if workspace is None:
                workspace = ET.SubElement(engine, "WORKSPACE")
            _set_text(workspace, "XCOORD", str(x), create=True)
            _set_text(workspace, "YCOORD", str(y), create=True)

            ip = dev_cfg.get("ip")
            if ip:
                self._update_device_ip(engine, dev_cfg)

            devices_elem.append(new_device)

        # -----------------------
        # Links
        # -----------------------
        if links_config:
            for link_cfg in links_config:
                self._create_link(links_elem, link_cfg, device_saverefs)

        xml_bytes = b'<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(root, encoding="utf-8", method="xml")
        encrypted = encrypt_pkt_data(xml_bytes)
        Path(output_path).write_bytes(encrypted)

        return output_path

    def _update_device_ip(self, engine: ET.Element, dev_cfg: dict[str, Any]) -> None:
        module = engine.find("MODULE")
        if module is None:
            return

        slots = module.findall("SLOT")
        if not slots:
            return

        slot_module = slots[0].find("MODULE")
        if slot_module is None:
            return

        port = slot_module.find("PORT")
        if port is None:
            return

        _set_text(port, "IP", str(dev_cfg.get("ip", "")), create=True)
        _set_text(port, "SUBNET", str(dev_cfg.get("subnet", "255.255.255.0")), create=True)
        _set_text(port, "POWER", "true", create=True)
        _set_text(port, "UPMETHOD", "3", create=True)

    def _create_link(self, links_elem: ET.Element, link_cfg: dict[str, Any], device_saverefs: dict[str, str]) -> None:
        if self.link_template is None:
            logger.warning("No link template available; skipping link %s", link_cfg)
            return

        from_name = _validate_name(str(link_cfg["from"]))
        to_name = _validate_name(str(link_cfg["to"]))

        from_saveref = device_saverefs.get(from_name)
        to_saveref = device_saverefs.get(to_name)

        if not from_saveref or not to_saveref:
            logger.warning("Device not found for link: %s", link_cfg)
            return

        link = copy.deepcopy(self.link_template)

        # Ensure FROM/TO exist
        _set_text(link, "FROM", from_saveref, create=True)
        _set_text(link, "TO", to_saveref, create=True)

        # Ensure at least 2 PORT nodes
        ports = link.findall("PORT")
        while len(ports) < 2:
            ports.append(ET.SubElement(link, "PORT"))

        ports[0].text = str(link_cfg.get("from_port", "FastEthernet0/0"))
        ports[1].text = str(link_cfg.get("to_port", "FastEthernet0/1"))

        # Set memaddr fields (create if missing)
        for tag in ("FROMDEVICEMEMADDR", "TODEVICEMEMADDR", "FROMPORTMEMADDR", "TOPORTMEMADDR"):
            _set_text(link, tag, _rand_memaddr(), create=True)

        links_elem.append(link)


# -----------------------
# Cached loader + template path
# -----------------------
@lru_cache(maxsize=1)
def get_pkt_generator(template_path: str) -> PKTGenerator:
    logger.info("Loading PKT generator template in cache from %s", template_path)
    return PKTGenerator(template_path)


def get_template_path() -> Path:
    env_template = os.environ.get("PKT_TEMPLATE_PATH")
    if env_template and Path(env_template).exists():
        return Path(env_template)

    docker_path = Path("/app/templates/simple_ref.pkt")
    if docker_path.exists():
        return docker_path

    candidate = Path(__file__).resolve().parent.parent.parent / "templates" / "simple_ref.pkt"
    if candidate.exists():
        return candidate

    candidate = Path.cwd() / "backend" / "templates" / "simple_ref.pkt"
    if candidate.exists():
        return candidate

    raise FileNotFoundError("simple_ref.pkt template not found. Set PKT_TEMPLATE_PATH env variable.")


# -----------------------
# Topology helpers
# -----------------------
def build_links_config(num_routers: int, num_switches: int, num_pcs: int) -> list[dict[str, str]]:
    links_config: list[dict[str, str]] = []

    if num_routers > 0 and num_switches > 0:
        for i in range(min(num_routers, num_switches)):
            links_config.append({
                "from": _safe_name("Router", i),
                "from_port": "FastEthernet0/0",
                "to": _safe_name("Switch", i),
                "to_port": "FastEthernet0/1",
            })

        if num_switches > num_routers:
            for i in range(num_routers, num_switches):
                port_idx = i - num_routers + 1
                links_config.append({
                    "from": _safe_name("Router", num_routers - 1),
                    "from_port": f"FastEthernet0/{port_idx}",
                    "to": _safe_name("Switch", i),
                    "to_port": "FastEthernet0/1",
                })

    if num_switches > 0:
        for pc_idx in range(num_pcs):
            switch_idx = pc_idx % num_switches
            port_num = (pc_idx // num_switches) + 2
            links_config.append({
                "from": _safe_name("Switch", switch_idx),
                "from_port": f"FastEthernet{port_num}/1",
                "to": _safe_name("PC", pc_idx),
                "to_port": "FastEthernet0",
            })

    return links_config


# -----------------------
# Main entrypoint
# -----------------------
def save_pkt_file(subnets: list, config: dict[str, Any], output_dir: str) -> dict[str, Any]:
    logger.info("Generating PKT file with template-based approach")

    try:
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        pkt_filename = f"network_{timestamp}.pkt"
        xml_filename = f"network_{timestamp}.xml"

        pkt_path = str(Path(output_dir) / pkt_filename)
        xml_path = str(Path(output_dir) / xml_filename)

        template_path = str(get_template_path())
        generator = get_pkt_generator(template_path)

        device_counts = config.get("devices", {})
        num_routers = int(device_counts.get("routers", 1))
        num_switches = int(device_counts.get("switches", 1))
        num_pcs = int(device_counts.get("pcs", 0))

        # IMPORTANT: no x/y here -> grid handled in generator.generate()
        devices_config: list[dict[str, Any]] = []

        for i in range(num_routers):
            devices_config.append({"name": _safe_name("Router", i), "type": "router"})

        for i in range(num_switches):
            devices_config.append({"name": _safe_name("Switch", i), "type": "switch"})

        pc_idx = 0
        for subnet in subnets:
            subnet_pcs = min(3, max(0, num_pcs - pc_idx))
            for i in range(subnet_pcs):
                if pc_idx >= num_pcs:
                    break
                usable = getattr(subnet, "usable_range", [])
                ip = usable[i] if i < len(usable) else ""
                devices_config.append({
                    "name": _safe_name("PC", pc_idx),
                    "type": "pc",
                    "ip": ip,
                    "subnet": getattr(subnet, "mask", "255.255.255.0"),
                })
                pc_idx += 1

        while pc_idx < num_pcs:
            devices_config.append({"name": _safe_name("PC", pc_idx), "type": "pc"})
            pc_idx += 1

        links_config = build_links_config(num_routers, num_switches, num_pcs)
        logger.info("Generating %s devices and %s links", len(devices_config), len(links_config))

        generator.generate(devices_config, links_config=links_config, output_path=pkt_path)

        # Export XML of the GENERATED PKT (not the template)
        pkt_bytes
    return name


def _safe_name(prefix: str, index: int) -> str:
    return _validate_name(f"{prefix}{index}")


def _rand_saveref() -> str:
    n = 10**18 + secrets.randbelow(9 * 10**18)
    return f"save-ref-id{n}"


def _rand_memaddr() -> str:
    return str(10**12 + secrets.randbelow(9 * 10**12))


def _ensure_child(parent: ET.Element, tag: str) -> ET.Element:
    child = parent.find(tag)
    if child is None:
        child = ET.SubElement(parent, tag)
    return child


def _set_text(parent: ET.Element, tag: str, value: str, *, create: bool = True) -> None:
    elem = parent.find(tag)
    if elem is None:
        if not create:
            return
        elem = ET.SubElement(parent, tag)
    elem.text = value


# -----------------------
# Generator
# -----------------------
class PKTGenerator:
    def __init__(self, template_path: str = "simple_ref.pkt") -> None:
        template_bytes = Path(template_path).read_bytes()
        xml_str = decrypt_pkt_data(template_bytes).decode("utf-8", errors="strict")
        self.template_root = ET.fromstring(xml_str)

        template_network = self.template_root.find("NETWORK")
        if template_network is None:
            raise ValueError("Invalid template: missing NETWORK node")

        template_devices_node = template_network.find("DEVICES")
        if template_devices_node is None:
            raise ValueError("Invalid template: missing NETWORK/DEVICES node")

        template_devices = template_devices_node.findall("DEVICE")

        self.device_templates: dict[str, ET.Element] = {}
        for device in template_devices:
            engine = device.find("ENGINE")
            if engine is None:
                continue
            dev_type = (engine.findtext("TYPE") or "").strip().lower()
            if dev_type:
                self.device_templates[dev_type] = device

        if "router" not in self.device_templates:
            raise ValueError("Invalid template: no router device template found")

        links_node = template_network.find("LINKS")
        template_links = links_node.findall("LINK") if links_node is not None else []
        self.link_template: Optional[ET.Element] = template_links[0] if template_links else None

    def generate(self, devices_config: list[dict[str, Any]], links_config: Optional[list[dict[str, Any]]] = None,
                 output_path: str = "output.pkt") -> str:
        root = copy.deepcopy(self.template_root)
        network = root.find("NETWORK")
        if network is None:
            raise ValueError("Template clone error: missing NETWORK")

        devices_elem = _ensure_child(network, "DEVICES")
        links_elem = _ensure_child(network, "LINKS")

        devices_elem.clear()
        links_elem.clear()

        # -----------------------
        # GRID layout parameters
        # -----------------------
        num_devices = len(devices_config)
        if num_devices <= 4:
            cols = 2
        elif num_devices <= 9:
            cols = 3
        else:
            cols = 4

        device_saverefs: dict[str, str] = {}

        # -----------------------
        # Devices
        # -----------------------
        for idx, dev_cfg in enumerate(devices_config):
            name = _validate_name(dev_cfg["name"])
            dev_type = str(dev_cfg.get("type", "router")).strip().lower() or "router"

            template = self.device_templates.get(dev_type) or self.device_templates["router"]
            new_device = copy.deepcopy(template)

            engine = new_device.find("ENGINE")
            if engine is None:
                logger.warning("Skipping device %s: missing ENGINE in template", name)
                continue

            _set_text(engine, "NAME", name, create=True)
            _set_text(engine, "SYSNAME", name, create=False)

            saveref = _rand_saveref()
            _set_text(engine, "SAVEREFID", saveref, create=True)
            device_saverefs[name] = saveref

            # Calcola coordinate griglia
            default_x = 200 + (idx % cols) * 250
            default_y = 200 + (idx // cols) * 200

            x = int(dev_cfg.get("x", default_x))
            y = int(dev_cfg.get("y", default_y))

            # Trova o crea COORDSETTINGS
            coords = engine.find("COORDSETTINGS")
            if coords is None:
                    coords = ET.SubElement(engine, "COORDSETTINGS")

            _set_text(coords, "XCOORD", str(x), create=True)
            _set_text(coords, "YCOORD", str(y), create=True)

            ip = dev_cfg.get("ip")
            if ip:
                self._update_device_ip(engine, dev_cfg)

            devices_elem.append(new_device)

        # -----------------------
        # Links
        # -----------------------
        if links_config:
            for link_cfg in links_config:
                self._create_link(links_elem, link_cfg, device_saverefs)

        xml_bytes = b'<?xml version="1.0" encoding="utf-8"?>\n' + ET.tostring(root, encoding="utf-8", method="xml")
        encrypted = encrypt_pkt_data(xml_bytes)
        Path(output_path).write_bytes(encrypted)

        return output_path

    def _update_device_ip(self, engine: ET.Element, dev_cfg: dict[str, Any]) -> None:
        module = engine.find("MODULE")
        if module is None:
            return

        slots = module.findall("SLOT")
        if not slots:
            return

        slot_module = slots[0].find("MODULE")
        if slot_module is None:
            return

        port = slot_module.find("PORT")
        if port is None:
            return

        _set_text(port, "IP", str(dev_cfg.get("ip", "")), create=True)
        _set_text(port, "SUBNET", str(dev_cfg.get("subnet", "255.255.255.0")), create=True)
        _set_text(port, "POWER", "true", create=True)
        _set_text(port, "UPMETHOD", "3", create=True)

    def _create_link(self, links_elem: ET.Element, link_cfg: dict[str, Any], device_saverefs: dict[str, str]) -> None:
        if self.link_template is None:
            logger.warning("No link template available; skipping link %s", link_cfg)
            return

        from_name = _validate_name(str(link_cfg["from"]))
        to_name = _validate_name(str(link_cfg["to"]))

        from_saveref = device_saverefs.get(from_name)
        to_saveref = device_saverefs.get(to_name)

        if not from_saveref or not to_saveref:
            logger.warning("Device not found for link: %s", link_cfg)
            return

        link = copy.deepcopy(self.link_template)

        # Ensure FROM/TO exist
        _set_text(link, "FROM", from_saveref, create=True)
        _set_text(link, "TO", to_saveref, create=True)

        # Ensure at least 2 PORT nodes
        ports = link.findall("PORT")
        while len(ports) < 2:
            ports.append(ET.SubElement(link, "PORT"))

        ports[0].text = str(link_cfg.get("from_port", "FastEthernet0/0"))
        ports[1].text = str(link_cfg.get("to_port", "FastEthernet0/1"))

        # Set memaddr fields (create if missing)
        for tag in ("FROMDEVICEMEMADDR", "TODEVICEMEMADDR", "FROMPORTMEMADDR", "TOPORTMEMADDR"):
            _set_text(link, tag, _rand_memaddr(), create=True)

        links_elem.append(link)


# -----------------------
# Cached loader + template path
# -----------------------
@lru_cache(maxsize=1)
def get_pkt_generator(template_path: str) -> PKTGenerator:
    logger.info("Loading PKT generator template in cache from %s", template_path)
    return PKTGenerator(template_path)


def get_template_path() -> Path:
    env_template = os.environ.get("PKT_TEMPLATE_PATH")
    if env_template and Path(env_template).exists():
        return Path(env_template)

    docker_path = Path("/app/templates/simple_ref.pkt")
    if docker_path.exists():
        return docker_path

    candidate = Path(__file__).resolve().parent.parent.parent / "templates" / "simple_ref.pkt"
    if candidate.exists():
        return candidate

    candidate = Path.cwd() / "backend" / "templates" / "simple_ref.pkt"
    if candidate.exists():
        return candidate

    raise FileNotFoundError("simple_ref.pkt template not found. Set PKT_TEMPLATE_PATH env variable.")


# -----------------------
# Topology helpers
# -----------------------
def build_links_config(num_routers: int, num_switches: int, num_pcs: int) -> list[dict[str, str]]:
    links_config: list[dict[str, str]] = []

    if num_routers > 0 and num_switches > 0:
        for i in range(min(num_routers, num_switches)):
            links_config.append({
                "from": _safe_name("Router", i),
                "from_port": "FastEthernet0/0",
                "to": _safe_name("Switch", i),
                "to_port": "FastEthernet0/1",
            })

        if num_switches > num_routers:
            for i in range(num_routers, num_switches):
                port_idx = i - num_routers + 1
                links_config.append({
                    "from": _safe_name("Router", num_routers - 1),
                    "from_port": f"FastEthernet0/{port_idx}",
                    "to": _safe_name("Switch", i),
                    "to_port": "FastEthernet0/1",
                })

    if num_switches > 0:
        for pc_idx in range(num_pcs):
            switch_idx = pc_idx % num_switches
            port_num = (pc_idx // num_switches) + 2
            links_config.append({
                "from": _safe_name("Switch", switch_idx),
                "from_port": f"FastEthernet{port_num}/1",
                "to": _safe_name("PC", pc_idx),
                "to_port": "FastEthernet0",
            })

    return links_config


# -----------------------
# Main entrypoint
# -----------------------
def save_pkt_file(subnets: list, config: dict[str, Any], output_dir: str) -> dict[str, Any]:
    logger.info("Generating PKT file with template-based approach")

    try:
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        pkt_filename = f"network_{timestamp}.pkt"
        xml_filename = f"network_{timestamp}.xml"

        pkt_path = str(Path(output_dir) / pkt_filename)
        xml_path = str(Path(output_dir) / xml_filename)

        template_path = str(get_template_path())
        generator = get_pkt_generator(template_path)

        device_counts = config.get("devices", {})
        num_routers = int(device_counts.get("routers", 1))
        num_switches = int(device_counts.get("switches", 1))
        num_pcs = int(device_counts.get("pcs", 0))

        # IMPORTANT: no x/y here -> grid handled in generator.generate()
        devices_config: list[dict[str, Any]] = []

        for i in range(num_routers):
            devices_config.append({"name": _safe_name("Router", i), "type": "router"})

        for i in range(num_switches):
            devices_config.append({"name": _safe_name("Switch", i), "type": "switch"})

        pc_idx = 0
        for subnet in subnets:
            subnet_pcs = min(3, max(0, num_pcs - pc_idx))
            for i in range(subnet_pcs):
                if pc_idx >= num_pcs:
                    break
                usable = getattr(subnet, "usable_range", [])
                ip = usable[i] if i < len(usable) else ""
                devices_config.append({
                    "name": _safe_name("PC", pc_idx),
                    "type": "pc",
                    "ip": ip,
                    "subnet": getattr(subnet, "mask", "255.255.255.0"),
                })
                pc_idx += 1

        while pc_idx < num_pcs:
            devices_config.append({"name": _safe_name("PC", pc_idx), "type": "pc"})
            pc_idx += 1

        links_config = build_links_config(num_routers, num_switches, num_pcs)
        logger.info("Generating %s devices and %s links", len(devices_config), len(links_config))

        generator.generate(devices_config, links_config=links_config, output_path=pkt_path)

        # Export XML of the GENERATED PKT (not the template)
        pkt_bytes = Path(pkt_path).read_bytes()
        generated_xml = decrypt_pkt_data(pkt_bytes).decode("utf-8", errors="strict")
        Path(xml_path).write_text(generated_xml, encoding="utf-8")

        file_size = Path(pkt_path).stat().st_size
        return {
            "success": True,
            "pkt_path": pkt_path,
            "xml_path": xml_path,
            "encoding_used": "template_based",
            "file_size": file_size,
            "pka2xml_available": False,
            "method": "template_cloning",
        }

    except Exception as exc:
        logger.error("PKT generation failed: %s", exc, exc_info=True)
        return {"success": False, "error": str(exc)}
