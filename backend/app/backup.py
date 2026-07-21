"""Automatische Sicherung der SQLite-Datenbank nach /backup.

**Warum kein Dateikopieren.** Die Datenbank läuft seit 2.2.0 im WAL-Modus.
Ein `shutil.copy` der .db-Datei erwischt einen Stand ohne die noch nicht
eingecheckten Transaktionen aus der -wal-Datei; schreibt gleichzeitig jemand,
ist die Kopie im schlimmsten Fall in sich widersprüchlich. Verwendet wird
deshalb die Online-Backup-API von SQLite (`Connection.backup()`): sie liest
seitenweise unter Sperrschutz, läuft nebenläufig zu Schreibzugriffen und
liefert immer einen konsistenten Stand – ohne die App anzuhalten.

**Warum /backup.** Home Assistant nimmt dieses Verzeichnis in seine eigenen
Voll-Sicherungen auf. Damit landet die Datenbank in derselben Sicherungskette
wie der Rest der Installation. Fehlt das Mapping `backup:rw` im Manifest,
weicht das Modul auf /share aus, statt den Dienst scheitern zu lassen.

**Gefahr beim Aufräumen.** In /backup liegen die Voll-Sicherungen von Home
Assistant. Die rollierende Bereinigung fasst deshalb ausschließlich Dateien an,
die dem eigenen Namensmuster entsprechen – alles andere bleibt unberührt.
"""
import asyncio
import gzip
import logging
import os
import re
import shutil
import sqlite3
import tempfile
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from .config import settings as runtime_settings

log = logging.getLogger("zaehlwerk.backup")

# Namensmuster der eigenen Sicherungen. Die Bereinigung löscht NUR Treffer.
FILENAME_RE = re.compile(r"^zaehlwerk_(\d{8})-(\d{6})\.db\.gz$")
FILENAME_FMT = "zaehlwerk_%Y%m%d-%H%M%S.db.gz"

PRIMARY_DIR = Path("/backup")
FALLBACK_DIR = Path("/share/zaehlwerk-backups")

# Obergrenze für hochgeladene Sicherungen. Großzügig bemessen, weil eine
# Datenbank über Jahre durchaus in den zweistelligen MB-Bereich wächst.
MAX_IMPORT_BYTES = 500 * 1024 * 1024

# Tabellen, deren Fehlen zeigt, dass die Datei keine Zählwerk-Sicherung ist.
# Bewusst knapp gehalten: eine ältere Sicherung darf jüngere Spalten oder
# Tabellen vermissen – dafür laufen im Anschluss die Migrationen erneut.
REQUIRED_TABLES = {"systems", "readings", "app_settings"}

_restore_lock = threading.Lock()


class RestoreError(Exception):
    """Eine hochgeladene oder ausgewählte Datei ist keine gültige, unversehrte
    Zählwerk-Sicherung und wird deshalb NICHT live geschaltet."""


def backup_dir() -> Path:
    """/backup, falls vom Supervisor gemappt – sonst /share als Rückfallebene.

    Explizite Override per ZAEHLWERK_BACKUP_DIR geht beidem vor. Das ist keine
    dritte Ebene der HA-Erkennung, sondern für Umgebungen ohne /backup und
    /share gedacht: der dezentrale Standalone-Betrieb (docker-compose mountet
    nur /data – Sicherungen unter /share lägen sonst auf der vergänglichen
    Container-Ebene und wären beim nächsten Image-Rebuild verloren) sowie
    Testläufe auf unprivilegierten Runnern, die weder /backup noch /share
    anlegen dürfen.
    """
    override = os.environ.get("ZAEHLWERK_BACKUP_DIR")
    if override:
        path = Path(override)
        path.mkdir(parents=True, exist_ok=True)
        return path
    if PRIMARY_DIR.is_dir() and os.access(PRIMARY_DIR, os.W_OK):
        return PRIMARY_DIR
    FALLBACK_DIR.mkdir(parents=True, exist_ok=True)
    return FALLBACK_DIR


