"""Schema-Migrationen über PRAGMA user_version.

Warum überhaupt: `SQLModel.metadata.create_all()` legt fehlende Tabellen an,
ändert aber NIE bestehende. Ohne dieses Modul würde jede neue Spalte auf
Bestandsinstallationen still mit `OperationalError: no such column` enden.

Ablauf: SQLite hält pro Datei einen Integer (`PRAGMA user_version`, Default 0).
Beim Start läuft jede Migration mit einer höheren Nummer als der gespeicherten
Version genau einmal, aufsteigend, in einer Transaktion. Danach wird die
Version hochgesetzt. Ist die DB neu, hat `create_all()` bereits alles angelegt –
die Migrationen sind deshalb konsequent idempotent formuliert
(`ADD COLUMN` nur nach Spaltenprüfung).

Neue Migration ergänzen: Funktion schreiben, unten in MIGRATIONS eintragen.
Nummern werden nie wiederverwendet und nie umsortiert.
"""
import logging

from sqlalchemy import text
from sqlalchemy.engine import Connection

log = logging.getLogger("zaehlwerk.migrations")


def _columns(conn: Connection, table: str) -> set[str]:
    rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return {r[1] for r in rows}


def _table_exists(conn: Connection, table: str) -> bool:
    row = conn.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name=:t"),
        {"t": table},
    ).fetchone()
    return row is not None


# --------------------------------------------------------------------------
# Migration 1: Tabelle für anwendungsweite Einstellungen (Key/Value)
# --------------------------------------------------------------------------
def _m001_app_settings(conn: Connection) -> None:
    if _table_exists(conn, "app_settings"):
        return
    conn.execute(text("""
        CREATE TABLE app_settings (
            key   VARCHAR NOT NULL PRIMARY KEY,
            value VARCHAR NOT NULL
        )
    """))


# --------------------------------------------------------------------------
# Migration 2: Zaehler-Metadaten
# --------------------------------------------------------------------------
def _m002_meters(conn: Connection) -> None:
    if not _table_exists(conn, "meters"):
        conn.execute(text("""
            CREATE TABLE meters (
                id                   VARCHAR NOT NULL PRIMARY KEY,
                system_id            VARCHAR NOT NULL,
                hersteller           VARCHAR,
                modell               VARCHAR,
                zaehlernummer        VARCHAR,
                bauart               VARCHAR,
                baujahr              INTEGER,
                eichung_bis          DATE,
                messstellenbetreiber VARCHAR,
                stellen_vor          INTEGER,
                stellen_nach         INTEGER,
                eingebaut_am         DATE,
                ausgebaut_am         DATE,
                notiz                VARCHAR,
                erstellt_am          DATETIME NOT NULL,
                FOREIGN KEY(system_id) REFERENCES systems(id)
            )
        """))
    # Indizes getrennt und mit IF NOT EXISTS: laeuft auch, wenn die Tabelle
    # bei einer Neuinstallation schon von create_all() angelegt wurde.
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_meters_system_id ON meters (system_id)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_meters_zaehlernummer ON meters (zaehlernummer)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_meters_eichung_bis ON meters (eichung_bis)"))


# --------------------------------------------------------------------------
# Migration 3: Tarifperioden
# --------------------------------------------------------------------------
def _m003_tariffs(conn: Connection) -> None:
    if not _table_exists(conn, "tariffs"):
        conn.execute(text("""
            CREATE TABLE tariffs (
                id           VARCHAR NOT NULL PRIMARY KEY,
                system_id    VARCHAR NOT NULL,
                name         VARCHAR,
                anbieter     VARCHAR,
                gueltig_ab   DATE NOT NULL,
                gueltig_bis  DATE,
                arbeitspreis FLOAT NOT NULL,
                grundpreis   FLOAT NOT NULL DEFAULT 0.0,
                notiz        VARCHAR,
                erstellt_am  DATETIME NOT NULL,
                FOREIGN KEY(system_id) REFERENCES systems(id)
            )
        """))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_tariffs_system_id ON tariffs (system_id)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_tariffs_gueltig_ab ON tariffs (gueltig_ab)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_tariffs_gueltig_bis ON tariffs (gueltig_bis)"))


