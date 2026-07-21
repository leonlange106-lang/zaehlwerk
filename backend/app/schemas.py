"""Request-/Response-Schemas (API-Vertrag), getrennt von der DB-Tabelle."""
from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------- Systeme ----------
class SystemCreate(BaseModel):
    name: str
    typ: str
    einheit: str
    farbe: str = "#3b82f6"
    icon: str = "bolt"
    zusatzfelder: dict[str, Any] = Field(default_factory=dict)


class SystemUpdate(BaseModel):
    name: Optional[str] = None
    typ: Optional[str] = None
    einheit: Optional[str] = None
    farbe: Optional[str] = None
    icon: Optional[str] = None
    zusatzfelder: Optional[dict[str, Any]] = None
    aktiv: Optional[bool] = None  # Archivieren = aktiv:false


class SystemRead(BaseModel):
    id: str
    name: str
    typ: str
    einheit: str
    farbe: str
    icon: str
    zusatzfelder: dict[str, Any]
    aktiv: bool
    erstellt_am: datetime


# ---------- Ablesungen ----------
# Herkunftskennungen. 'mqtt' fehlt bewusst: sie wird ausschließlich vom
# Listener gesetzt und darf nicht über die Schnittstelle behauptet werden –
# sonst ließen sich Datensätze als automatisch erfasst ausgeben.
READING_SOURCES_CLIENT = ("manual", "ha_api")
READING_SOURCES_ALL = ("manual", "ha_api", "mqtt", "import")


class ReadingCreate(BaseModel):
    datum: date                       # Ablesedatum, NICHT Erfassungszeitpunkt
    value: float
    cost: Optional[float] = None
    meter_replaced: bool = False      # Zählertausch
    # Startstand des neuen Zählers beim Tausch (nur mit meter_replaced=True).
    # Ohne Angabe gilt weiter: neuer Zähler startet bei 0.
    meter_start: Optional[float] = Field(None, ge=0)
    note: Optional[str] = None
    source: str = Field("manual", pattern="^(manual|ha_api)$")

    @model_validator(mode="after")
    def _meter_start_needs_replace(self):
        # Ein Startstand ohne Zählertausch ist widersprüchlich – lieber früh
        # abweisen als still ignorieren.
        if self.meter_start is not None and not self.meter_replaced:
            raise ValueError("meter_start ist nur bei meter_replaced=True zulässig")
        if self.meter_start is not None and self.meter_start > self.value:
            raise ValueError("Startstand des neuen Zählers darf nicht über dem Ablesewert liegen")
        return self


class ReadingRead(BaseModel):
    id: str                           # base64(system_id|timestamp_ns)
    system_id: str
    datum: datetime
    value: float
    cost: Optional[float] = None
    meter_replaced: bool = False
    meter_start: Optional[float] = None
    note: Optional[str] = None
    source: str = "manual"
    # abgeleitete Felder
    consumption: Optional[float] = None
    consumption_per_day: Optional[float] = None
    is_outlier: bool = False
    cost_effective: Optional[float] = None
    cost_estimated: bool = False


# ---------- Statistik / Chart ----------
class StatsRead(BaseModel):
    total_consumption: float
    total_cost: float
    total_days: float
    avg_per_day: Optional[float] = None
    cost_per_day: Optional[float] = None
    cost_per_unit: Optional[float] = None
    min_per_day: Optional[float] = None
    min_per_day_datum: Optional[datetime] = None
    max_per_day: Optional[float] = None
    max_per_day_datum: Optional[datetime] = None
    outlier_threshold: Optional[float] = None
    reading_count: int = 0
    cost_estimated: bool = False
    # Tarifbasierte Kosten (2.16.0). None, solange keine Tarifperiode greift.
    total_cost_tariff: Optional[float] = None
    total_energy_cost: Optional[float] = None
    total_base_cost: Optional[float] = None
    avg_price_effective: Optional[float] = None
    covered_intervals: int = 0
    coverage_ratio: float = 0.0


class ChartData(BaseModel):
    system_id: str
    name: str
    unit: str
    color: str
    labels: list[str]
    values: list[Optional[float]]
    consumption: list[Optional[float]]
    consumption_per_day: list[Optional[float]]
    outliers: list[bool]
    meter_replaced: list[bool]


