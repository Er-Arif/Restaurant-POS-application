from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from pos_system.config.app_config import BACKUP_DIR, DB_PATH
from pos_system.database.session import SessionLocal, engine


class BackupService:
    def create_backup(self) -> str:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        target = BACKUP_DIR / f"pos_backup_{timestamp}.db"
        SessionLocal.remove()
        engine.dispose()
        shutil.copy2(DB_PATH, target)
        return str(target)

    def list_backups(self) -> list[str]:
        return [str(path) for path in sorted(BACKUP_DIR.glob("*.db"), reverse=True)]

    def restore_backup(self, path: str) -> None:
        source = Path(path)
        if not source.exists():
            raise ValueError("Backup file not found.")
        SessionLocal.remove()
        engine.dispose()
        shutil.copy2(source, DB_PATH)
