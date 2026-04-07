from __future__ import annotations

import hashlib
import platform
import uuid


def safe_machine_guid() -> str:
    if platform.system().lower() != "windows":
        return platform.node()
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography") as key:
            value, _ = winreg.QueryValueEx(key, "MachineGuid")
            return value
    except Exception:
        return platform.node()


def hardware_fingerprint() -> str:
    raw = "|".join(
        [
            safe_machine_guid(),
            platform.node(),
            platform.machine(),
            hex(uuid.getnode()),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()