class ImportResult(BaseModel):
    imported: int
    skipped: int
    errors: list[str]


# ---------- Anwendungseinstellungen ----------
class AppSettingsRead(BaseModel):
    offline_mode: bool
    backup_enabled: bool
    backup_time: str
    backup_keep_days: int
    mqtt_enabled: bool = False
    mqtt_use_supervisor: bool = True
    mqtt_host: str = ""
    mqtt_port: int = 1883
    mqtt_username: str = ""
    mqtt_base_topic: str = "tele"
    mqtt_tasmota_discovery: bool = False
    mqtt_interval: str = "daily"
    mqtt_watchdog_enabled: bool = True
    mqtt_watchdog_hours: int = 48
    default_role: str = "writer"
    audit_keep_days: int = 365
    telemetry_keep_days: int = 0
    # Kein Passwortfeld: der Server gibt nur bekannt, ob eines hinterlegt ist.
    mqtt_password_set: bool = False
    notify_enabled: bool
    notify_interval_hours: int
    default_interval_days: int
    outlier_sigma: float


class AppSettingsUpdate(BaseModel):
    """Teil-Update mit Grenzen. Verstoesse -> HTTP 422 VOR dem Schreibzugriff.

    Grenzen begruendet:
    - notify_interval_hours 1..168: unter 1 h waere Spam, ueber 7 Tage sinnlos,
      weil Ablesungen frueher faellig werden.
    - default_interval_days 0..3650: 0 = automatische Median-Prognose.
    - outlier_sigma 1.0..5.0: unter 1 sigma waere fast jeder Wert ein
      Ausreisser, ueber 5 sigma praktisch keiner mehr.
    """
    # Kill-Switch. Standard ist AN: externe Abfragen muessen bewusst
    # freigeschaltet werden, nicht bewusst abgeschaltet.
    offline_mode: Optional[bool] = None
    notify_enabled: Optional[bool] = None
    notify_interval_hours: Optional[int] = Field(None, ge=1, le=168)
    default_interval_days: Optional[int] = Field(None, ge=0, le=3650)
    outlier_sigma: Optional[float] = Field(None, ge=1.0, le=5.0)
    backup_enabled: Optional[bool] = None
    # HH:MM, 24h. Muster statt Freitext -> _seconds_until() bekommt nie Muell.
    backup_time: Optional[str] = Field(None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    # Untergrenze 1 Tag; oben 365, darueber laeuft /backup unnoetig voll.
    backup_keep_days: Optional[int] = Field(None, ge=1, le=365)
    mqtt_enabled: Optional[bool] = None
    mqtt_use_supervisor: Optional[bool] = None
    mqtt_host: Optional[str] = Field(None, max_length=200)
    mqtt_port: Optional[int] = Field(None, ge=1, le=65535)
    mqtt_username: Optional[str] = Field(None, max_length=120)
    mqtt_password: Optional[str] = Field(None, max_length=256)
    mqtt_base_topic: Optional[str] = Field(None, max_length=120)
    mqtt_tasmota_discovery: Optional[bool] = None
    mqtt_interval: Optional[str] = Field(
        None, pattern="^(daily|weekly|monthly|quarterly|yearly)$")
    mqtt_watchdog_enabled: Optional[bool] = None
    # Untergrenze 1 h waere praktisch dauerbeschaeftigt, Obergrenze 14 Tage
    # macht die Meldung nutzlos verspaetet.
    mqtt_watchdog_hours: Optional[int] = Field(None, ge=1, le=336)
    default_role: Optional[str] = Field(None, pattern="^(guest|viewer|writer|admin)$")
    # Untergrenze entspricht der Schutzfrist der Trigger – ein kleinerer Wert
    # würde von der Datenbank ohnehin nicht durchgesetzt.
    audit_keep_days: Optional[int] = Field(None, ge=30, le=3650)
    # 0 = unbegrenzt. Obergrenze 100 Jahre als Tippfehlerbremse. Untergrenze 0,
    # damit sich die Reduktion vollständig abschalten lässt.
    telemetry_keep_days: Optional[int] = Field(None, ge=0, le=36500)

    @field_validator("outlier_sigma")
    @classmethod
    def _round_sigma(cls, v):
        return None if v is None else round(v, 2)


class SystemInfo(BaseModel):
    """Read-only Laufzeitdiagnose (Sektion A der Einstellungen)."""
    app_version: str
    schema_version: int
    python_version: str
    platform: str
    db_path: str
    db_exists: bool
    db_size_bytes: int
    journal_mode: str
    foreign_keys: bool
    runtime: str
    supervisor_available: bool
    system_count: int
    reading_count: int
    meter_count: int = 0
    offline_mode: bool = True
    socket_guard_active: bool = False


# ---------- Zähler-Metadaten ----------
# Vorschlagswerte für die UI. Bewusst KEIN Enum in der DB: der Markt bringt
# laufend neue Bauarten, ein Enum würde bei jedem neuen Typ eine Migration
# erzwingen. Freitext + Vorschlagsliste ist hier robuster.
BAUART_VORSCHLAEGE = [
    "mME (moderne Messeinrichtung)", "iMSys (intelligentes Messsystem)",
    "Ferraris-Zähler", "Drehstromzähler", "Wechselstromzähler",
    "Balgengaszähler", "Ultraschall-Gaszähler", "Drehkolbengaszähler",
    "Flügelradzähler", "Woltmannzähler", "Ultraschall-Wasserzähler",
]


class MeterBase(BaseModel):
    hersteller: Optional[str] = Field(None, max_length=120)
    modell: Optional[str] = Field(None, max_length=120)
    zaehlernummer: Optional[str] = Field(None, max_length=80)
    bauart: Optional[str] = Field(None, max_length=120)
    baujahr: Optional[int] = Field(None, ge=1900, le=2100)
    eichung_bis: Optional[date] = None
    messstellenbetreiber: Optional[str] = Field(None, max_length=160)
    stellen_vor: Optional[int] = Field(None, ge=1, le=12)
    stellen_nach: Optional[int] = Field(None, ge=0, le=6)
    eingebaut_am: Optional[date] = None
    ausgebaut_am: Optional[date] = None
    notiz: Optional[str] = Field(None, max_length=1000)

    @field_validator("hersteller", "modell", "zaehlernummer", "bauart",
                     "messstellenbetreiber", "notiz", mode="before")
    @classmethod
    def _trim(cls, v):
        """Leerstrings aus Formularen zu None – sonst steht in der DB "" statt NULL."""
        if v is None:
            return None
        v = str(v).strip()
        return v or None

    @model_validator(mode="after")
    def _check_dates(self):
        if self.eingebaut_am and self.ausgebaut_am and self.ausgebaut_am < self.eingebaut_am:
            raise ValueError("ausgebaut_am darf nicht vor eingebaut_am liegen")
        if self.baujahr and self.eingebaut_am and self.eingebaut_am.year < self.baujahr:
            raise ValueError("eingebaut_am liegt vor dem Baujahr")
        return self


class MeterCreate(MeterBase):
    pass


class MeterUpdate(MeterBase):
    pass


class MeterRead(MeterBase):
    id: str
    system_id: str
    erstellt_am: datetime
    # abgeleitet, nicht gespeichert
    aktiv: bool = True                        # ausgebaut_am is None
    eichung_faellig_in_tagen: Optional[int] = None
    eichung_abgelaufen: bool = False


class MeterCalibrationEntry(BaseModel):
    """Eintrag der Eichfristen-Übersicht."""
    meter_id: str
    system_id: str
    system_name: str
    zaehlernummer: Optional[str] = None
    hersteller: Optional[str] = None
    eichung_bis: date
    faellig_in_tagen: int
    abgelaufen: bool


# ---------- Externe Daten / Kill-Switch ----------
class ExternalStatus(BaseModel):
    offline_mode: bool
    socket_guard_active: bool
    providers: list[dict[str, Any]]
    cache: list[dict[str, Any]]


class WeatherRead(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    dates: list[str] = []
    temp_max: list[Optional[float]] = []
    temp_min: list[Optional[float]] = []
    cached: bool = False
    stale: bool = False
    age_seconds: int = 0


class TariffRead(BaseModel):
    market: str
    slots: list[dict[str, Any]] = []
    min_ct: Optional[float] = None
    max_ct: Optional[float] = None
    avg_ct: Optional[float] = None
    cached: bool = False
    stale: bool = False
    age_seconds: int = 0


# ---------- Sicherungen ----------
class BackupEntry(BaseModel):
    file: str
    created: str
    size_bytes: int
    age_days: int


class BackupStatus(BaseModel):
    enabled: bool
    directory: str
    supervisor_backup_dir: bool     # True = /backup gemappt, False = Rückfall auf /share
    time: str
    keep_days: int
    entries: list[BackupEntry]
    total_bytes: int


class RestoreResult(BaseModel):
    restored_from: str
    safety_backup: Optional[str] = None


# ---------- Tarifperioden ----------
class TariffStats(BaseModel):
    """Tarifkennzahlen, werden der Statistik beigemischt."""
    total_cost_tariff: Optional[float] = None
    total_energy_cost: Optional[float] = None
    total_base_cost: Optional[float] = None
    avg_price_effective: Optional[float] = None
    covered_intervals: int = 0
    coverage_ratio: float = 0.0


class TariffPlanBase(BaseModel):
    name: Optional[str] = Field(None, max_length=120)
    anbieter: Optional[str] = Field(None, max_length=120)
    gueltig_ab: date
    gueltig_bis: Optional[date] = None
    # Obergrenzen als Tippfehlerbremse: 100 €/Einheit und 5000 €/Jahr sind weit
    # jenseits realer Tarife, fangen aber ein verrutschtes Komma ab. grundpreis
    # ist seit v3.18.0 ein JAHRESbetrag (zuvor 1000 €/Monat als Grenze).
    arbeitspreis: float = Field(..., ge=0, le=100)
    grundpreis: float = Field(0.0, ge=0, le=5000)
    notiz: Optional[str] = Field(None, max_length=500)

    @field_validator("name", "anbieter", "notiz", mode="before")
    @classmethod
    def _trim(cls, v):
        if v is None:
            return None
        v = str(v).strip()
        return v or None

    @model_validator(mode="after")
    def _check_range(self):
        if self.gueltig_bis and self.gueltig_bis < self.gueltig_ab:
            raise ValueError("gueltig_bis darf nicht vor gueltig_ab liegen")
        return self


class TariffPlanCreate(TariffPlanBase):
    pass


class TariffPlanUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=120)
    anbieter: Optional[str] = Field(None, max_length=120)
    gueltig_ab: Optional[date] = None
    gueltig_bis: Optional[date] = None
    arbeitspreis: Optional[float] = Field(None, ge=0, le=100)
    grundpreis: Optional[float] = Field(None, ge=0, le=5000)   # €/Jahr seit v3.18.0
    notiz: Optional[str] = Field(None, max_length=500)


class TariffPlanRead(TariffPlanBase):
    id: str
    system_id: str
    erstellt_am: datetime
    aktiv: bool = False        # Periode umfasst das heutige Datum


class MqttAssign(BaseModel):
    """Zuordnung eines erkannten Topics zu einem System."""
    system_id: str
    topic: str = Field(..., max_length=200, pattern=r"^[^#+\s]+$")


class MqttPath(BaseModel):
    """Fester JSON-Pfad zum Zählerstand, z. B. "MT631.Total_in"."""
    system_id: str
    path: Optional[str] = Field(None, max_length=200)


class MqttDevice(BaseModel):
    """Gerätename aus der Discovery-Liste, zum Ignorieren/Wieder-Anzeigen."""
    device: str = Field(..., max_length=200)


# ---------- Authentifizierung ----------
class UserRead(BaseModel):
    id: str
    username: str
    display_name: str
    role: str = "viewer"
    is_admin: bool = False
    aktiv: bool = True
    source: str = "lokal"        # "lokal" | "homeassistant"


class UserUpdate(BaseModel):
    role: Optional[str] = Field(None, pattern="^(guest|viewer|writer|admin)$")
    aktiv: Optional[bool] = None


class AuthStatus(BaseModel):
    mode: str                    # "lokal" | "homeassistant"
    authenticated: bool
    setup_required: bool
    # True, wenn die Ersteinrichtung nur deshalb nötig ist, weil bereits Konten
    # existieren, aber keines lokal anmeldbar ist (z. B. nach dem Einspielen
    # einer HA-Sicherung). Die Oberfläche erklärt den Fall dann gesondert.
    recovery: bool = False
    crypto_available: bool
    user: Optional[UserRead] = None
    permissions: Optional[dict[str, Any]] = None
    roles: list[dict[str, Any]] = []


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=120)
    password: str = Field(..., min_length=1, max_length=256)


class SetupRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=120,
                          pattern=r"^[A-Za-z0-9._@-]+$")
    display_name: Optional[str] = Field(None, max_length=120)
    # Zwölf Zeichen Untergrenze statt der oft zitierten acht: Länge trägt bei
    # Passwörtern mehr zur Widerstandsfähigkeit bei als erzwungene Sonderzeichen.
    password: str = Field(..., min_length=12, max_length=256)


class SqlQueryRequest(BaseModel):
    """Lesende Datenbankabfrage. Die Prüfung erfolgt serverseitig; die
    Längengrenze fängt nur offensichtlichen Unfug früh ab."""
    sql: str = Field(..., min_length=1, max_length=4000)


class BulkDeleteRequest(BaseModel):
    """Sammellöschung. Die Obergrenze verhindert, dass ein versehentlich
    erzeugter Aufruf den gesamten Bestand in einem Zug entfernt."""
    ids: list[str] = Field(..., min_length=1, max_length=1000)


# ---------- Dashboard ----------
# Die zulässigen Kacheltypen stehen im Schema, nicht nur in der Oberfläche:
# ein unbekannter Typ würde beim Zeichnen ins Leere laufen.
WIDGET_TYPES = ("latest_reading", "line_chart", "pie_chart", "cost_summary",
                "trend", "cost_forecast")

