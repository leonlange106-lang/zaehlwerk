"""Datenmodell (SQLite) – Stammdaten, Messwerte, Zähler-Metadaten, Einstellungen."""
import uuid
from datetime import date, datetime
from enum import Enum
from typing import Optional

from sqlmodel import Column, Field, JSON, SQLModel


class SystemType(str, Enum):
    strom = "Strom"
    gas = "Gas"
    wasser = "Wasser"
    pv_erzeugung = "PV-Erzeugung"
    pv_einspeisung = "PV-Einspeisung"
    custom = "Custom"


class System(SQLModel, table=True):
    __tablename__ = "systems"

    # Stabile UUID (niemals der Name – Namen können sich ändern)
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str
    typ: str
    einheit: str
    farbe: str = "#3b82f6"
    icon: str = "bolt"
    # Typ-spezifische Zusatzfelder (z.B. Gas: brennwert; PV: kwp) als JSON -> generisch erweiterbar
    zusatzfelder: dict = Field(default_factory=dict, sa_column=Column(JSON))
    # Kein Hard-Delete: Systeme werden archiviert (aktiv=False), Messreihen bleiben erhalten
    aktiv: bool = True
    erstellt_am: datetime = Field(default_factory=datetime.utcnow)


class Reading(SQLModel, table=True):
    __tablename__ = "readings"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    system_id: str = Field(index=True, foreign_key="systems.id")
    datum: datetime = Field(index=True)          # Ablesedatum (nicht Erfassungszeitpunkt)
    value: float
    cost: Optional[float] = None
    meter_replaced: bool = False
    # Startstand des NEUEN Zählers beim Zählertausch. Nur relevant, wenn
    # meter_replaced=True. Der Verbrauch des Tausch-Intervalls ist dann
    # value - meter_start statt (wie bisher) value - 0. Bleibt das Feld leer,
    # gilt weiter die 0-Annahme (neuer Zähler startet bei 0). Seit Migration 9.
    meter_start: Optional[float] = None
    note: Optional[str] = None
    # Herkunft: manual | mqtt | ha_api | import. Spalte existiert seit
    # Migration 7 (source-Spalte an readings ergänzen); hier bisher nicht
    # deklariert. Ohne Deklaration kennt die ORM-Zuordnung die Spalte nicht -
    # generierte INSERTs ließen sie aus, SQLite füllte sie über den
    # Spalten-Standardwert 'manual' auf. Jede Ablesung landete dadurch
    # unabhängig von ihrer echten Herkunft als 'manual' in der Datenbank, und
    # `Reading.source` als Filterausdruck (z. B. beim Rohdaten-Export) war
    # nicht auswertbar.
    source: str = Field(default="manual", index=True)



class Meter(SQLModel, table=True):
    """Physischer Zähler als eigene Entität, 1:N unter einem System.

    Warum nicht als Spalten am System: Ein System (z. B. "Strom Hauptzähler")
    überlebt mehrere physische Zähler – der Zählertausch ist bereits über
    `Reading.meter_replaced` abgebildet. Metadaten am System würden beim
    Tausch die Historie des alten Geräts überschreiben.

    Bewusst NICHT verknüpft mit der Verbrauchsberechnung: `logic.py` bleibt
    unverändert. Diese Tabelle ist reine Dokumentation (Eichfrist, Seriennummer,
    Hersteller) und kann fehlen, ohne dass eine Auswertung bricht.
    """
    __tablename__ = "meters"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    system_id: str = Field(index=True, foreign_key="systems.id")

    hersteller: Optional[str] = None          # z. B. "Pipersberg", "EasyMeter", "Landis+Gyr"
    modell: Optional[str] = None              # z. B. "mMe4.0", "Q4000"
    zaehlernummer: Optional[str] = Field(default=None, index=True)   # aufgedruckte Nummer
    bauart: Optional[str] = None              # z. B. "Balgengaszaehler", "Ferraris", "mME"
    baujahr: Optional[int] = None

    # Eichfrist: in D je nach Medium 5-16 Jahre. Praktischer Kern dieser Tabelle.
    eichung_bis: Optional[date] = Field(default=None, index=True)
    messstellenbetreiber: Optional[str] = None

    # Stellenzahl -> Grundlage fuer Plausibilitaet und Ueberlauferkennung
    stellen_vor: Optional[int] = None
    stellen_nach: Optional[int] = None

    eingebaut_am: Optional[date] = None
    ausgebaut_am: Optional[date] = None        # None = aktuell verbaut
    notiz: Optional[str] = None
    erstellt_am: datetime = Field(default_factory=datetime.utcnow)


