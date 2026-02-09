"""
PKT File Generator Service - Creates Cisco Packet Tracer 8.x compatible files

This module orchestrates the complete generation of .pkt files that can be opened
in Cisco Packet Tracer 8.x and later versions.

Process:
1. Build XML structure (using pkt_xml_builder.py)
2. Convert XML to PKT using ptexplorer (NEW APPROACH)
3. Fallback to Twofish/EAX if ptexplorer unavailable

References:
- ptexplorer: Custom module in backend/ptexplorer.py
- pka2xml (mircodz): https://github.com/mircodz/pka2xml
- Unpacket (Punkcake21): https://github.com/Punkcake21/Unpacket

Key improvements:
- Uses ptexplorer for native PT file generation
- No manual encryption needed
- Full compatibility with Packet Tracer
"""

import os
import sys
import logging
import uuid
import struct
from datetime import datetime
from typing import List, Dict, Any
from pathlib import Path

from app.models.schemas import SubnetResult
from app.services.pkt_xml_builder import build_pkt_xml
from app.services.pkt_crypto import encrypt_pkt_data, validate_encryption

# Add backend directory to path to import ptexplorer
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

try:
    from ptexplorer import PTFile
    PTEXPLORER_AVAILABLE = True
except ImportError:
    PTEXPLORER_AVAILABLE = False
    logging.warning("ptexplorer not available - will use fallback encryption")

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_OUTPUT_DIR = "/tmp/tracenet"
DEFAULT_XML_VERSION = "8.2.2.0400"  # PT 8.x version


def build_pkt_from_xml(xml_bytes: bytes, output_path: Path) -> None:
    """
    Converte un XML Packet Tracer in un file .pkt compatibile usando ptexplorer.
    
    Args:
        xml_bytes: contenuto XML in bytes.
        output_path: path completo del file .pkt da generare.
        
    Raises:
        ImportError: se ptexplorer non è disponibile
        Exception: se la conversione fallisce
    """
    if not PTEXPLORER_AVAILABLE:
        raise ImportError("ptexplorer library is not available")
    
    # Crea file XML temporaneo
    tmp_xml = output_path.with_suffix(".tmp.xml")
    tmp_xml.write_bytes(xml_bytes)
    
    try:
        pt = PTFile()
        # Leggi il contenuto XML come stringa UTF-8
        xml_text = tmp_xml.read_text(encoding="utf-8")
        # Carica l'XML nel PTFile
        pt.open_xml(xml_text)
        # Salva il .pkt compatibile con Packet Tracer
        pt.save(str(output_path))
        
        logger.info(f"✅ PTFile successfully created: {output_path}")
    finally:
        # Rimuovi il file temporaneo
        try:
            tmp_xml.unlink()
        except FileNotFoundError:
            pass


