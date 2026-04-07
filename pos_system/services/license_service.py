from __future__ import annotations

import base64
import hashlib
import json
from datetime import UTC, date, datetime, timedelta

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from sqlalchemy import select

from pos_system.config.app_config import BUNDLED_PUBLIC_KEY, LICENSE_FILE
from pos_system.database.session import session_scope
from pos_system.models.dtos import ActivationResult, StartupState
from pos_system.models.entities import LicenseRecord, User
from pos_system.models.enums import LicenseType, StartupStatus
from pos_system.utils.system import hardware_fingerprint


class LicenseService:
    _APP_SECRET_FRAGMENTS = ("offline", "restaurant", "pos", "licensing", "protection")

    def get_hardware_fingerprint(self) -> str:
        return hardware_fingerprint()

    def validate_startup(self) -> StartupState:
        validation = self.validate_installed_license()
        if not validation.success:
            return StartupState(status=StartupStatus.NEEDS_ACTIVATION, message=validation.message)
        with session_scope() as session:
            has_user = session.scalar(select(User.id).limit(1)) is not None
        if not has_user:
            return StartupState(status=StartupStatus.NEEDS_SETUP, message="Activation complete. Finish setup.")
        return StartupState(status=StartupStatus.READY, message="License verified.")

    def activate(self, license_key: str) -> ActivationResult:
        payload = self._decode_license_key(license_key)
        self._verify_payload(payload)
        self._store_license_file(payload)
        self._sync_license_record(payload)
        return ActivationResult(
            success=True,
            message="License activated successfully.",
            license_type=LicenseType(payload["license_type"]),
            expiry_date=self._parse_expiry(payload.get("expiry_date")),
        )

    def validate_installed_license(self) -> ActivationResult:
        if not LICENSE_FILE.exists():
            return ActivationResult(False, "No activated license found.")
        try:
            encrypted_blob = LICENSE_FILE.read_bytes()
            raw_data = self._fernet().decrypt(encrypted_blob)
            payload = json.loads(raw_data.decode("utf-8"))
            self._verify_payload(payload)
            with session_scope() as session:
                record = session.scalar(select(LicenseRecord).limit(1))
                if not record:
                    raise ValueError("License record missing.")
                now = datetime.now(UTC).replace(tzinfo=None)
                if record.last_validated_at and now + timedelta(minutes=10) < record.last_validated_at:
                    raise ValueError("System clock rollback detected.")
                record.last_validated_at = now
                session.flush()
            return ActivationResult(
                True,
                "License validated.",
                license_type=LicenseType(payload["license_type"]),
                expiry_date=self._parse_expiry(payload.get("expiry_date")),
            )
        except (InvalidToken, ValueError, json.JSONDecodeError) as exc:
            return ActivationResult(False, str(exc))

    def _verify_payload(self, payload: dict) -> None:
        public_key = self._load_public_key()
        if public_key is None:
            raise ValueError("License verifier public key is not configured.")
        signature = base64.urlsafe_b64decode(payload["signature"].encode("utf-8"))
        signed_payload = dict(payload)
        signed_payload.pop("signature")
        message = json.dumps(signed_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        public_key.verify(
            signature,
            message,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256(),
        )
        if payload["hardware_fingerprint"] != self.get_hardware_fingerprint():
            raise ValueError("License does not match this machine.")
        expiry = self._parse_expiry(payload.get("expiry_date"))
        if expiry and expiry < date.today():
            raise ValueError("License has expired.")

    def _decode_license_key(self, license_key: str) -> dict:
        cleaned = "".join(license_key.strip().split())
        padded = cleaned + "=" * (-len(cleaned) % 4)
        try:
            decoded = base64.urlsafe_b64decode(padded.encode("utf-8"))
            payload = json.loads(decoded.decode("utf-8"))
            if "signature" not in payload:
                raise ValueError("License signature missing.")
            return payload
        except Exception as exc:
            raise ValueError("Invalid license key format.") from exc

    def _store_license_file(self, payload: dict) -> None:
        raw = json.dumps(payload, sort_keys=True).encode("utf-8")
        encrypted = self._fernet().encrypt(raw)
        LICENSE_FILE.write_bytes(encrypted)

    def _sync_license_record(self, payload: dict) -> None:
        fingerprint_hash = hashlib.sha256(payload["hardware_fingerprint"].encode("utf-8")).hexdigest()
        with session_scope() as session:
            record = session.scalar(select(LicenseRecord).limit(1))
            if not record:
                record = LicenseRecord(
                    hardware_fingerprint_hash=fingerprint_hash,
                    license_type=LicenseType(payload["license_type"]),
                )
                session.add(record)
            record.hardware_fingerprint_hash = fingerprint_hash
            record.license_type = LicenseType(payload["license_type"])
            record.expiry_date = self._parse_expiry(payload.get("expiry_date"))
            record.activated_at = datetime.now(UTC).replace(tzinfo=None)
            record.last_validated_at = datetime.now(UTC).replace(tzinfo=None)
            session.flush()

    def _fernet(self) -> Fernet:
        secret_material = "|".join((*self._APP_SECRET_FRAGMENTS, self.get_hardware_fingerprint()))
        key = hashlib.sha256(secret_material.encode("utf-8")).digest()
        return Fernet(base64.urlsafe_b64encode(key))

    @staticmethod
    def _parse_expiry(value: str | None) -> date | None:
        if not value:
            return None
        return datetime.strptime(value, "%Y-%m-%d").date()

    @staticmethod
    def _load_public_key():
        if not BUNDLED_PUBLIC_KEY.exists():
            return None
        pem_bytes = BUNDLED_PUBLIC_KEY.read_bytes().strip()
        if not pem_bytes:
            return None
        try:
            return serialization.load_pem_public_key(pem_bytes)
        except ValueError:
            return None
