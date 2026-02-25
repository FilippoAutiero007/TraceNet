"""
Core PKT generator logic.
Orchestrates the loading of templates and generation of the network XML.
"""
import copy
import json
import logging
import threading
import xml.etree.ElementTree as ET
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.services.pkt_crypto import decrypt_pkt_data
from app.services.pkt_generator import devices, links, utils

logger = logging.getLogger(__name__)


class PKTGenerator:
    """
    Generator for Cisco Packet Tracer (PKT) files using a template-based approach.
    """

    def __init__(self, template_path: str = "simple_ref.pkt") -> None:
        """
        Initialize the generator by loading the catalog and default template.
        """
        self.template_path = template_path
        try:
            self.default_template_root = self._load_template_file(template_path)
        except Exception as e:
            logger.warning("Could not load default template %s: %s", template_path, e)
            self.default_template_root = None

        # Load Device Catalog
        self.catalog: Dict[str, Any] = {}
        try:
            catalog_path = Path(__file__).parent / "device_catalog.json"
            if catalog_path.exists():
                with open(catalog_path, "r", encoding="utf-8") as f:
                    self.catalog = json.load(f)
            else:
                logger.error("device_catalog.json not found at %s", catalog_path)
        except Exception as e:
            logger.error("Failed to load device catalog: %s", e)

        # Thread-safe cache for loaded device templates
        self._template_cache: Dict[str, ET.Element] = {}
        self._template_cache_lock = threading.Lock()

        # Find link template (from default template)
        self.link_template: Optional[ET.Element] = None
        if self.default_template_root is not None:
            network = self.default_template_root.find("NETWORK")
            if network is not None:
                links_node = network.find("LINKS")
                if links_node is not None:
                    link_list = links_node.findall("LINK")
                    self.link_template = link_list[0] if link_list else None

        # Cache reference physical paths and PW prototype nodes from base template
        self._base_physical_paths: Dict[str, List[str]] = self._extract_base_physical_paths()
        self._base_pw_nodes: Dict[str, ET.Element] = self._extract_base_pw_nodes()
        # Parent per i PC (stesso container di PC0 nel template)
        self._pc_parent_node: Optional[ET.Element] = self._extract_pc_parent_node()

    # ------------------------------------------------------------------
    # Template loading
    # ------------------------------------------------------------------

    def _load_template_file(self, path_str: str) -> ET.Element:
        """Load and decrypt a PKT template file."""
        resolved_path = resolve_path(path_str)
        if not resolved_path:
            raise FileNotFoundError(f"Template not found: {path_str}")

        template_bytes = resolved_path.read_bytes()
        xml_str = decrypt_pkt_data(template_bytes).decode("utf-8", errors="strict")
        return ET.fromstring(xml_str)

    def _get_template_for_device(self, base_template_path: str) -> ET.Element:
        """
        Return a deep-copied DEVICE element from cache, loading from disk if needed.
        Thread-safe via per-instance lock.
        """
        with self._template_cache_lock:
            cached = self._template_cache.get(base_template_path)
            if cached is not None:
                return copy.deepcopy(cached)

        # Load outside the lock to avoid blocking other threads during I/O
        root = self._load_template_file(base_template_path)

        network = root.find("NETWORK")
        if network is not None:
            devices_node = network.find("DEVICES")
            if devices_node is not None:
                device = devices_node.find("DEVICE")
                if device is not None:
                    with self._template_cache_lock:
                        self._template_cache[base_template_path] = device
                    return copy.deepcopy(device)

        raise ValueError(f"Could not find valid DEVICE node in template {base_template_path}")

    # ------------------------------------------------------------------
    # Catalog / device-type resolution
    # ------------------------------------------------------------------

    def resolve_device_type(self, device_type: str) -> Dict[str, Any]:
        """
        Look up device type in catalog.
        Returns metadata dict (including base_template path).
        """
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

    # ------------------------------------------------------------------
    # Main generation entry point
    # ------------------------------------------------------------------

    def generate(
        self,
        devices_config: List[Dict[str, Any]],
        links_config: Optional[List[Dict[str, Any]]] = None,
    ) -> ET.Element:
        """
        Generate a new PKT XML structure based on the provided configuration.
        """
        if self.default_template_root is None:
            raise RuntimeError(
                "Cannot generate PKT: Base template (simple_ref.pkt) failed to load."
            )

        root = copy.deepcopy(self.default_template_root)
        network = root.find("NETWORK")
        if network is None:
            raise ValueError("Corrupted template state: NETWORK node missing in clone")

        devices_elem = utils.ensure_child(network, "DEVICES")
        links_elem = utils.ensure_child(network, "LINKS")
        devices_elem.clear()
        links_elem.clear()

        device_saverefs: Dict[str, str] = {}
        total_devices = len(devices_config)

        # 1. Create Devices
        for idx, dev_cfg in enumerate(devices_config):
            dev_type = str(dev_cfg.get("type", "router")).strip().lower()
            catalog_entry = self.resolve_device_type(dev_type)
            base_template_path = catalog_entry.get("base_template")

            if not base_template_path:
                logger.error("No base_template defined for device type '%s'", dev_type)
                continue

            try:
                template_device = self._get_template_for_device(base_template_path)

                # clone_device è atteso che scriva il saveref assegnato in dev_cfg["_saveref"]
                new_device = devices.clone_device(
                    template_device,
                    idx,
                    dev_cfg,
                    total_devices,
                    meta=catalog_entry,
                )
                devices_elem.append(new_device)

                name = dev_cfg.get("name")
                saveref = dev_cfg.get("_saveref")
                if name and saveref:
                    device_saverefs[name] = saveref
                elif name:
                    logger.warning(
                        "clone_device did not populate '_saveref' for device '%s'; "
                        "links involving this device may not resolve correctly.",
                        name,
                    )

            except Exception as e:
                logger.error("Failed to create device '%s': %s", dev_cfg.get("name"), e)

        # 2. Create Links
        if links_config and self.link_template is not None:
            for link_cfg in links_config:
                new_link = links.create_link(self.link_template, link_cfg, device_saverefs)
                if new_link is not None:
                    links_elem.append(new_link)

        # 3. Keep PHYSICALWORKSPACE in sync with device workspace GUIDs
        self._sync_physical_workspace(root, devices_elem)

        return root

    # ------------------------------------------------------------------
    # Physical workspace helpers
    # ------------------------------------------------------------------

    def _extract_base_physical_paths(self) -> Dict[str, List[str]]:
        """
        Extract the PHYSICAL path lists from the default template devices.
        These act as the canonical hierarchy for the global Physical Workspace.
        """
        paths: Dict[str, List[str]] = {}
        if self.default_template_root is None:
            return paths

        devices_node = self.default_template_root.find("NETWORK/DEVICES")
        if devices_node is None:
            return paths

        for dev in devices_node:
            type_elem = dev.find("ENGINE/TYPE")
            phys_elem = dev.find("WORKSPACE/PHYSICAL")
            if phys_elem is None or phys_elem.text is None:
                continue

            raw_type = (type_elem.text if type_elem is not None else "").lower()
            key = (
                "pc"
                if "pc" in raw_type or "server" in raw_type else
                "switch"
                if "switch" in raw_type else
                "router"
                if "router" in raw_type else
                None
            )
            if key is None:
                continue

            path_parts = [p.strip("{} ") for p in phys_elem.text.split(",") if p.strip()]
            paths[key] = path_parts

        return paths

    def _extract_base_pw_nodes(self) -> Dict[str, ET.Element]:
        """
        Grab prototype PHYSICALWORKSPACE NODE entries for router / switch / pc.
        Searches the whole PW tree so nested PC0 prototypes are found too.
        """
        nodes: Dict[str, ET.Element] = {}
        if self.default_template_root is None:
            return nodes

        pw = self.default_template_root.find("PHYSICALWORKSPACE")
        if pw is None:
            return nodes

        for node in pw.iter("NODE"):
            name_elem = node.find("NAME")
            if name_elem is None or name_elem.text is None:
                continue
            raw = name_elem.text.lower()
            key = (
                "router"
                if "router0" in raw else
                "switch"
                if "switch0" in raw else
                "pc"
                if "pc0" in raw else
                None
            )
            if key and key not in nodes:
                nodes[key] = copy.deepcopy(node)

        return nodes

    def _extract_pc_parent_node(self) -> Optional[ET.Element]:
        """
        Trova il NODE padre che contiene PC0 nel PHYSICALWORKSPACE di base.
        I nuovi PC verranno aggiunti come fratelli lì, non dentro il Rack.
        """
        if self.default_template_root is None:
            return None

        pw = self.default_template_root.find("PHYSICALWORKSPACE")
        if pw is None:
            return None

        def find_parent_of_pc0(parent: ET.Element) -> Optional[ET.Element]:
            for child in list(parent):
                if child.tag == "NODE":
                    name = child.findtext("NAME")
                    if name and name.strip() == "PC0":
                        return parent
                found = find_parent_of_pc0(child)
                if found is not None:
                    return found
            return None

        return find_parent_of_pc0(pw)

    def _sync_physical_workspace(
        self,
        root: ET.Element,
        devices_elem: ET.Element,
    ) -> None:
        """
        Allinea ogni device (WORKSPACE/PHYSICAL) con il PHYSICALWORKSPACE globale.
        Per ogni device:
        - genera un nuovo GUID fisico,
        - aggiorna il path in WORKSPACE/PHYSICAL,
        - trova o crea il NODE corrispondente in PHYSICALWORKSPACE
            (PC sotto il parent di PC0, router/switch nel Rack),
        - sincronizza UUID_STR con il GUID fisico.
        """
        if not self._base_physical_paths:
            return

        pw = root.find("PHYSICALWORKSPACE")
        if pw is None:
            return

        def find_pc_parent(node: ET.Element) -> Optional[ET.Element]:
            for child in list(node):
                if child.tag == "NODE":
                    name = child.findtext("NAME")
                    if name and name.strip() == "PC0":
                        return node
                found = find_pc_parent(child)
                if found is not None:
                    return found
            return None

        # Nodo Rack (per router/switch e fallback)
        rack_node: Optional[ET.Element] = None
        for node in pw.iter("NODE"):
            name = (node.findtext("NAME") or "").strip()
            if name == "Rack":
                rack_node = node
                break

        # Parent dei PC nel PHYSICALWORKSPACE corrente (non quello della base)
        pc_parent_node = find_pc_parent(pw)

        # Index: NAME -> NODE esistente
        pw_nodes: Dict[str, ET.Element] = {}
        for node in pw.iter("NODE"):
            name = (node.findtext("NAME") or "").strip()
            if name:
                pw_nodes[name] = node

        for dev in devices_elem:
            name_elem = dev.find("ENGINE/NAME")
            type_elem = dev.find("ENGINE/TYPE")
            phys_elem = dev.find("WORKSPACE/PHYSICAL")
            if name_elem is None or type_elem is None or phys_elem is None:
                continue

            dname = name_elem.text or ""
            dtype = (type_elem.text or "").lower()

            if not dname:
                continue

            # pc/server -> "pc", switch -> "switch", router -> "router"
            if "pc" in dtype or "server" in dtype:
                base_key = "pc"
            elif "switch" in dtype:
                base_key = "switch"
            elif "router" in dtype:
                base_key = "router"
            else:
                # Tipo non mappato: non tocchiamo il PHYSICALWORKSPACE
                continue
            logger.info("SYNC_PW device %s type %s base_key %s", dname, dtype, base_key)

            base_path = self._base_physical_paths.get(base_key, [])
            if not base_path:
                continue

            # GUID nuovo e path fisico aggiornato nel device
            new_guid = str(uuid.uuid4())
            new_path = base_path[:-1] + [new_guid]
            phys_elem.text = ",".join(f"{{{p}}}" for p in new_path)

            # Nodo fisico corrispondente (crea se manca)
            pw_node = pw_nodes.get(dname)
            if pw_node is None:
                proto = self._base_pw_nodes.get(base_key)
                if proto is not None:
                    pw_node = copy.deepcopy(proto)

                    # Nome aggiornato sul clone
                    name_field = pw_node.find("NAME")
                    if name_field is not None:
                        name_field.text = dname

                    # PC -> stesso parent di PC0; router/switch -> Rack
                    if base_key == "pc" and pc_parent_node is not None:
                        parent_node = pc_parent_node
                    else:
                        parent_node = rack_node

                    if parent_node is not None:
                        if parent_node.tag == "CHILDREN":
                            siblings = parent_node
                        else:
                            siblings = parent_node.find("CHILDREN")
                            if siblings is None:
                                siblings = ET.SubElement(parent_node, "CHILDREN")

                        existing_named = [
                            n for n in siblings.findall("NODE")
                            if (n.findtext("NAME") or "").strip()
                            and (n.findtext("NAME") or "").lower().startswith(base_key)
                        ]
                        base_x = float(pw_node.findtext("X", default="0"))
                        step_x = 86.0 if base_key == "pc" else 120.0
                        x_elem = pw_node.find("X")
                        if x_elem is not None:
                            x_elem.text = str(base_x + step_x * len(existing_named))

                        siblings.append(pw_node)
                        pw_nodes[dname] = pw_node

            if pw_node is not None:
                uuid_elem = pw_node.find("UUID_STR")
                if uuid_elem is None:
                    uuid_elem = ET.SubElement(pw_node, "UUID_STR")
                uuid_elem.text = f"{{{new_guid}}}"