# Zeitraum je Kachel. "all" wertet den gesamten Bestand aus, "custom" einen
# frei gewählten Zeitraum (range_from/range_to).
TIMEFRAMES = ("7d", "30d", "90d", "ytd", "12m", "all", "custom")

# Rastergrenzen. Vier Spalten sind die Vorgabe der Oberfläche; die Höhe ist auf
# vier Einheiten begrenzt, damit eine einzelne Kachel nicht die ganze Seite
# einnimmt und die übrigen unerreichbar macht.
GRID_COLS = 4
MAX_TILES = 24


class DashboardTile(BaseModel):
    id: str = Field(..., min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    type: str = Field(
        ...,
        pattern="^(latest_reading|line_chart|pie_chart|cost_summary|trend|cost_forecast)$")
    x: int = Field(0, ge=0, le=GRID_COLS - 1)
    y: int = Field(0, ge=0, le=200)
    w: int = Field(1, ge=1, le=GRID_COLS)
    h: int = Field(1, ge=1, le=4)
    system_id: Optional[str] = Field(None, max_length=64)
    # Mehrere Systeme in einem Diagramm. `system_id` bleibt für die einfache
    # Zuordnung bestehen und wird als erstes Element behandelt, damit ältere
    # Layouts unverändert weiterlaufen.
    system_ids: list[str] = Field(default_factory=list, max_length=6)
    timeframe: str = Field("12m", pattern="^(7d|30d|90d|ytd|12m|all|custom)$")
    title: Optional[str] = Field(None, max_length=80)
    # Nur bei timeframe == "custom" ausgewertet.
    range_from: Optional[date] = None
    range_to: Optional[date] = None

    @model_validator(mode="after")
    def _fit_grid(self):
        # Kachel darf nicht über den rechten Rand hinausragen – sonst wäre sie
        # im Raster nicht darstellbar und rutschte in der Anzeige weg.
        if self.x + self.w > GRID_COLS:
            raise ValueError(f"Kachel {self.id} ragt über {GRID_COLS} Spalten hinaus")
        if self.timeframe == "custom":
            if not self.range_from or not self.range_to:
                raise ValueError(f"Kachel {self.id}: benutzerdefinierter Zeitraum braucht Start und Ende")
            if self.range_from > self.range_to:
                raise ValueError(f"Kachel {self.id}: Start liegt nach dem Ende")
        return self


class DashboardLayout(BaseModel):
    tiles: list[DashboardTile] = Field(..., max_length=MAX_TILES)
