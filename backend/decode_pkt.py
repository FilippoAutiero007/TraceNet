from pathlib import Path
from app.services.pkt_crypto import decrypt_pkt_data


def main(pkt_path_str: str, xml_path_str: str) -> None:
    pkt_path = Path(pkt_path_str)
    xml_path = Path(xml_path_str)

    raw = pkt_path.read_bytes()
    xml_bytes = decrypt_pkt_data(raw)
    xml_path.write_bytes(xml_bytes)


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        print("Usage: python decode_pkt.py input.pkt output.xml", file=sys.stderr)
        raise SystemExit(1)

    main(sys.argv[1], sys.argv[2])
