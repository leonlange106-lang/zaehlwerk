"""Konfiguration. Zählwerk ist standalone (nur SQLite).

DB-Pfad-Priorität:
1. ENV SQLITE_PATH (explizit)
2. /config/zaehlwerk.db   -> Add-on-Config-Verzeichnis: liegt im normalen HA-Backup!
3. /share/zaehlwerk/      -> ältere Version: wird einmalig nach /config migriert
4. /data/zaehlwerk.db     -> noch ältere Version: wird einmalig migriert
5. ./data/zaehlwerk.db    -> lokaler Betrieb ohne HA
"""
import os
import shutil
from pathlib import Path

from pydantic_settings import BaseSettings


def _migrate(old: Path, new: Path) -> None:
    """Einmalige, nicht-destruktive Übernahme (Kopie; Original bleibt als Fallback liegen)."""
    if new.exists() or not old.exists():
        return
    try:
        shutil.copy2(old, new)
        # WAL-Sidecar-Dateien mitnehmen, falls vorhanden
        for suffix in ("-wal", "-shm"):
            side = Path(str(old) + suffix)
            if side.exists():
                shutil.copy2(side, Path(str(new) + suffix))
    except Exception:
        pass


if "SQLITE_PATH" not in os.environ:
    if Path("/config").is_dir():                       # HA-Add-on: addon_config (im HA-Backup)
        target = Path("/config/zaehlwerk.db")
        _migrate(Path("/share/zaehlwerk/zaehlwerk.db"), target)
        _migrate(Path("/data/zaehlwerk.db"), target)
        os.environ["SQLITE_PATH"] = str(target)
    elif Path("/data").is_dir():                       # Docker-Standalone
        os.environ["SQLITE_PATH"] = "/data/zaehlwerk.db"


class Settings(BaseSettings):
    sqlite_path: str = "./data/zaehlwerk.db"
    cors_origins: str = "*"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