def save_pkt_file(subnets: List[SubnetResult], config: Dict[str, Any], output_dir: str = None) -> Dict[str, Any]:
    """
    Generate a complete .pkt file using ptexplorer.
    
    This is the main entry point for PKT file generation. It coordinates:
    1. XML structure building (pkt_xml_builder.py)
    2. PKT generation using ptexplorer (preferred method)
    3. Fallback to Twofish/EAX encryption if ptexplorer unavailable
    4. Validation
    
    Args:
        subnets: List of calculated subnet configurations
        config: Network configuration dict containing:
            - routing_protocol: RoutingProtocol value
            - routers: int (number of routers)
            - switches: int (number of switches) 
            - pcs: int (number of PCs)
        output_dir: Directory to save files (default: /tmp/tracenet)
        
    Returns:
        Dict with generation results:
        {
            "success": bool,
            "pkt_path": str (path to .pkt file),
            "xml_path": str (path to debug XML file),
            "encoding_used": str ("ptexplorer" or "twofish_eax_fallback"),
            "file_size": int (bytes),
            "validation": str (validation message)
        }
    """
    # Setup output directory
    if output_dir is None:
        output_dir = os.getenv("OUTPUT_DIR", DEFAULT_OUTPUT_DIR)
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate timestamped filenames with unique identifier to prevent race conditions
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    pkt_path = Path(output_dir) / f"network_{timestamp}_{unique_id}.pkt"
    xml_path = Path(output_dir) / f"network_{timestamp}_{unique_id}.xml"
    
    logger.info(f"🔧 PKT Generation Started")
    logger.info(f"   Output path: {pkt_path}")
    logger.info(f"   Using: {'ptexplorer' if PTEXPLORER_AVAILABLE else 'Twofish/EAX fallback'}")
    
    try:
        # STEP 1: Build XML structure
        logger.info(f"📝 Step 1: Building XML structure...")
        xml_content = build_pkt_xml(subnets, config)
        logger.info(f"✅ XML structure built ({len(xml_content)} bytes)")
        
        # STEP 2: Save debug XML file
        logger.info(f"💾 Step 2: Saving debug XML...")
        xml_path.write_text(xml_content, encoding='utf-8')
        logger.info(f"✅ Debug XML saved: {xml_path}")
        
        # STEP 3: Validate XML before conversion
        try:
            import xml.etree.ElementTree as ET
            ET.fromstring(xml_content)
            logger.info(f"✅ XML validation passed")
        except ET.ParseError as e:
            logger.warning(f"⚠️ XML Validation Warning: {e}")
        
        xml_bytes = xml_content.encode('utf-8')
        
        # STEP 4: Try ptexplorer first, fallback to Twofish/EAX
        encoding_method = "unknown"
        validation_msg = ""
        
        if PTEXPLORER_AVAILABLE:
            try:
                logger.info(f"🔄 Step 4: Converting XML to PKT using ptexplorer...")
                build_pkt_from_xml(xml_bytes, pkt_path)
                encoding_method = "ptexplorer"
                logger.info(f"✅ PKT file created with ptexplorer")
                validation_msg = "✅ Generated with ptexplorer (no manual encryption needed)"
            except Exception as e:
                logger.warning(f"⚠️ ptexplorer failed: {e}, falling back to Twofish/EAX")
                # Fallback to manual encryption
                encoding_method = "twofish_eax_fallback"
                encrypted_data = encrypt_pkt_data(xml_bytes)
                logger.info(f"✅ Encryption complete ({len(encrypted_data)} bytes)")
                
                # Validate encryption
                is_valid, validation_msg = validate_encryption(xml_bytes)
                logger.info(f"   {validation_msg}")
                
                # Create PKT5 header
                magic = b'PKT5'
                version = struct.pack('<HHHH', 8, 2, 2, 400)
                header_size = 512
                padding = b'\x00' * (header_size - len(magic) - len(version))
                pkt_header = magic + version + padding
                
                # Write file
                with pkt_path.open('wb') as f:
                    f.write(pkt_header)
                    f.write(encrypted_data)
        else:
            # No ptexplorer, use Twofish/EAX directly
            logger.info(f"🔐 Step 4: Encrypting with Twofish/EAX (ptexplorer not available)...")
            encoding_method = "twofish_eax_fallback"
            encrypted_data = encrypt_pkt_data(xml_bytes)
            logger.info(f"✅ Encryption complete ({len(encrypted_data)} bytes)")
            
            # Validate encryption
            is_valid, validation_msg = validate_encryption(xml_bytes)
            logger.info(f"   {validation_msg}")
            
            # Create PKT5 header
            logger.info(f"📦 Step 5: Creating PKT5 header...")
            magic = b'PKT5'
            version = struct.pack('<HHHH', 8, 2, 2, 400)
            header_size = 512
            padding = b'\x00' * (header_size - len(magic) - len(version))
            pkt_header = magic + version + padding
            logger.info(f"✅ PKT5 header created: {len(pkt_header)} bytes")
            
            # Write .pkt file with header
            logger.info(f"💾 Step 6: Writing .pkt file...")
            with pkt_path.open('wb') as f:
                f.write(pkt_header)
                f.write(encrypted_data)
        
        file_size = pkt_path.stat().st_size
        logger.info(f"✅ PKT file written: {file_size} bytes")
        
        # Check file size sanity
        if file_size < 100:
            logger.warning(f"⚠️ File size suspiciously small ({file_size} bytes)")
            
        # Success response
        return {
            "success": True,
            "pkt_path": str(pkt_path),
            "xml_path": str(xml_path),
            "encoding_used": encoding_method,
            "file_size": file_size,
            "validation": validation_msg,
            "pka2xml_available": False,
            "ptexplorer_available": PTEXPLORER_AVAILABLE
        }
        
    except Exception as e:
        logger.error(f"❌ PKT generation failed: {str(e)}", exc_info=True)
        
        # Create error file for debugging
        try:
            error_path = str(pkt_path) + ".err"
            with open(error_path, 'w') as f:
                f.write(f"Error: {str(e)}\n")
                f.write(f"Config: {config}\n")
                f.write(f"Subnets: {len(subnets)}\n")
            logger.info(f"📝 Error details saved to: {error_path}")
        except:
            pass
        
        return {
            "success": False,
            "error": str(e),
            "encoding_used": "failed",
            "pkt_path": None,
            "xml_path": None,
            "ptexplorer_available": PTEXPLORER_AVAILABLE
        }


