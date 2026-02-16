"""Final PKT Generator - optimized with caching, sanitization and link support."""

import copy
import logging
import os
import random
import re
import sys
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

import xml.etree.ElementTree as ET

from app.services.pkt_crypto import decrypt_pkt_data, encrypt_pkt_data

sys.path.insert(0, '.')

logger = logging.getLogger(__name__)
_SAFE_DEVICE_NAME = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class PKTGenerator:
    def __init__(self, template_path: str = 'simple_ref.pkt'):
        with open(template_path, 'rb') as file_handle:
            encrypted = file_handle.read()

        xml_str = decrypt_pkt_data(encrypted).decode('utf-8')
        self.template_root = ET.fromstring(xml_str)

        template_network = self.template_root.find('NETWORK')
        template_devices = template_network.find('DEVICES').findall('DEVICE')

        self.device_templates = {}
        for device in template_devices:
            engine = device.find('ENGINE')
            dev_type = engine.find('TYPE').text.lower()
            self.device_templates[dev_type] = device

        template_links = template_network.find('LINKS').findall('LINK')
        self.link_template = template_links[0] if template_links else None

    def generate(self, devices_config, links_config=None, output_path='output.pkt'):
        root = copy.deepcopy(self.template_root)
        network = root.find('NETWORK')
        devices_elem = network.find('DEVICES')
        links_elem = network.find('LINKS')

        devices_elem.clear()
        links_elem.clear()

        device_saverefs = {}

        for idx, dev_cfg in enumerate(devices_config):
            dev_type = dev_cfg.get('type', 'router').lower()
            template = self.device_templates.get(dev_type) or self.device_templates.get('router')

            new_device = copy.deepcopy(template)
            engine = new_device.find('ENGINE')

            engine.find('NAME').text = dev_cfg['name']
            sysname = engine.find('SYSNAME')
            if sysname is not None:
                sysname.text = dev_cfg['name']

            new_saverefid = f"save-ref-id{random.randint(10**18, 10**19)}"
            saverefid_elem = engine.find('SAVEREFID')
            if saverefid_elem is not None:
                saverefid_elem.text = new_saverefid
            else:
                ET.SubElement(engine, 'SAVEREFID').text = new_saverefid

            device_saverefs[dev_cfg['name']] = new_saverefid

                     coords = engine.find('COORDSETTINGS')
            if coords is not None:
                # Determina automaticamente il numero di colonne in base ai dispositivi
                num_devices = len(devices_config)
                if num_devices <= 4:
                    cols = 2  # Griglia 2 colonne per pochi dispositivi
                elif num_devices <= 9:
                    cols = 3  # Griglia 3 colonne per numero medio
                else:
                    cols = 4  # Griglia 4 colonne per molti dispositivi
                
                coords.find('XCOORD').text = str(dev_cfg.get('x', 200 + (idx % cols) * 250))
                coords.find('YCOORD').text = str(dev_cfg.get('y', 200 + (idx // cols) * 200))



            if 'ip' in dev_cfg:
                self._update_device_ip(engine, dev_cfg)

            devices_elem.append(new_device)

        if links_config:
            for link_cfg in links_config:
                self._create_link(links_elem, link_cfg, device_saverefs)

        xml_str = '<?xml version="1.0" encoding="utf-8"?>\n'
        xml_str += ET.tostring(root, encoding='unicode', method='xml')

        encrypted = encrypt_pkt_data(xml_str.encode('utf-8'))

        with open(output_path, 'wb') as file_handle:
            file_handle.write(encrypted)

        return output_path

    def _update_device_ip(self, engine, dev_cfg):
        module = engine.find('MODULE')
        if module is None:
            return

        slots = module.findall('SLOT')
        if not slots:
            return

        slot_module = slots[0].find('MODULE')
        if slot_module is None:
            return

        port = slot_module.find('PORT')
        if port is None:
            return

        for tag, value in [
            ('IP', dev_cfg.get('ip', '')),
            ('SUBNET', dev_cfg.get('subnet', '255.255.255.0')),
            ('POWER', 'true'),
            ('UPMETHOD', '3'),
        ]:
            elem = port.find(tag)
            if elem is not None:
                elem.text = value

    def _create_link(self, links_elem, link_cfg, device_saverefs):
        if not self.link_template:
            logger.warning("No link template available")
            return

        link = copy.deepcopy(self.link_template)

        from_saveref = device_saverefs.get(link_cfg['from'])
        to_saveref = device_saverefs.get(link_cfg['to'])

        if not from_saveref or not to_saveref:
            logger.warning("Device not found for link: %s", link_cfg)
            return

           # Verifica e creazione elementi FROM/TO se mancanti
        from_elem = link.find('FROM')
        to_elem = link.find('TO')
        
        if from_elem is None:
            logger.warning("Link template missing FROM element, creating it")
            from_elem = ET.SubElement(link, 'FROM')
        if to_elem is None:
            logger.warning("Link template missing TO element, creating it")
            to_elem = ET.SubElement(link, 'TO')
        
        from_elem.text = from_saveref
        to_elem.text = to_saveref

        ports = link.findall('PORT')
        if len(ports) >= 2:
            ports[0].text = link_cfg.get('from_port', 'FastEthernet0/0')
            ports[1].text = link_cfg.get('to_port', 'FastEthernet0/1')

        for tag in ['FROMDEVICEMEMADDR', 'TODEVICEMEMADDR', 'FROMPORTMEMADDR', 'TOPORTMEMADDR']:
            elem = link.find(tag)
            if elem is not None:
                elem.text = str(random.randint(10**12, 10**13))

        links_elem.append(link)


@lru_cache(maxsize=1)
def get_pkt_generator(template_path: str) -> PKTGenerator:
    logger.info("Loading PKT generator template in cache from %s", template_path)
    return PKTGenerator(template_path)


def get_template_path() -> Path:
    env_template = os.environ.get("PKT_TEMPLATE_PATH")
    if env_template and Path(env_template).exists():
        return Path(env_template)

    # Priorità 1: Path assoluto standard in Docker
    docker_path = Path("/app/templates/simple_ref.pkt")
    if docker_path.exists():
        return docker_path

    # Priorità 2: Path relativo al file (struttura repo)
    candidate = Path(__file__).resolve().parent.parent.parent / "templates" / "simple_ref.pkt"
    if candidate.exists():
        return candidate

    # Priorità 3: Path relativo alla working directory
    candidate = Path.cwd() / "backend" / "templates" / "simple_ref.pkt"
    if candidate.exists():
        return candidate

    raise FileNotFoundError("simple_ref.pkt template not found. Set PKT_TEMPLATE_PATH env variable.")


def _safe_name(prefix: str, index: int) -> str:
    candidate = f"{prefix}{index}"
    if not _SAFE_DEVICE_NAME.fullmatch(candidate):
        raise ValueError(f"Unsafe device name generated: {candidate}")
    return candidate


def build_links_config(num_routers: int, num_switches: int, num_pcs: int) -> list[dict[str, str]]:
    links_config: list[dict[str, str]] = []

    if num_routers > 0 and num_switches > 0:
        for i in range(min(num_routers, num_switches)):
            links_config.append({
                'from': _safe_name('Router', i),
                'from_port': 'FastEthernet0/0',
                'to': _safe_name('Switch', i),
                'to_port': 'FastEthernet0/1',
            })

        if num_switches > num_routers:
            for i in range(num_routers, num_switches):
                port_idx = i - num_routers + 1
                links_config.append({
                    'from': _safe_name('Router', num_routers - 1),
                    'from_port': f'FastEthernet0/{port_idx}',
                    'to': _safe_name('Switch', i),
                    'to_port': 'FastEthernet0/1',
                })

    if num_switches > 0:
        for pc_idx in range(num_pcs):
            switch_idx = pc_idx % num_switches
            port_num = (pc_idx // num_switches) + 2
            links_config.append({
                'from': _safe_name('Switch', switch_idx),
                'from_port': f'FastEthernet{port_num}/1',
                'to': _safe_name('PC', pc_idx),
                'to_port': 'FastEthernet0',
            })

    return links_config


def save_pkt_file(subnets: list, config: dict[str, Any], output_dir: str) -> dict[str, Any]:
    logger.info("Generating PKT file with template-based approach")

    try:
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        pkt_filename = f"network_{timestamp}.pkt"
        xml_filename = f"network_{timestamp}.xml"

        pkt_path = os.path.join(output_dir, pkt_filename)
        xml_path = os.path.join(output_dir, xml_filename)

        template_path = str(get_template_path())
        generator = get_pkt_generator(template_path)

        devices_config = []
        device_counts = config.get("devices", {})
        num_routers = int(device_counts.get("routers", 1))
        num_switches = int(device_counts.get("switches", 1))
        num_pcs = int(device_counts.get("pcs", 0))

        # Generazione sicura dei device config
        try:
            for i in range(num_routers):
                devices_config.append({
                    "name": _safe_name("Router", i),
                    "type": "router",
                })

            for i in range(num_switches):
                devices_config.append({
                    "name": _safe_name("Switch", i),
                    "type": "switch",
                })

            pc_idx = 0
            for subnet in subnets:
                subnet_pcs = min(3, num_pcs - pc_idx)
                for i in range(subnet_pcs):
                    if pc_idx >= num_pcs:
                        break
                    ip = subnet.usable_range[i] if i < len(subnet.usable_range) else ""
                    devices_config.append({
                        "name": _safe_name("PC", pc_idx),
                        "type": "pc",
                        "ip": ip,
                        "subnet": subnet.mask,
                    })
                    pc_idx += 1

            while pc_idx < num_pcs:
                devices_config.append({
                    "name": _safe_name("PC", pc_idx),
                    "type": "pc",
                })
                pc_idx += 1

        except Exception as dev_exc:
            logger.error("Error generating device configurations: %s", dev_exc)
            raise ValueError(f"Device configuration failed: {dev_exc}")

        links_config = build_links_config(num_routers, num_switches, num_pcs)
        logger.info("Generating %s devices and %s links", len(devices_config), len(links_config))

        generator.generate(devices_config, links_config=links_config, output_path=pkt_path)

        with open(template_path, 'rb') as file_handle:
            xml_content = decrypt_pkt_data(file_handle.read()).decode('utf-8')
        with open(xml_path, 'w', encoding='utf-8') as xml_handle:
            xml_handle.write(xml_content)

        file_size = os.path.getsize(pkt_path)
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
        return {
            "success": False,
            "error": str(exc),
        }
