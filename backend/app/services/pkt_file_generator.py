import os
import gzip
import struct
import zlib
import subprocess
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Tuple, List, Dict, Any, Optional
import logging
import tempfile
import shutil

# Configure logging
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
DEFAULT_XML_VERSION = "8.2.2.0400"  # Default for modern PT
DEFAULT_ENCODING = "external_pka2xml"     # Options: legacy_xor, external_pka2xml, gzip

def _get_env_config():
    return {
        "XML_VERSION": os.getenv("PKT_XML_VERSION", DEFAULT_XML_VERSION),
        "ENCODING": os.getenv("PKT_ENCODING", DEFAULT_ENCODING)
    }

# --- ENCODING UTILITIES ---

def _legacy_xor_encode(xml_content: str) -> bytes:
    """
    Encodes XML string into legacy Packet Tracer binary format (XOR + zlib).
    Format: [Uncompressed Length (4 bytes BE)] + [Zlib Compressed Data]
    Obfuscation: XOR with (TotalLength - Index).
    """
    data_bytes = xml_content.encode('utf-8')
    uncompressed_len = len(data_bytes)
    
    # 1. Compress
    compressed_data = zlib.compress(data_bytes)
    
    # 2. Header (Big Endian uint32)
    header = struct.pack('>I', uncompressed_len)
    payload = bytearray(header + compressed_data)
    
    # 3. XOR Obfuscation
    total_len = len(payload)
    for i in range(total_len):
        key = (total_len - i) & 0xFF
        payload[i] ^= key
        
    return bytes(payload)

def _legacy_xor_decode(encoded_data: bytes) -> str:
    """
    Decodes legacy Packet Tracer binary format (XOR + zlib) back to XML string.
    Used for testing roundtrip integrity.
    """
    payload = bytearray(encoded_data)
    total_len = len(payload)
    
    # 1. XOR De-obfuscation
    for i in range(total_len):
        key = (total_len - i) & 0xFF
        payload[i] ^= key
        
    # 2. Extract Header
    # header = payload[:4] (Uncompressed length, ignored in Python decompression but useful for checks)
    compressed_data = payload[4:]
    
    # 3. Decompress
    try:
        decompressed_data = zlib.decompress(compressed_data)
        return decompressed_data.decode('utf-8')
    except Exception as e:
        raise ValueError(f"Failed to decompress legacy payload: {e}")

def encode_with_pka2xml(xml_content: str) -> bytes:
    """Encode XML using external pka2xml tool"""
    
    logger.info("🔄 Starting pka2xml encoding...")
    
    # Create temp files
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False, encoding='utf-8') as xml_file:
        xml_file.write(xml_content)
        xml_path = xml_file.name
    
    pkt_path = xml_path.replace('.xml', '.pkt')
    
    try:
        # Determine command based on environment (Docker or Host)
        pka2xml_binary = shutil.which("pka2xml")
        
        if pka2xml_binary:
             # Strategy 1: Direct Binary Execution (Production/Docker)
            cmd = [pka2xml_binary, "-e", xml_path, pkt_path]
            logger.info(f"   Running local binary: {' '.join(cmd)}")
        else:
             # Strategy 2: Docker-in-Docker / Host Execution (Dev/Windows)
             # This requires 'pka2xml:latest' image available on host
             work_dir = os.path.dirname(xml_path)
             input_file = os.path.basename(xml_path)
             output_file = os.path.basename(pkt_path)
             
             cmd = [
                "docker", "run", "--rm",
                "-v", f"{work_dir}:/data",
                "pka2xml:latest",
                "pka2xml", "-e",
                f"/data/{input_file}",
                f"/data/{output_file}"
            ]
             logger.info(f"   Running Docker container: {' '.join(cmd)}")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.stdout:
            logger.info(f"   pka2xml stdout: {result.stdout}")
        if result.stderr:
            logger.warning(f"   pka2xml stderr: {result.stderr}")
        
        if result.returncode != 0:
            raise Exception(f"pka2xml failed with code {result.returncode}: {result.stderr}")
        
        # Read encoded file
        if not os.path.exists(pkt_path):
             # Try fallback to legacy name if output filename logic differs
             raise Exception(f"pka2xml did not create output file at {pkt_path}")
        
        with open(pkt_path, 'rb') as f:
            encoded_data = f.read()
            
        if len(encoded_data) == 0:
             raise Exception("pka2xml created an empty file")
        
        logger.info(f"✅ pka2xml encoding successful: {len(encoded_data)} bytes")
        return encoded_data
        
    finally:
        # Cleanup temp files
        for path in [xml_path, pkt_path]:
            if os.path.exists(path):
                try:
                    os.unlink(path)
                except:
                    pass

# --- VALIDATION ---

def validate_pkt_xml(xml_content: str) -> None:
    """
    Validates logical consistency of the generated XML.
    """
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as e:
         raise ValueError(f"Invalid XML syntax: {e}")

    # 1. Collect all Device Names and Interfaces
    device_map = {}
    for device in root.findall(".//DEVICE"):
        dev_name = device.get("name")
        if not dev_name: continue
        interfaces = set()
        for iface in device.findall("INTERFACE"):
            if_name = iface.get("name")
            if if_name: interfaces.add(if_name)
        device_map[dev_name] = interfaces

    # 2. Validate Links
    for i, link in enumerate(root.findall(".//LINKS/LINK")):
        src = link.get("from")
        dst = link.get("to")
        if not src or not dst: raise ValueError(f"Link {i} incomplete")
        if src not in device_map: raise ValueError(f"Link src '{src}' not found")
        if dst not in device_map: raise ValueError(f"Link dst '{dst}' not found")