def validate_pkt_file(pkt_path: str) -> Dict[str, Any]:
    """
    Validates a generated .pkt file by attempting to decrypt it.
    
    This function verifies that:
    1. File exists and is readable
    2. File can be decrypted successfully (if using Twofish/EAX)
    3. Decrypted data is valid XML
    4. XML contains expected PT structure
    
    Args:
        pkt_path: Path to .pkt file to validate
        
    Returns:
        Dict with validation results
    """
    from app.services.pkt_crypto import decrypt_pkt_data
    import xml.etree.ElementTree as ET
    
    logger.info(f"🔍 Validating PKT file: {pkt_path}")
    
    if not os.path.exists(pkt_path):
        return {
            "valid": False,
            "error": "File does not exist"
        }
    
    try:
        # Try to use ptexplorer first if available
        if PTEXPLORER_AVAILABLE:
            try:
                pt = PTFile()
                pt.open(pkt_path)
                xml_data = pt.export_xml()
                logger.info(f"   Loaded with ptexplorer, XML size: {len(xml_data)} bytes")
            except Exception as e:
                logger.warning(f"   ptexplorer validation failed: {e}, trying manual decryption")
                # Fallback to manual decryption
                with open(pkt_path, 'rb') as f:
                    file_data = f.read()
                # Skip PKT5 header (512 bytes)
                encrypted_data = file_data[512:]
                xml_data = decrypt_pkt_data(encrypted_data)
                logger.info(f"   Decrypted size: {len(xml_data)} bytes")
        else:
            # No ptexplorer, decrypt manually
            with open(pkt_path, 'rb') as f:
                file_data = f.read()
            # Skip PKT5 header (512 bytes)
            encrypted_data = file_data[512:]
            xml_data = decrypt_pkt_data(encrypted_data)
            logger.info(f"   Decrypted size: {len(xml_data)} bytes")
        
        # Parse XML
        if isinstance(xml_data, bytes):
            xml_data = xml_data.decode('utf-8')
        
        root = ET.fromstring(xml_data)
        
        # Check structure
        if root.tag != "PACKETTRACER5":
            return {
                "valid": False,
                "error": f"Invalid root tag: {root.tag}"
            }
        
        version = root.get("VERSION", "unknown")
        workspace = root.find("WORKSPACE")
        
        if workspace is None:
            return {
                "valid": False,
                "error": "Missing WORKSPACE element"
            }
        
        devices = workspace.find("DEVICES")
        links = workspace.find("LINKS")
        
        device_count = len(devices.findall("DEVICE")) if devices is not None else 0
        link_count = len(links.findall("LINK")) if links is not None else 0
        
        logger.info(f"✅ Validation passed:")
        logger.info(f"   Version: {version}")
        logger.info(f"   Devices: {device_count}")
        logger.info(f"   Links: {link_count}")
        
        return {
            "valid": True,
            "version": version,
            "devices": device_count,
            "links": link_count,
            "xml_size": len(xml_data)
        }
        
    except Exception as e:
        logger.error(f"❌ Validation failed: {str(e)}")
        return {
            "valid": False,
            "error": str(e)
        }
