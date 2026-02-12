"""
PKT Crypto Service - Handles encryption/decryption of Cisco Packet Tracer files

NOTE - IMPORTANT:
Queste funzioni di cifratura (Twofish/EAX) NON sono usate per i file .pkt destinati a Cisco Packet Tracer
quando ptexplorer è disponibile. Packet Tracer utilizza un proprio formato/procedura di codifica gestito
tramite ptexplorer (backend/ptexplorer.py).

Manteniamo queste funzioni solo per:
- Fallback quando ptexplorer non è disponibile
- Eventuali formati interni / backup cifrati
- Testing e validazione

This module provides cryptographic functions for generating valid .pkt files
that can be opened in Cisco Packet Tracer 8.x and later versions.

References:
- Unpacket (Punkcake21): https://github.com/Punkcake21/Unpacket
  Used for Twofish/EAX encryption implementation
- pka2xml (mircodz): https://github.com/mircodz/pka2xml
  Used for understanding the complete encryption pipeline

Encryption Pipeline (following pka2xml algorithm):
1. Stage 1: Compression - zlib compression with 4-byte big-endian size header
2. Stage 2: Obfuscation - XOR with (compressed_size - i) for each byte i
3. Stage 3: Encryption - Twofish in EAX mode (key=[137]*16, iv=[16]*16)
4. Stage 4: Obfuscation - Reverse order + XOR with (length - i*length)

The pipeline ensures compatibility with Packet Tracer 8.x encryption format.
"""

import gzip
import zlib
import struct
from typing import Tuple
from Decipher.eax import EAX
from Decipher.twofish import Twofish


def compress_qt(xml_data: bytes) -> bytes:
    """
    Compresses XML data using zlib with Qt-style format.
    
    Qt compression format:
    - 4 bytes: original size (big-endian)
    - N bytes: zlib compressed data
    
    Args:
        xml_data: Raw XML data to compress
        
    Returns:
        Compressed data with Qt header
        
    Reference: Unpacket/repacket.py - compress_qt()
    """
    size = len(xml_data)
    header = struct.pack(">I", size)  # Big-endian uint32
    compressed = zlib.compress(xml_data)
    return header + compressed


def obf_stage2(data: bytes) -> bytes:
    """
    Applies Stage 2 obfuscation (XOR with position-based key).
    
    Algorithm: result[i] = data[i] ^ ((length - i) & 0xFF)
    
    This is symmetric: applying it twice returns the original data.
    
    Args:
        data: Data to obfuscate
        
    Returns:
        Obfuscated data
        
    Reference: 
    - pka2xml.hpp line 85: output[i] = output[i] ^ (output.size() - i)
    - Unpacket/repacket.py - obf_stage2()
    """
    L = len(data)
    return bytes(b ^ (L - i & 0xFF) for i, b in enumerate(data))


def obf_stage1(data: bytes) -> bytes:
    """
    Applies Stage 1 obfuscation (reverse order + XOR).
    
    Algorithm:
    - For each byte at position i in the input
    - Calculate key = (length - i*length) & 0xFF
    - XOR byte with key
    - Place result at mirrored position (length-1-i)
    
    Args:
        data: Data to obfuscate
        
    Returns:
        Obfuscated data
        
    Reference:
    - pka2xml.hpp line 74-76: Stage 1 deobfuscation (this is the reverse)
    - Unpacket/repacket.py - obf_stage1()
    """
    L = len(data)
    output = bytearray(L)
    
    for i in range(L):
        # Key calculation as per pka2xml algorithm
        key_byte = (L - i * L) & 0xFF
        val = data[i] ^ key_byte
        
        # Place result in mirror position
        output[L - 1 - i] = val
        
    return bytes(output)