class User(SQLModel, table=True):
    """Benutzerkonto.

    `password_hash` ist bewusst optional: Nutzer, die über Home-Assistant-Ingress
    kommen, haben hier gar kein Passwort – ihre Anmeldung ist bereits vor dem
    Add-on erfolgt. `external_id` hält in diesem Fall die HA-Benutzerkennung.
    """
    __tablename__ = "users"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    username: str = Field(index=True, unique=True)
    display_name: Optional[str] = None
    password_hash: Optional[str] = None          # None = Anmeldung über Ingress
    external_id: Optional[str] = Field(default=None, index=True)   # HA-Benutzerkennung
    # Rolle steuert die Rechte. `is_admin` bleibt als Feld erhalten, wird aber
    # nur noch aus der Rolle abgeleitet – Doppelpflege wäre eine Fehlerquelle.
    role: str = Field(default="viewer", index=True)
    is_admin: bool = False
    aktiv: bool = True
    # Persönliches Dashboard als JSON-Zeichenkette. Bewusst am Nutzer und nicht
    # in einer eigenen Tabelle: es gibt genau ein Layout je Konto, und ein
    # Verbund über eine 1:1-Beziehung wäre nur zusätzlicher Aufwand.
    dashboard_layout: Optional[str] = None
    letzter_login: Optional[datetime] = None
    erstellt_am: datetime = Field(default_factory=datetime.utcnow)
    # Zwei-Faktor (TOTP). Das Secret liegt Fernet-verschlüsselt (Schlüssel
    # ausserhalb der DB, siehe app/twofactor.py); `two_factor_enabled` wird erst
    # nach erfolgreicher Verifikation des ersten Codes gesetzt.
    two_factor_secret: Optional[str] = None
    two_factor_enabled: bool = False
    # Erstanmelde-Zwang: Ein vom Admin angelegtes Konto startet mit einem
    # temporären Passwort (`temp_password_active`) und muss beim ersten Login
    # Passwort ändern UND 2FA einrichten (`is_first_login`), bevor die regulären
    # Routen freigegeben werden.
    temp_password_active: bool = False
    is_first_login: bool = False


class Tariff(SQLModel, table=True):
    """Tarifperiode eines Systems.

    Zeitscheiben statt eines einzelnen Preises am System: Preise ändern sich,
    und ein Bestand über 24 Jahre mit einem heutigen Arbeitspreis zu bewerten
    wäre schlicht falsch. Jede Periode gilt ab `gueltig_ab` bis `gueltig_bis`;
    ist letzteres leer, läuft sie bis auf Weiteres.

    Der bestehende Ø-Preis in `System.zusatzfelder["preis"]` bleibt unberührt
    und dient weiter als grobe Schätzung, wenn für einen Zeitraum kein Tarif
    hinterlegt ist.
    """
    __tablename__ = "tariffs"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    system_id: str = Field(index=True, foreign_key="systems.id")

    name: Optional[str] = None                 # z. B. "Grundversorgung 2024"
    anbieter: Optional[str] = None
    gueltig_ab: date = Field(index=True)
    gueltig_bis: Optional[date] = Field(default=None, index=True)   # None = offen

    arbeitspreis: float                        # € je Einheit (kWh, m³ …), brutto
    # € je JAHR, brutto (seit v3.18.0 / Migration 10). Zuvor ein Monatsbetrag;
    # die Migration hat Bestandswerte einmalig mit 12 multipliziert, damit der
    # tatsächliche Euro-Betrag erhalten bleibt. Tagesgenaue Abrechnung:
    # grundpreis / Tage-des-Jahres je Verbrauchstag (siehe logic.apply_tariffs).
    grundpreis: float = 0.0
    notiz: Optional[str] = None
    erstellt_am: datetime = Field(default_factory=datetime.utcnow)