# --------------------------------------------------------------------------
# Migration 4: Benutzerkonten
# --------------------------------------------------------------------------
def _m004_users(conn: Connection) -> None:
    if not _table_exists(conn, "users"):
        conn.execute(text("""
            CREATE TABLE users (
                id            VARCHAR NOT NULL PRIMARY KEY,
                username      VARCHAR NOT NULL,
                display_name  VARCHAR,
                password_hash VARCHAR,
                external_id   VARCHAR,
                is_admin      BOOLEAN NOT NULL DEFAULT 0,
                aktiv         BOOLEAN NOT NULL DEFAULT 1,
                letzter_login DATETIME,
                erstellt_am   DATETIME NOT NULL
            )
        """))
    conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username ON users (username)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_users_external_id ON users (external_id)"))


# --------------------------------------------------------------------------
# Migration 5: Rollen
# --------------------------------------------------------------------------
def _m005_roles(conn: Connection) -> None:
    """Erste echte Spaltenerweiterung an einer bestehenden Tabelle.

    SQLite kann `ADD COLUMN` ohne Tabellenneubau, solange ein konstanter
    Vorgabewert gesetzt wird. Die Spaltenprüfung davor macht den Schritt
    idempotent – bei einer Neuinstallation hat `create_all()` sie bereits
    angelegt und der Aufruf würde sonst mit "duplicate column" scheitern.
    """
    if "role" not in _columns(conn, "users"):
        conn.execute(text(
            "ALTER TABLE users ADD COLUMN role VARCHAR NOT NULL DEFAULT 'viewer'"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_users_role ON users (role)"))

    # Bestandskonten einordnen: bisherige Administratoren behalten ihre
    # Rechte, alle uebrigen duerfen weiterhin eintragen. Ein pauschales
    # Herabstufen auf "viewer" wuerde bestehende Installationen lahmlegen.
    conn.execute(text(
        "UPDATE users SET role = 'admin' WHERE is_admin = 1 AND role = 'viewer'"))
    conn.execute(text(
        "UPDATE users SET role = 'writer' WHERE is_admin = 0 AND role = 'viewer'"))


# --------------------------------------------------------------------------
# Migration 6: persönliches Dashboard
# --------------------------------------------------------------------------
def _m006_dashboard(conn: Connection) -> None:
    if "dashboard_layout" not in _columns(conn, "users"):
        conn.execute(text("ALTER TABLE users ADD COLUMN dashboard_layout TEXT"))


# --------------------------------------------------------------------------
# Migration 7: Herkunft der Ablesungen
# --------------------------------------------------------------------------
def _m007_reading_source(conn: Connection) -> None:
    if "source" not in _columns(conn, "readings"):
        conn.execute(text(
            "ALTER TABLE readings ADD COLUMN source VARCHAR(50) NOT NULL DEFAULT 'manual'"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_readings_source ON readings (source)"))

    # Bestandsdaten einordnen. Bis 3.6.0 kennzeichnete die MQTT-Uebernahme ihre
    # Datensaetze ueber die Notiz "MQTT" - ein Behelf, der das Notizfeld des
    # Nutzers belegte. Diese Eintraege bekommen die Herkunft und geben die
    # Notiz wieder frei; alles uebrige bleibt bei 'manual'.
    conn.execute(text("UPDATE readings SET source = 'mqtt' WHERE note = 'MQTT'"))
    conn.execute(text("UPDATE readings SET note = NULL WHERE note = 'MQTT'"))


# --------------------------------------------------------------------------
# Migration 8: Aenderungsprotokoll
# --------------------------------------------------------------------------
def _m008_audit(conn: Connection) -> None:
    if not _table_exists(conn, "audit_logs"):
        conn.execute(text("""
            CREATE TABLE audit_logs (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                ts           DATETIME NOT NULL,
                user_id      VARCHAR,
                username     VARCHAR,
                action       VARCHAR NOT NULL,
                target_table VARCHAR NOT NULL,
                target_id    VARCHAR,
                old_value    TEXT,
                new_value    TEXT
            )
        """))
    for idx, col in [("ix_audit_ts", "ts"), ("ix_audit_user", "user_id"),
                     ("ix_audit_action", "action"), ("ix_audit_table", "target_table"),
                     ("ix_audit_target", "target_id")]:
        conn.execute(text(f"CREATE INDEX IF NOT EXISTS {idx} ON audit_logs ({col})"))

    # Unveraenderlichkeit auf Datenbankebene. Die Ereignisse im ORM schuetzen
    # nur den Weg ueber die Anwendung; diese Trigger greifen auch bei einem
    # Zugriff ueber die SQL-Konsole der Admin-Werkzeuge oder ueber sqlite3.
    conn.execute(text("DROP TRIGGER IF EXISTS audit_logs_no_update"))
    conn.execute(text("""
        CREATE TRIGGER audit_logs_no_update BEFORE UPDATE ON audit_logs
        BEGIN
            SELECT RAISE(ABORT, 'audit_logs ist unveraenderlich');
        END
    """))
    # Loeschen bleibt fuer die Aufbewahrungsfrist moeglich, aber erst ab 30
    # Tagen: Bestand darf altern, ein frischer Eintrag laesst sich nicht
    # beseitigen.
    conn.execute(text("DROP TRIGGER IF EXISTS audit_logs_no_delete"))
    conn.execute(text("""
        CREATE TRIGGER audit_logs_no_delete BEFORE DELETE ON audit_logs
        WHEN OLD.ts > datetime('now', '-30 days')
        BEGIN
            SELECT RAISE(ABORT, 'Eintraege juenger als 30 Tage sind geschuetzt');
        END
    """))


# --------------------------------------------------------------------------
# Migration 9: Startstand des neuen Zaehlers beim Zaehlertausch
# --------------------------------------------------------------------------
def _m009_meter_start(conn: Connection) -> None:
    if "meter_start" not in _columns(conn, "readings"):
        conn.execute(text("ALTER TABLE readings ADD COLUMN meter_start FLOAT"))
    # Kein Backfill: NULL bedeutet "neuer Zaehler startet bei 0" - genau das
    # Verhalten, das bisher fuer jeden Tausch galt. Bestandsdaten bleiben also
    # unveraendert korrekt.


# --------------------------------------------------------------------------
# Migration 10: Grundpreis von Monats- auf Jahresbetrag umstellen
# --------------------------------------------------------------------------
def _m010_grundpreis_yearly(conn: Connection) -> None:
    """Bis v3.17.x war tariffs.grundpreis ein MONATSbetrag, ab v3.18.0 ein
    JAHRESbetrag. Damit der tatsaechlich vom Nutzer gemeinte Euro-Betrag
    erhalten bleibt, werden die Bestandswerte einmalig mit 12 multipliziert.
    Laeuft genau einmal (durch user_version abgesichert)."""
    conn.execute(text(
        "UPDATE tariffs SET grundpreis = grundpreis * 12 WHERE grundpreis IS NOT NULL"))


# --------------------------------------------------------------------------
# Migration 11: Zwei-Faktor und Erstanmelde-Zwang an users
# --------------------------------------------------------------------------
def _m011_two_factor(conn: Connection) -> None:
    """Spalten für TOTP-Zwei-Faktor und den Erstanmelde-Flow.

    Bestandskonten bleiben unangetastet: alle Flags starten auf 0/NULL, es gibt
    also keinen rückwirkenden 2FA- oder Passwortwechsel-Zwang. Neu vom Admin
    angelegte Konten setzen die Flags selbst.
    """
    cols = _columns(conn, "users")
    if "two_factor_secret" not in cols:
        conn.execute(text("ALTER TABLE users ADD COLUMN two_factor_secret TEXT"))
    if "two_factor_enabled" not in cols:
        conn.execute(text("ALTER TABLE users ADD COLUMN two_factor_enabled BOOLEAN NOT NULL DEFAULT 0"))
    if "temp_password_active" not in cols:
        conn.execute(text("ALTER TABLE users ADD COLUMN temp_password_active BOOLEAN NOT NULL DEFAULT 0"))
    if "is_first_login" not in cols:
        conn.execute(text("ALTER TABLE users ADD COLUMN is_first_login BOOLEAN NOT NULL DEFAULT 0"))


def _m012_tariff_contract(conn: Connection) -> None:
    """Vertragsunterlage (Dokument-URL) und Kündigungsfrist je Tarif.

    Grundlage für Dokument-Upload/OCR und die Vertragsende-Warnung: aus
    `gueltig_bis` minus `notice_period_days` ergibt sich der letzte Kündigungs-
    termin. Bestandsdaten bleiben unangetastet (Spalten starten auf NULL)."""
    cols = _columns(conn, "tariffs")
    if "contract_document_url" not in cols:
        conn.execute(text("ALTER TABLE tariffs ADD COLUMN contract_document_url TEXT"))
    if "notice_period_days" not in cols:
        conn.execute(text("ALTER TABLE tariffs ADD COLUMN notice_period_days INTEGER"))


def _m013_billing(conn: Connection) -> None:
    """Abrechnungserfassung (TICKET-3.1): Kennzeichen `is_billed` an Ablesungen
    (eine Ablesung, deren Kosten aus einer echten Abrechnung stammen) und eine
    Tabelle `billing_years` mit den offiziell abgerechneten Jahreskosten je
    System. Beides rückwärtskompatibel: Bestandsablesungen bleiben is_billed=0,
    die Kostenrechnung greift weiter auf Tarife zurück."""
    cols = _columns(conn, "readings")
    if "is_billed" not in cols:
        conn.execute(text("ALTER TABLE readings ADD COLUMN is_billed BOOLEAN NOT NULL DEFAULT 0"))
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS billing_years (
            id VARCHAR PRIMARY KEY,
            system_id VARCHAR NOT NULL REFERENCES systems(id),
            year INTEGER NOT NULL,
            cost FLOAT NOT NULL,
            is_billed BOOLEAN NOT NULL DEFAULT 1,
            erstellt_am DATETIME NOT NULL
        )
    """))
    conn.execute(text(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_billing_years_system_year "
        "ON billing_years (system_id, year)"))


def _m014_system_order(conn: Connection) -> None:
    """Manuelle Sortierung der Systeme (TICKET-4.1): Spalte `sort_index`. Der
    Bestand wird einmalig anhand der bisherigen Namensreihenfolge durchnummeriert,
    damit sich die Anzeige beim Update nicht sichtbar umsortiert."""
    cols = _columns(conn, "systems")
    if "sort_index" not in cols:
        conn.execute(text("ALTER TABLE systems ADD COLUMN sort_index INTEGER NOT NULL DEFAULT 0"))
        rows = conn.execute(text("SELECT id FROM systems ORDER BY name")).fetchall()
        for i, row in enumerate(rows):
            conn.execute(text("UPDATE systems SET sort_index = :i WHERE id = :id"),
                         {"i": i, "id": row[0]})


MIGRATIONS: list[tuple[int, str, callable]] = [
    (1, "app_settings-Tabelle anlegen", _m001_app_settings),
    (2, "meters-Tabelle fuer Zaehler-Metadaten anlegen", _m002_meters),
    (3, "tariffs-Tabelle fuer Tarifperioden anlegen", _m003_tariffs),
    (4, "users-Tabelle fuer Benutzerkonten anlegen", _m004_users),
    (5, "Rollenspalte an users ergaenzen", _m005_roles),
    (6, "dashboard_layout an users ergaenzen", _m006_dashboard),
    (7, "source-Spalte an readings ergaenzen", _m007_reading_source),
    (8, "audit_logs-Tabelle samt Unveraenderlichkeit anlegen", _m008_audit),
    (9, "meter_start-Spalte an readings ergaenzen", _m009_meter_start),
    (10, "grundpreis von Monats- auf Jahresbetrag umstellen", _m010_grundpreis_yearly),
    (11, "Zwei-Faktor und Erstanmelde-Zwang an users", _m011_two_factor),
    (12, "Vertragsunterlage und Kuendigungsfrist an tariffs", _m012_tariff_contract),
    (13, "Abrechnungserfassung: is_billed an readings + billing_years-Tabelle", _m013_billing),
    (14, "Manuelle Sortierung: sort_index an systems", _m014_system_order),
]


def run_migrations(engine) -> int:
    """Führt ausstehende Migrationen aus. Gibt die erreichte Schemaversion zurück."""
    with engine.begin() as conn:
        current = conn.execute(text("PRAGMA user_version")).scalar() or 0
        target = max((n for n, _, _ in MIGRATIONS), default=0)
        if current >= target:
            return current
        for number, label, fn in sorted(MIGRATIONS, key=lambda m: m[0]):
            if number <= current:
                continue
            log.info("Migration %s: %s", number, label)
            fn(conn)
            # user_version akzeptiert keine Bindeparameter -> Nummer ist eine
            # modulinterne Konstante, keine Nutzereingabe.
            conn.execute(text(f"PRAGMA user_version = {int(number)}"))
        return target


def schema_version(engine) -> int:
    with engine.connect() as conn:
        return conn.execute(text("PRAGMA user_version")).scalar() or 0
