from pathlib import Path
from app.services.pkt_crypto import decrypt_pkt_data

BASE_DIR = Path(__file__).parent

FILES = [
    BASE_DIR / "manual_1r2s3p.pkt",
]


def decrypt_one(pkt_path: Path) -> None:
    if not pkt_path.exists():
        print(f"SKIP (not found): {pkt_path}")
        return

    out_path = pkt_path.with_suffix(".xml")
    data = pkt_path.read_bytes()
    xml_bytes = decrypt_pkt_data(data)
    out_path.write_bytes(xml_bytes)
    print(f"OK  : {out_path.relative_to(BASE_DIR)}")


def main():
    for p in FILES:
        decrypt_one(p)


if __name__ == "__main__":
    main()