class AuditLog(SQLModel, table=True):
    """Änderungsprotokoll. Wird ausschließlich angehängt.

    Ohne Fremdschlüssel auf `users`: der Eintrag muss auch dann bestehen
    bleiben, wenn das Konto später entfernt wird – sonst verschwände mit dem
    Konto genau die Spur, die es zu dokumentieren gilt. Der Benutzername wird
    deshalb zusätzlich als Text mitgeführt.
    """
    __tablename__ = "audit_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    ts: datetime = Field(default_factory=datetime.utcnow, index=True)
    user_id: Optional[str] = Field(default=None, index=True)
    username: Optional[str] = None
    action: str = Field(index=True)               # INSERT | UPDATE | DELETE
    target_table: str = Field(index=True)
    target_id: Optional[str] = Field(default=None, index=True)
    old_value: Optional[str] = None               # JSON
    new_value: Optional[str] = None               # JSON


class AppSetting(SQLModel, table=True):
    """Anwendungsweite Einstellungen als Key/Value.

    Bewusst KV statt einer Spalte je Option: neue Optionen brauchen dann keine
    Schemaänderung und damit keine weitere Migration. Werte werden als Text
    abgelegt und beim Lesen typisiert (siehe routers/settings.py).
    """
    __tablename__ = "app_settings"

    key: str = Field(primary_key=True)
    value: str


# --------------------------------------------------------------------------
# Multi-Tenant: Routing & Rechte (leben ausschließlich in der zentralen
# System-DB, nicht in den Mandanten-Datenbanken)
# --------------------------------------------------------------------------
class DatabaseRole(str, Enum):
    """Rolle eines Nutzers auf einer konkreten Datenbank."""
    owner = "owner"            # Eigentümer: volle Kontrolle inkl. Freigaben
    read_write = "read_write"  # darf lesen und schreiben
    read_only = "read_only"    # darf nur lesen


class UserDatabase(SQLModel, table=True):
    """Registrierung einer Mandanten-Datenbank (zentrale System-DB).

    Jeder Nutzer erhält standardmäßig genau eine eigene, isolierte SQLite-Datei.
    Diese Tabelle bildet das Routing ab: welche Datei zu welchem Eigentümer
    gehört. `filename` ist relativ zum Tenants-Verzeichnis; die beim Umzug
    übernommene Bestands-Datenbank trägt `is_default=True` und einen absoluten
    Pfad.
    """
    __tablename__ = "user_databases"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str
    owner_user_id: str = Field(index=True)          # verweist auf users.id (System-DB)
    filename: str                                   # relativ zu TENANTS_DIR (oder absolut = Bestand)
    db_kind: str = "sqlite"
    is_default: bool = False                        # die übernommene Bestands-DB
    erstellt_am: datetime = Field(default_factory=datetime.utcnow)


class DatabaseAccess(SQLModel, table=True):
    """Zugriffs-/Rollen-Matrix: welcher Nutzer darf mit welcher DB was.

    Freigaben an andere Nutzer laufen über diese Tabelle (Multi-User-Access auf
    eine DB). Die Eigentümerschaft ergibt sich zusätzlich aus
    `UserDatabase.owner_user_id`; für den Eigentümer wird beim Anlegen zudem ein
    expliziter `owner`-Eintrag geschrieben. Liegt in der zentralen System-DB.
    """
    __tablename__ = "database_access"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(index=True)
    database_id: str = Field(index=True)
    role: str = Field(default=DatabaseRole.read_only.value)
    erstellt_am: datetime = Field(default_factory=datetime.utcnow)
