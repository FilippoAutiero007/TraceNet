"""
PKT File Generator Service - Creates Cisco Packet Tracer 8.x compatible files

This module orchestrates the complete generation of .pkt files that can be opened
in Cisco Packet Tracer 8.x and later versions.

Process:
1. Build XML structure (using pkt_xml_builder.py)
2. Encrypt XML data (using pkt_crypto.py)
3. Write final .pkt file
4. Validate roundtrip encryption (optional)

References:
- pka2xml (mircodz): https://github.com/mircodz/pka2xml
  Used for understanding PT file format and encryption
- Unpacket (Punkcake21): https://github.com/Punkcake21/Unpacket
  Used for Twofish/EAX implementation

Key improvements over original implementation:
- Uses proper Twofish/EAX encryption (not XOR obfuscation)
- Generates PT 8.x compatible XML structure
- Includes validation of encryption pipeline
- Full documentation of cryptographic process
"""

import os
import logging
from datetime import datetime
from typing import List, Dict, Any

from app.models.schemas import SubnetResult
from app.services.pkt_xml_builder import build_pkt_xml
from app.services.pkt_crypto import encrypt_pkt_data, validate_encryption

logger = logging.getLogger(__name__)

# Default configuration
DEFAULT_OUTPUT_DIR = "/tmp/tracenet"
DEFAULT_XML_VERSION = "8.2.2.0400"  # PT 8.x version


def save_pkt_file(subnets: List[SubnetResult], config: Dict[str, Any], output_dir: str = None) -> Dict[str, Any]:
    """
    Generate a complete .pkt file with proper encryption.
    
    This is the main entry point for PKT file generation. It coordinates:
    1. XML structure building (pkt_xml_builder.py)
    2. Encryption (pkt_crypto.py using Unpacket's implementation)
    3. File I/O
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
            "encoding_used": str (always "twofish_eax"),
            "file_size": int (bytes),
            "validation": str (validation message)
        }
        
    References:
    - Original pkt_file_generator.py for structure
    - pka2xml for encryption algorithm
    - Unpacket for cryptographic implementation
    """
    # Setup output directory
    if output_dir is None:
        output_dir = os.getenv("OUTPUT_DIR", DEFAULT_OUTPUT_DIR)
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate timestamped filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pkt_path = os.path.join(output_dir, f"network_{timestamp}.pkt")
    xml_path = os.path.join(output_dir, f"network_{timestamp}.xml")
    
    logger.info(f"🔧 PKT Generation Started")
    logger.info(f"   Output path: {pkt_path}")
    logger.info(f"   Using: Twofish/EAX encryption (Unpacket implementation)")
    
    try:
        # STEP 1: Build XML structure
        # Reference: pkt_xml_builder.py - build_pkt_xml()
        logger.info(f"📝 Step 1: Building XML structure...")
        xml_content = build_pkt_xml(subnets, config)
        logger.info(f"✅ XML structure built ({len(xml_content)} bytes)")
        
        # STEP 2: Save debug XML file
        logger.info(f"💾 Step 2: Saving debug XML...")
        with open(xml_path, 'w', encoding='utf-8') as f:
            f.write(xml_content)
        logger.info(f"✅ Debug XML saved: {xml_path}")
        
        # STEP 3: Validate XML before encryption (optional)
        try:
            import xml.etree.ElementTree as ET
            ET.fromstring(xml_content)
            logger.info(f"✅ XML validation passed")
        except ET.ParseError as e:
            logger.warning(f"⚠️ XML Validation Warning: {e}")
        
        # STEP 4: Encrypt XML data
        # Reference: pkt_crypto.py - encrypt_pkt_data()
        # Uses Unpacket's Twofish/EAX implementation
        logger.info(f"🔐 Step 4: Encrypting with Twofish/EAX...")
        xml_bytes = xml_content.encode('utf-8')
        encrypted_data = encrypt_pkt_data(xml_bytes)
        logger.info(f"✅ Encryption complete ({len(encrypted_data)} bytes)")
        
        # STEP 5: Validate encryption (roundtrip test)
        logger.info(f"🔍 Step 5: Validating encryption...")
        is_valid, validation_msg = validate_encryption(xml_bytes)
        logger.info(f"   {validation_msg}")
        
        # STEP 6: Write .pkt file
        logger.info(f"💾 Step 6: Writing .pkt file...")
        with open(pkt_path, 'wb') as f:
            f.write(encrypted_data)
        
        file_size = os.path.getsize(pkt_path)
        logger.info(f"✅ PKT file written: {file_size} bytes")
        
        # Check file size sanity
        if file_size < 100:
            logger.warning(f"⚠️ File size suspiciously small ({file_size} bytes)")
            
        # Success response
        return {
            "success": True,
            "pkt_path": pkt_path,
            "xml_path": xml_path,
            "encoding_used": "twofish_eax",  # Using proper encryption now
            "file_size": file_size,
            "validation": validation_msg,
            "pka2xml_available": False  # We're using pure Python implementation
        }
        
    except Exception as e:
        logger.error(f"❌ PKT generation failed: {str(e)}", exc_info=True)
        
        # Create error file for debugging
        try:
            error_path = pkt_path + ".err"
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
            "xml_path": None
        }


def validate_pkt_file(pkt_path: str) -> Dict[str, Any]:
    """
    Validates a generated .pkt file by attempting to decrypt it.
    
    This function verifies that:
    1. File exists and is readable
    2. File can be decrypted successfully
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
        # Read file
        with open(pkt_path, 'rb') as f:
            encrypted_data = f.read()
        
        logger.info(f"   File size: {len(encrypted_data)} bytes")
        
        # Decrypt
        xml_data = decrypt_pkt_data(encrypted_data)
        logger.info(f"   Decrypted size: {len(xml_data)} bytes")
        
        # Parse XML
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