# ---------------------------------------------------------------------------
# Module-level singleton factory (thread-safe double-checked locking)
# ---------------------------------------------------------------------------

_generator_instance: Optional[PKTGenerator] = None
_generator_lock = threading.Lock()


def get_pkt_generator(template_path: str) -> PKTGenerator:
    """
    Return the shared PKTGenerator singleton, creating it on first call.
    Uses double-checked locking so it is safe under concurrent ASGI workers.
    """
    global _generator_instance
    if _generator_instance is None:
        with _generator_lock:
            if _generator_instance is None:
                resolved = resolve_path(template_path)
                path_str = str(resolved) if resolved else template_path
                logger.info(
                    "Initializing PKT generator with base template %s", path_str
                )
                _generator_instance = PKTGenerator(path_str)
    return _generator_instance

# ---------------------------------------------------------------------------
# Path resolution utilities
# ---------------------------------------------------------------------------

def resolve_path(path_str: str) -> Optional[Path]:
    """
    Resolve a file path by checking absolute path, CWD, and standard project layouts.
    The 'templates/' candidates are only appended when the path_str does not already
    contain 'templates' to avoid duplicated entries.
    """
    if not path_str:
        return None

    path = Path(path_str)
    if path.is_absolute() and path.exists():
        return path

    candidates = [
        Path.cwd() / path_str,
        Path.cwd() / "backend" / path_str,
        # Four parents up from app/services/pkt_generator/<this file> → backend/
        Path(__file__).parent.parent.parent.parent / path_str,
    ]

    if "templates" not in path_str:
        candidates.append(Path.cwd() / "templates" / path_str)
        candidates.append(Path.cwd() / "backend" / "templates" / path_str)

    for cand in candidates:
        if cand.exists():
            return cand

    return None


def resolve_template_path() -> Path:
    """Legacy resolver for simple_ref.pkt, kept for compatibility."""
    p = resolve_path("simple_ref.pkt")
    if p:
        return p

    p2 = resolve_path("templates/simple_ref.pkt")
    if p2:
        return p2

    raise FileNotFoundError("simple_ref.pkt template not found.")
