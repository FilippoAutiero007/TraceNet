#!/usr/bin/env python3
"""
Re-encode Template Compatibility Test
======================================
Reads simple_ref.pkt, decrypts it, re-encrypts it, and verifies that the
roundtrip produces bit-identical XML.

Usage:
    cd backend
    python tools/reencode_template.py [path/to/template.pkt]

Outputs:
    reencoded.xml  – the decrypted XML
    reencoded.pkt  – the re-encrypted PKT (should be openable in PT)

Exit code:
    0 – roundtrip OK
    1 – roundtrip FAILED (crypto bug detected)
    2 – file not found / other error
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make sure the backend package is importable when running as a script.
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.pkt_crypto import decrypt_pkt_data, encrypt_pkt_data  # noqa: E402


def reencode(template_path: Path, out_dir: Path) -> int:
    if not template_path.is_file():
        print(f"ERROR: Template not found: {template_path}", file=sys.stderr)
        return 2

    print(f"Reading  : {template_path}  ({template_path.stat().st_size:,} bytes)")

    # Step 1 – decrypt
    raw_pkt = template_path.read_bytes()
    try:
        xml_bytes = decrypt_pkt_data(raw_pkt)
    except Exception as exc:
        print(f"FAIL  decrypt failed: {exc}", file=sys.stderr)
        return 1

    print(f"Decrypted: {len(xml_bytes):,} bytes of XML")
    print(f"  Starts : {xml_bytes[:80]!r}")

    # Save decrypted XML
    out_dir.mkdir(parents=True, exist_ok=True)
    xml_out = out_dir / "reencoded.xml"
    xml_out.write_bytes(xml_bytes)
    print(f"Saved XML: {xml_out}")

    # Step 2 – re-encrypt
    try:
        re_enc = encrypt_pkt_data(xml_bytes)
    except Exception as exc:
        print(f"FAIL  re-encrypt failed: {exc}", file=sys.stderr)
        return 1

    pkt_out = out_dir / "reencoded.pkt"
    pkt_out.write_bytes(re_enc)
    print(f"Saved PKT: {pkt_out}  ({len(re_enc):,} bytes)")

    # Step 3 – verify roundtrip: decrypt(reenc) == original xml
    try:
        xml_check = decrypt_pkt_data(re_enc)
    except Exception as exc:
        print(f"FAIL  re-decrypt failed: {exc}", file=sys.stderr)
        return 1

    if xml_check != xml_bytes:
        print("FAIL  decrypt(encrypt(xml)) != xml  — crypto pipeline is NOT self-inverse!", file=sys.stderr)
        # Show first difference
        for i, (a, b) in enumerate(zip(xml_bytes, xml_check)):
            if a != b:
                print(f"  First diff at byte {i}: original={a:#04x} reencoded={b:#04x}", file=sys.stderr)
                break
        if len(xml_bytes) != len(xml_check):
            print(f"  Length mismatch: original={len(xml_bytes)} reencoded={len(xml_check)}", file=sys.stderr)
        return 1

    # Also verify the re-encoded .pkt is byte-identical to the original
    if re_enc == raw_pkt:
        print("ROUNDTRIP OK – re-encrypted file is byte-identical to original .pkt")
    else:
        # Byte-identical is not guaranteed (EAX/nonce could differ if IV were random),
        # but in our case IV is hardcoded so they SHOULD match.
        print("NOTE: re-encoded .pkt differs from original (acceptable if IV is non-deterministic)")
        print(f"  original size={len(raw_pkt)} re-encoded size={len(re_enc)}")

    print(f"ROUNDTRIP OK – original and reencoded XML are identical ({len(xml_bytes):,} bytes)")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) >= 2:
        template_path = Path(argv[1])
    else:
        template_path = BACKEND_DIR / "templates" / "simple_ref.pkt"

    out_dir = BACKEND_DIR / "tmp_out"
    return reencode(template_path, out_dir)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