def _source_path() -> Path:
    return Path(runtime_settings.sqlite_path)


def create_backup() -> dict:
    """Erzeugt eine konsistente, komprimierte Sicherung.

    Ablauf: Online-Backup in eine temporäre Datei -> `PRAGMA integrity_check`
    auf der Kopie -> gzip -> atomares Umbenennen ins Zielverzeichnis. Die
    Zieldatei erscheint dadurch erst, wenn sie vollständig und geprüft ist.
    Bricht ein Schritt ab, bleibt nichts Halbfertiges liegen.
    """
    src = _source_path()
    if not src.exists():
        raise FileNotFoundError(f"Datenbank nicht gefunden: {src}")

    target_dir = backup_dir()
    target = target_dir / datetime.now().strftime(FILENAME_FMT)
    started = datetime.now()

    tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp_db.close()
    tmp_db_path = Path(tmp_db.name)
    tmp_gz_path = target.with_suffix(target.suffix + ".part")

    try:
        # 1) Online-Backup: konsistent trotz paralleler Schreibzugriffe
        source_conn = sqlite3.connect(f"file:{src}?mode=ro", uri=True, timeout=30)
        dest_conn = sqlite3.connect(str(tmp_db_path))
        try:
            source_conn.backup(dest_conn, pages=200, sleep=0.05)
        finally:
            dest_conn.close()
            source_conn.close()

        # 2) Kopie prüfen, bevor sie als gültige Sicherung gilt
        check_conn = sqlite3.connect(str(tmp_db_path))
        try:
            result = check_conn.execute("PRAGMA integrity_check").fetchone()[0]
        finally:
            check_conn.close()
        if result != "ok":
            raise RuntimeError(f"Integritätsprüfung fehlgeschlagen: {result}")

        raw_size = tmp_db_path.stat().st_size

        # 3) Komprimieren und erst danach an den endgültigen Namen
        with open(tmp_db_path, "rb") as f_in, gzip.open(tmp_gz_path, "wb", compresslevel=6) as f_out:
            shutil.copyfileobj(f_in, f_out, length=1024 * 1024)
        tmp_gz_path.replace(target)

        info = {
            "file": target.name,
            "path": str(target),
            "size_bytes": target.stat().st_size,
            "source_bytes": raw_size,
            "created": started.isoformat(timespec="seconds"),
            "duration_ms": int((datetime.now() - started).total_seconds() * 1000),
        }
        log.info("Sicherung erstellt: %s (%s Bytes)", target.name, info["size_bytes"])
        return info
    finally:
        tmp_db_path.unlink(missing_ok=True)
        tmp_gz_path.unlink(missing_ok=True)


