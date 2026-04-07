from __future__ import annotations

import argparse
import base64
import json
from datetime import UTC, datetime
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa


def generate_keypair(private_key_path: Path, public_key_path: Path) -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    public_bytes = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    private_key_path.write_bytes(private_bytes)
    public_key_path.write_bytes(public_bytes)


def load_private_key(path: Path):
    return serialization.load_pem_private_key(path.read_bytes(), password=None)


def create_license(private_key_path: Path, hardware_id: str, license_type: str, expiry_date: str | None) -> str:
    private_key = load_private_key(private_key_path)
    payload = {
        "hardware_fingerprint": hardware_id,
        "license_type": license_type,
        "expiry_date": expiry_date,
        "issued_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    message = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    signature = private_key.sign(
        message,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256(),
    )
    payload["signature"] = base64.urlsafe_b64encode(signature).decode("utf-8")
    encoded = base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8")).decode("utf-8")
    return encoded


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Offline license generator for WhiteLabelPOS.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init-keys", help="Generate a fresh RSA keypair.")
    init_parser.add_argument("--private-key", required=True, type=Path)
    init_parser.add_argument("--public-key", required=True, type=Path)

    create_parser = subparsers.add_parser("generate", help="Generate a signed offline license.")
    create_parser.add_argument("--private-key", required=True, type=Path)
    create_parser.add_argument("--hardware-id", required=True)
    create_parser.add_argument("--license-type", choices=["trial", "lifetime"], required=True)
    create_parser.add_argument("--expiry-date", help="YYYY-MM-DD for trials; omit for lifetime.")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "init-keys":
        args.private_key.parent.mkdir(parents=True, exist_ok=True)
        args.public_key.parent.mkdir(parents=True, exist_ok=True)
        generate_keypair(args.private_key, args.public_key)
        print(f"Private key written to {args.private_key}")
        print(f"Public key written to {args.public_key}")
        return
    license_key = create_license(
        private_key_path=args.private_key,
        hardware_id=args.hardware_id,
        license_type=args.license_type,
        expiry_date=args.expiry_date,
    )
    print(license_key)


if __name__ == "__main__":
    main()