# --- BUILDER --- 
# Note: The actual build_pkt_xml function must be defined here
# Since it wasn't in the provided code, I'm adding a placeholder

def build_pkt_xml(subnets: List[Any], config: Dict[str, Any]) -> str:
    """
    Builds the XML content for the PKT file.
    This is a placeholder - replace with your actual implementation.
    """
    # TODO: Implement actual XML building logic based on subnets and config
    xml_version = _get_env_config()["XML_VERSION"]
    
    xml_template = f"""<?xml version="1.0" encoding="UTF-8"?>
<PACKETTRACER5 VERSION="{xml_version}">
    <WORKSPACE>
        <DEVICES>
            <!-- Devices will be added here -->
        </DEVICES>
        <LINKS>
            <!-- Links will be added here -->
        </LINKS>
    </WORKSPACE>
</PACKETTRACER5>"""
    
    return xml_template

# --- MAIN ORCHESTRATOR ---

def save_pkt_file(subnets: List[Any], config: Dict[str, Any], output_dir: str = "/tmp") -> Dict[str, Any]:
    """
    Generate PKT file with detailed logging and robust fallback.
    Returns dictionary with status and paths.
    """
    os.makedirs(output_dir, exist_ok=True)
    env_config = _get_env_config()
    requested_encoding = env_config["ENCODING"]
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pkt_path = os.path.join(output_dir, f"network_{timestamp}.pkt")
    xml_path = os.path.join(output_dir, f"network_{timestamp}.xml")
    
    # Log environment
    logger.info(f"🔧 PKT Generation Started")
    logger.info(f"   Output path: {pkt_path}")
    logger.info(f"   Requested encoding: {requested_encoding}")
    
    # Check pka2xml availability
    pka2xml_path = shutil.which("pka2xml")
    pka2xml_available = bool(pka2xml_path)
    
    if requested_encoding == "external_pka2xml":
        if pka2xml_path:
            logger.info(f"✅ pka2xml found at: {pka2xml_path}")
        else:
            logger.warning(f"⚠️ pka2xml NOT FOUND in PATH - will fallback to Docker/Legacy")

    try:
        # 1. Build
        xml_content = build_pkt_xml(subnets, config)
        logger.info(f"✅ XML structure built ({len(xml_content)} bytes)")
        
        # 2. Validate
        try:
            validate_pkt_xml(xml_content)
        except ValueError as e:
            logger.warning(f"⚠️ XML Validation Warning: {e}")

        # 3. Save XML (Debug)
        with open(xml_path, 'w', encoding='utf-8') as f:
            f.write(xml_content)
            
        # 4. Encode
        encoded_data = b""
        encoding_used = "unknown"
        
        # Strategy: Try requested -> Try Fallback
        
        if requested_encoding == "external_pka2xml":
            try:
                encoded_data = encode_with_pka2xml(xml_content)
                encoding_used = "external_pka2xml"
            except Exception as e:
                logger.error(f"❌ pka2xml encoding failed: {e}")
                logger.warning("⚠️ Falling back to legacy_xor")
                
                # Downgrade version logic for fallback
                if "VERSION>8." in xml_content:
                    xml_content = xml_content.replace(">8.2.2.0400<", ">6.2.0.0052<")
                    
                encoded_data = _legacy_xor_encode(xml_content)
                encoding_used = "legacy_xor_fallback"
                
        elif requested_encoding == "gzip":
             # Proper gzip compression
             encoded_data = gzip.compress(xml_content.encode('utf-8'))
             encoding_used = "gzip"
             
        else: # Default legacy_xor
            encoded_data = _legacy_xor_encode(xml_content)
            encoding_used = "legacy_xor"

        # 5. Create PKT Header + Write PKT (FIX B1: timestamp in big-endian)
        # PKT Format: [HEADER (16 bytes)] + [ENCODED_PAYLOAD]
        # Header: magic(4) + version(2) + header_len(2) + timestamp(4) + payload_len(4)
        
        MAGIC_NUMBER = 0x504B5446  # 'PKTF' placeholder
        PKT_VERSION = 0x0001
        HEADER_SIZE = 16
        
        # Timestamp in BIG-ENDIAN (FIX B1 from analysis)
        timestamp_unix = int(datetime.now().timestamp())
        
        # Build header (all fields in network byte order = big-endian)
        header = struct.pack(
            '>IHHII',  # '>' = big-endian, I=uint32, H=uint16
            MAGIC_NUMBER,           # 4 bytes
            PKT_VERSION,            # 2 bytes
            HEADER_SIZE,            # 2 bytes
            timestamp_unix,         # 4 bytes (FIX: big-endian timestamp)
            len(encoded_data)       # 4 bytes (payload length)
        )
        
        # Write header + payload to PKT file
        with open(pkt_path, 'wb') as f:
            f.write(header)
            f.write(encoded_data)
            
        file_size = os.path.getsize(pkt_path)
        logger.info(f"✅ PKT file written: {file_size} bytes (header: {HEADER_SIZE}, payload: {len(encoded_data)})")
        
        if file_size < 1000 and encoding_used == "external_pka2xml":
             logger.warning(f"⚠️ File size suspiciously small ({file_size} bytes) for AES encoded file")

        return {
            "success": True,
            "pkt_path": pkt_path,
            "xml_path": xml_path,
            "encoding_used": encoding_used,
            "file_size": file_size,
            "pka2xml_available": pka2xml_available
        }

    except Exception as e:
        logger.error(f"❌ PKT generation process failed: {str(e)}", exc_info=True)
        # Create error file for debug
        with open(pkt_path + ".err", 'w') as f:
            f.write(str(e))
        return {
            "success": False,
            "error": str(e),
            "encoding_used": "failed"
        }