def encrypt_pkt_data(xml_data: bytes) -> bytes:
    """
    Encrypts XML data using the complete Packet Tracer encryption pipeline.
    
    NOTE: This function is only used as FALLBACK when ptexplorer is not available.
    Prefer using ptexplorer (backend/ptexplorer.py) for production PKT file generation.
    
    This function implements the full 4-stage encryption process used by
    Cisco Packet Tracer for .pkt and .pka files.
    
    Stages:
    1. Compression: Qt-style zlib compression
    2. Obfuscation: XOR with position-based key
    3. Encryption: Twofish-128 in EAX mode (authenticated encryption)
    4. Obfuscation: Reverse order + XOR
    
    Args:
        xml_data: Raw XML string as bytes (UTF-8 encoded)
        
    Returns:
        Fully encrypted data ready to be written to .pkt file
        
    References:
    - pka2xml.hpp encrypt() function (lines 200-229)
    - Unpacket repacket.py main() function (lines 128-139)
    
    Cryptographic parameters:
    - Algorithm: Twofish-128
    - Mode: EAX (authenticated encryption with associated data)
    - Key: [137] * 16 (hardcoded in PT)
    - IV/Nonce: [16] * 16 (hardcoded in PT)
    """
    # Hardcoded cryptographic parameters from Packet Tracer
    # Reference: pka2xml.hpp line 120-121
    KEY = bytes([137] * 16)
    IV = bytes([16] * 16)
    
    # Stage 1: Compression (qCompress-style)
    compressed = compress_qt(xml_data)
    
    # Stage 2: Obfuscation (XOR with position)
    obfuscated = obf_stage2(compressed)
    
    # Stage 3: Encryption (Twofish/EAX)
    tf = Twofish(KEY)
    eax = EAX(tf.encrypt)
    ciphertext, tag = eax.encrypt(nonce=IV, plaintext=obfuscated)
    
    # In .pkt files, the tag (16 bytes) is appended after ciphertext
    encrypted = ciphertext + tag
    
    # Stage 4: Final obfuscation (reverse + XOR)
    final = obf_stage1(encrypted)
    
    return final


def decrypt_pkt_data(pkt_data: bytes) -> bytes:
    """
    Decrypts .pkt file data back to XML (for testing/validation).
    
    This implements the reverse of encrypt_pkt_data() to verify
    that generated files can be properly decrypted.
    
    Args:
        pkt_data: Encrypted .pkt file content
        
    Returns:
        Decrypted XML data as bytes
        
    Reference: Unpacket/Decipher/pt_crypto.py - decrypt_pkt()
    """
    KEY = bytes([137] * 16)
    IV = bytes([16] * 16)
    
    # Stage 1: Deobfuscation (reverse of obf_stage1)
    L = len(pkt_data)
    stage1 = bytes(pkt_data[L-1-i] ^ ((L - i*L) & 0xFF) for i in range(L))
    
    # Stage 2: Decryption (Twofish/EAX)
    tf = Twofish(KEY)
    eax = EAX(tf.encrypt)
    
    # Split ciphertext and tag (last 16 bytes)
    ciphertext = stage1[:-16]
    tag = stage1[-16:]
    
    decrypted = eax.decrypt(nonce=IV, ciphertext=ciphertext, tag=tag)
    
    # Stage 3: Deobfuscation (reverse of obf_stage2)
    stage2 = obf_stage2(decrypted)
    
    # Stage 4: Decompression (Qt format)
    if len(stage2) < 6:
        raise ValueError("Corrupted PKT payload: too short after deobfuscation")

    size = struct.unpack(">I", stage2[:4])[0]
    compressed = stage2[4:]

    # Defensive check for compressed payload header.
    # Accept both GZIP (1f 8b) and ZLIB streams to avoid cryptic crashes on malformed files.
    try:
        if compressed[:2] == bytes((0x1F, 0x8B)):
            xml_data = gzip.decompress(compressed)[:size]
        else:
            xml_data = zlib.decompress(compressed)[:size]
    except Exception as exc:
        raise ValueError("Invalid compressed payload in PKT file") from exc

    return xml_data


def validate_encryption(xml_data: bytes) -> Tuple[bool, str]:
    """
    Validates that encryption/decryption roundtrip works correctly.
    
    This function encrypts XML data and then decrypts it to verify
    that the cryptographic pipeline is working correctly.
    
    Args:
        xml_data: XML data to test
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        # Encrypt
        encrypted = encrypt_pkt_data(xml_data)
        
        # Decrypt
        decrypted = decrypt_pkt_data(encrypted)
        
        # Verify
        if decrypted == xml_data:
            return True, "✅ Encryption validation successful (fallback method)"
        else:
            return False, "❌ Decrypted data does not match original"
            
    except Exception as e:
        return False, f"❌ Validation failed: {str(e)}"