def _validate_candidate(path: Path) -> None:
    """Prüft Integrität und Grundstruktur, BEVOR die Datei live geschaltet wird.

    Zwei Prüfungen, beide auf der entpackten Kopie, nie auf dem Original:
    `PRAGMA integrity_check` verwirft beschädigte Dateien, der Tabellenabgleich
    verwirft Dateien, die zwar gültiges SQLite, aber keine Zählwerk-Sicherung
    sind – ein falsch ausgewähltes Backup einer anderen Anwendung etwa.
    """
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    except sqlite3.Error as exc:
        raise RestoreError(f"Keine lesbare SQLite-Datenbank: {exc}") from exc
    try:
        try:
            result = conn.execute("PRAGMA integrity_check").fetchone()[0]
        except sqlite3.DatabaseError as exc:
            raise RestoreError(f"Keine lesbare SQLite-Datenbank: {exc}") from exc
        if result != "ok":
            raise RestoreError(f"Integritätsprüfung fehlgeschlagen: {result}")
        tables = {row[0] for row in
                  conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        missing = REQUIRED_TABLES - tables
        if missing:
            raise RestoreError(
                "Keine Zählwerk-Sicherung – es fehlen die Tabellen: "
                + ", ".join(sorted(missing)))
    finally:
        conn.close()


def _record_restore_audit(source_name: str, safety_file: Optional[str]) -> None:
    """Manueller Protokolleintrag: der Dateitausch läuft am ORM vorbei und
    würde von der automatischen Änderungsprotokollierung sonst nicht erfasst."""
    import json as _json

    from sqlmodel import Session

    from . import audit
    from .database import engine
    from .models import AuditLog

    actor = audit.current_actor.get() or {}
    with Session(engine) as session:
        session.add(AuditLog(
            user_id=actor.get("id"), username=actor.get("username"),
            action="RESTORE", target_table="database", target_id=None,
            new_value=_json.dumps(
                {"restored_from": source_name, "safety_backup": safety_file},
                ensure_ascii=False),
        ))
        session.commit()


def restore_from_file(source: Path) -> dict:
    """Ersetzt die laufende Datenbank durch den Inhalt einer gzip-Sicherung.

    Reihenfolge ist die eigentliche Absicherung: entpacken -> validieren
    (Integrität + Grundstruktur) -> Sicherheitskopie des AKTUELLEN Bestands ->
    laufende Verbindungen trennen -> Zieldatei austauschen -> Migrationen
    erneut anwenden, falls die Sicherung älter ist als der laufende
    Schemastand. Schlägt einer der ersten beiden Schritte fehl, bleibt die
    laufende Datenbank vollständig unangetastet.

    Ein Prozesslock verhindert, dass zwei Wiederherstellungen gleichzeitig
    laufen – ein zweiter Aufruf während einer laufenden Wiederherstellung
    träfe auf eine Datenbank im Umbau.
    """
    if not source.is_file():
        raise FileNotFoundError(f"Sicherung nicht gefunden: {source}")

    with _restore_lock:
        tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp_db.close()
        tmp_db_path = Path(tmp_db.name)
        try:
            try:
                with gzip.open(source, "rb") as f_in, open(tmp_db_path, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out, length=1024 * 1024)
            except gzip.BadGzipFile as exc:
                raise RestoreError(f"Keine gültige gzip-Datei: {exc}") from exc

            _validate_candidate(tmp_db_path)

            # Sicherheitsnetz: der aktuelle Bestand wird weggesichert, BEVOR er
            # angefasst wird. Schlägt das fehl (z. B. Datenträger voll), bricht
            # die Wiederherstellung hier ab statt einen unwiederbringlichen
            # Zustand zu riskieren.
            safety = create_backup()

            from .database import engine, init_db
            engine.dispose()      # Sperren/Verbindungen freigeben vor dem Dateitausch

            target = _source_path()
            for suffix in ("-wal", "-shm"):
                Path(str(target) + suffix).unlink(missing_ok=True)
            shutil.move(str(tmp_db_path), str(target))

            init_db()              # legt fehlende Tabellen an, wendet Migrationen erneut an

            log.warning("Datenbank wiederhergestellt aus %s (Sicherheitskopie: %s)",
                        source.name, safety["file"])
            _record_restore_audit(source.name, safety["file"])
            return {"restored_from": source.name, "safety_backup": safety["file"]}
        finally:
            tmp_db_path.unlink(missing_ok=True)


def list_backups() -> list[dict]:
    """Eigene Sicherungen, neueste zuerst. Fremde Dateien werden ignoriert."""
    out = []
    for entry in backup_dir().iterdir():
        if not entry.is_file():
            continue
        match = FILENAME_RE.match(entry.name)
        if not match:
            continue
        stamp = datetime.strptime(match.group(1) + match.group(2), "%Y%m%d%H%M%S")
        out.append({
            "file": entry.name,
            "created": stamp.isoformat(timespec="seconds"),
            "size_bytes": entry.stat().st_size,
            "age_days": (datetime.now() - stamp).days,
        })
    return sorted(out, key=lambda b: b["created"], reverse=True)


def prune(keep_days: int = 7, keep_min: int = 3) -> list[str]:
    """Rollierende Bereinigung.

    `keep_min` ist die Sicherung gegen die Sicherung: selbst wenn alle
    vorhandenen Sicherungen älter als `keep_days` sind – etwa weil das Add-on
    zwei Wochen aus war – bleiben die neuesten erhalten. Andernfalls würde
    ein einzelner Start ohne erfolgreiche Neusicherung den gesamten Bestand
    löschen.
    """
    entries = list_backups()
    if len(entries) <= keep_min:
        return []
    cutoff = datetime.now() - timedelta(days=keep_days)
    removed = []
    for entry in entries[keep_min:]:
        if datetime.fromisoformat(entry["created"]) < cutoff:
            path = backup_dir() / entry["file"]
            if FILENAME_RE.match(path.name):        # doppelter Boden
                path.unlink(missing_ok=True)
                removed.append(entry["file"])
    if removed:
        log.info("Bereinigt: %s Sicherung(en) entfernt", len(removed))
    return removed


def apply_telemetry_retention(session, keep_days: int) -> int:
    """Verdünnt hochfrequente MQTT-Telemetrie, die älter als `keep_days` ist,
    auf einen Datensatz je Kalendermonat und System. Gibt die Zahl der
    gelöschten Datensätze zurück.

    Sicherheiten:
      - Nur `source == 'mqtt'` wird angefasst. Von Hand erfasste, importierte
        oder aus Home Assistant übernommene Werte sind bewusste Aufzeichnungen
        und bleiben immer erhalten.
      - Behalten wird je (System, Jahr-Monat) der ÄLTESTE Datensatz. Genau so
        bleibt der allererste Zählerstand (die Basislinie) erhalten und der
        Gesamtverbrauch exakt: bei kumulativen Ständen ist er Endstand minus
        Anfangsstand, und beide bleiben stehen. Nur die zeitliche Auflösung
        alter Telemetrie sinkt (Monats- statt Tagespunkte). Behielte man
        stattdessen den jüngsten je Monat, ginge der Anfangsstand des ersten
        Monats verloren und der Gesamtverbrauch fiele zu niedrig aus.
      - keep_days <= 0 schaltet die Reduktion vollständig ab.
      - Die aktuellen `keep_days` Tage bleiben in voller Auflösung.
    """
    if not keep_days or keep_days <= 0:
        return 0
    from datetime import date, datetime as _dt
    from sqlmodel import select
    from .models import Reading

    cutoff = date.today() - timedelta(days=int(keep_days))
    cutoff_dt = _dt(cutoff.year, cutoff.month, cutoff.day)
    rows = session.exec(
        select(Reading).where(Reading.source == "mqtt", Reading.datum < cutoff_dt)
    ).all()

    # Je (System, Jahr, Monat) den ÄLTESTEN Datensatz behalten – so überlebt
    # der Anfangsstand jeder Reihe und der Gesamtverbrauch bleibt exakt.
    keep_id: dict[tuple, tuple] = {}
    for r in rows:
        key = (r.system_id, r.datum.year, r.datum.month)
        cur = keep_id.get(key)
        if cur is None or r.datum < cur[1] or (r.datum == cur[1] and r.id < cur[0]):
            keep_id[key] = (r.id, r.datum)
    keep = {v[0] for v in keep_id.values()}

    removed = 0
    for r in rows:
        if r.id not in keep:
            session.delete(r)      # über das ORM -> im Protokoll als Sammeleintrag
            removed += 1
    if removed:
        session.commit()
    return removed


def run_housekeeping(audit_keep_days: int = 365, telemetry_keep_days: int = 0) -> dict:
    """Tägliche Datenpflege, unabhängig von der Sicherung: Protokoll beschneiden
    und alte Telemetrie verdünnen. Läuft auch, wenn die automatische Sicherung
    abgeschaltet ist – die Datenbank soll trotzdem nicht unbegrenzt wachsen."""
    info = {"audit_pruned": 0, "telemetry_reduced": 0}
    try:
        from sqlmodel import Session
        from . import audit
        from .database import engine
        with Session(engine) as session:
            info["audit_pruned"] = audit.prune(session, audit_keep_days)
            session.commit()
            info["telemetry_reduced"] = apply_telemetry_retention(session, telemetry_keep_days)
        if info["telemetry_reduced"]:
            log.info("Telemetrie-Retention: %s alte MQTT-Datensätze auf Monatswerte reduziert",
                     info["telemetry_reduced"])
    except Exception as exc:  # noqa: BLE001
        log.warning("Datenpflege übersprungen: %s", exc)
    return info


def run_once(keep_days: int = 7, audit_keep_days: int = 365,
             telemetry_keep_days: int = 0) -> dict:
    info = create_backup()
    info["pruned"] = prune(keep_days)
    # Änderungsprotokoll + Telemetrie im selben Lauf pflegen: beide wachsen
    # laufend und brauchen sonst einen zweiten Zeitplan.
    info.update(run_housekeeping(audit_keep_days, telemetry_keep_days))
    return info


def _seconds_until(hhmm: str) -> float:
    """Sekunden bis zur nächsten Ausführung. Ungültige Zeitangabe -> 03:30."""
    try:
        hour, minute = (int(x) for x in str(hhmm).split(":", 1))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
    except (TypeError, ValueError):
        hour, minute = 3, 30
    now = datetime.now()
    nxt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if nxt <= now:
        nxt += timedelta(days=1)
    return (nxt - now).total_seconds()


async def scheduler() -> None:
    """Tagesplaner. Bewusst kein cron: das Add-on-Image bringt keinen Cron-Daemon
    mit, und ein zweiter Prozess müsste sich die Datenbank mit uvicorn teilen.
    Ein asyncio-Task im laufenden Prozess kennt die Einstellungen ohnehin.

    Einstellungen werden vor JEDEM Durchlauf neu gelesen – Änderungen an
    Uhrzeit, Aufbewahrung oder Ein/Aus greifen ohne Neustart.
    """
    await asyncio.sleep(120)      # Startphase abwarten
    while True:
        try:
            from .routers.settings import get_setting
            enabled = await asyncio.to_thread(get_setting, "backup_enabled", True)
            at = await asyncio.to_thread(get_setting, "backup_time", "03:30")
            keep = int(await asyncio.to_thread(get_setting, "backup_keep_days", 7))
            audit_keep = int(await asyncio.to_thread(get_setting, "audit_keep_days", 365))
            telemetry_keep = int(await asyncio.to_thread(get_setting, "telemetry_keep_days", 0))
        except Exception:  # noqa: BLE001
            enabled, at, keep, audit_keep, telemetry_keep = True, "03:30", 7, 365, 0

        wait = _seconds_until(at)
        # Nicht länger als eine Stunde am Stück schlafen: sonst würde eine
        # Änderung der Uhrzeit erst am Folgetag wirksam.
        await asyncio.sleep(min(wait, 3600))
        if wait > 3600:
            continue
        try:
            if enabled:
                await asyncio.to_thread(run_once, keep, audit_keep, telemetry_keep)
            else:
                # Sicherung aus, Datenpflege trotzdem: Protokoll und Telemetrie
                # sollen nicht unbegrenzt wachsen, nur weil kein Backup läuft.
                await asyncio.to_thread(run_housekeeping, audit_keep, telemetry_keep)
        except Exception as exc:  # noqa: BLE001
            log.error("Tägliche Datenpflege/Sicherung fehlgeschlagen: %s", exc)
        await asyncio.sleep(90)   # Doppelauslösung innerhalb derselben Minute vermeiden
