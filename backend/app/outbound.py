"""Ausgehende Internet-Verbindungen – zentrales Gate und harter Kill-Switch.

Aufbau in drei Schichten. Jede allein wäre umgehbar, zusammen sind sie es nicht:

1. **Anwendungsschicht** – `fetch_json()` ist der einzige vorgesehene Weg nach
   draußen. Prüft Offline-Modus, Anbieter-Allowlist und Schema.
2. **Netzwerkschicht** – `install_socket_guard()` hängt sich in
   `socket.getaddrinfo` ein und lässt im Offline-Modus keine Auflösung zu
   öffentlichen IP-Adressen mehr zu. Damit greift der Kill-Switch auch für
   Code, der das Gate umgeht – heute wie in künftigen Versionen.
3. **Auslieferung** – siehe README: das Frontend lädt Vue, Chart.js und
   tesseract.js per CDN. Das ist ein Browser-Request und liegt außerhalb
   dieses Moduls; ohne Vendoring bleibt Datensouveränität unvollständig.

**Nicht betroffen sind lokale Ziele.** `http://supervisor` (Home-Assistant-API)
und alles in privaten Netzen bleiben immer erreichbar – sonst würden
Benachrichtigungen und Entity-Abfragen mit dem Kill-Switch mitsterben. Der
Schalter trennt Internet, nicht das eigene Netz.

**Default ist offline.** Wer externe Daten will, schaltet sie bewusst frei.
"""
import ipaddress
import json
import logging
import socket
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

log = logging.getLogger("zaehlwerk.outbound")

# --------------------------------------------------------------------------
# Anbieter-Allowlist
# --------------------------------------------------------------------------
# Bewusst fest im Code statt konfigurierbar: eine vom Nutzer eintragbare URL
# wäre eine SSRF-Lücke hinter dem Ingress-Proxy. Neue Quelle = neues Release.
# Beide Anbieter arbeiten ohne API-Schlüssel -> es liegen keine Secrets im Repo.
PROVIDERS: dict[str, dict] = {
    "weather": {
        "label": "Open-Meteo (Wetter, DWD-basiert)",
        "host": "api.open-meteo.com",
        "base": "https://api.open-meteo.com/v1/forecast",
        "ttl": 1800,          # 30 min
        "privacy": "Kein Schlüssel, keine Registrierung. Übertragen werden Koordinaten.",
    },
    "tariff": {
        "label": "aWATTar (Day-Ahead-Börsenpreise)",
        "host": "api.awattar.de",
        "base": "https://api.awattar.de/v1/marketdata",
        "ttl": 3600,          # 1 h
        "privacy": "Kein Schlüssel, keine Registrierung. Übertragen wird nur der Zeitraum.",
    },
    "tariff_at": {
        "label": "aWATTar Österreich",
        "host": "api.awattar.at",
        "base": "https://api.awattar.at/v1/marketdata",
        "ttl": 3600,
        "privacy": "Kein Schlüssel, keine Registrierung.",
    },
    # Versionsprüfung für den dezentralen Selbst-Update-Weg. Liest ausschließlich
    # die Versionsdatei des öffentlichen Repos (contents-API, Base64-JSON).
    "github_version": {
        "label": "GitHub (Versionsprüfung)",
        "host": "api.github.com",
        "base": "https://api.github.com/repos/leonlange106-lang/zaehlwerk/contents/backend/app/version.py",
        "ttl": 3600,          # 1 h
        "privacy": "Kein Schlüssel. Übertragen wird nur die Abfrage der Versionsdatei.",
    },
}

ALLOWED_HOSTS = {p["host"] for p in PROVIDERS.values()}

USER_AGENT = "Zaehlwerk/2.12 (self-hosted; +https://github.com/leonlange106-lang/energy-tracker)"


class OutboundBlocked(Exception):
    """Ausgehende Verbindung wurde bewusst verhindert."""


# --------------------------------------------------------------------------
# Zustand
# --------------------------------------------------------------------------
# Modulweite Flagge statt DB-Abfrage pro Aufruf: getaddrinfo läuft potenziell
# sehr häufig, ein Datenbankzugriff pro Namensauflösung wäre nicht vertretbar.
# Aktualisiert wird sie beim Start und bei jedem Schreiben der Einstellungen.
_offline: bool = True
_lock = threading.Lock()


def set_offline(value: bool) -> None:
    global _offline
    with _lock:
        _offline = bool(value)
    log.info("Kill-Switch: %s", "Offline-Modus AKTIV" if _offline else "Internet freigegeben")


def is_offline() -> bool:
    return _offline


# --------------------------------------------------------------------------
# Schicht 2: Socket-Sperre
# --------------------------------------------------------------------------
_original_getaddrinfo = socket.getaddrinfo
_guard_installed = False


def _is_local_target(host: str, infos) -> bool:
    """Lokal = Loopback, privates Netz, link-local oder ein nicht auflösbarer
    Docker-interner Name. Diese Ziele bleiben immer erlaubt."""
    if host in {"supervisor", "localhost", "hassio", "homeassistant", "observer"}:
        return True
    for info in infos:
        addr = info[4][0]
        try:
            ip = ipaddress.ip_address(addr)
        except ValueError:
            continue
        if not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved):
            return False
    return True


def _guarded_getaddrinfo(host, port, *args, **kwargs):
    infos = _original_getaddrinfo(host, port, *args, **kwargs)
    if not _offline:
        return infos
    if _is_local_target(str(host), infos):
        return infos
    log.warning("Kill-Switch hat ausgehende Verbindung zu %s blockiert", host)
    raise OSError(
        f"Zählwerk-Kill-Switch: Verbindung zu '{host}' blockiert (Offline-Modus aktiv)"
    )


def install_socket_guard() -> None:
    """Einmalig beim Start aufrufen. Idempotent."""
    global _guard_installed
    if _guard_installed:
        return
    socket.getaddrinfo = _guarded_getaddrinfo
    _guard_installed = True
    log.info("Socket-Guard installiert")


# --------------------------------------------------------------------------
# Schicht 1: Anwendungs-Gate mit Cache
# --------------------------------------------------------------------------
_cache: dict[str, tuple[float, dict]] = {}


def cached(key: str, ttl: int):
    entry = _cache.get(key)
    if not entry:
        return None, None
    ts, data = entry
    age = time.time() - ts
    return data, age


def fetch_json(provider: str, params: dict | None = None, *, timeout: int = 10) -> dict:
    """Einziger vorgesehener Weg nach draußen.

    Fehlertolerant: Ist der Abruf nicht möglich – Offline-Modus, kein Netz,
    Anbieter gestört – wird ein noch vorhandener Cache-Eintrag zurückgegeben,
    auch ein abgelaufener. Erst wenn gar nichts da ist, fliegt eine Ausnahme.
    Damit bleibt die Oberfläche bedienbar, statt auf Fehlern zu stehen.
    """
    cfg = PROVIDERS.get(provider)
    if not cfg:
        raise OutboundBlocked(f"Unbekannter Anbieter '{provider}'")

    url = cfg["base"]
    if params:
        url = f"{url}?{urllib.parse.urlencode(params, doseq=True)}"
    key = f"{provider}:{url}"

    data, age = cached(key, cfg["ttl"])
    if data is not None and age is not None and age < cfg["ttl"]:
        return {**data, "_cached": True, "_age_seconds": int(age)}

    if _offline:
        if data is not None:
            return {**data, "_cached": True, "_stale": True, "_age_seconds": int(age)}
        raise OutboundBlocked(
            "Offline-Modus aktiv – externe Abfragen sind gesperrt und es liegen "
            "keine zwischengespeicherten Daten vor."
        )

    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https":
        raise OutboundBlocked("Nur HTTPS zulässig")
    if parsed.hostname not in ALLOWED_HOSTS:
        raise OutboundBlocked(f"Host '{parsed.hostname}' steht nicht auf der Allowlist")

    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    })
    try:
        # Kein Redirect-Folgen über den Standard hinaus: ein 302 auf einen
        # fremden Host würde die Allowlist aushebeln. Der Socket-Guard fängt
        # das zusätzlich ab, aber die Prüfung gehört auch hierher.
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            final_host = urllib.parse.urlparse(resp.geturl()).hostname
            if final_host not in ALLOWED_HOSTS:
                raise OutboundBlocked(f"Weiterleitung auf '{final_host}' abgewiesen")
            payload = json.loads(resp.read().decode("utf-8"))
    except OutboundBlocked:
        raise
    except (urllib.error.URLError, OSError, ValueError) as exc:
        if data is not None:
            log.warning("Abruf %s fehlgeschlagen (%s) – liefere Cache", provider, exc)
            return {**data, "_cached": True, "_stale": True, "_age_seconds": int(age or 0)}
        raise OutboundBlocked(f"Abruf fehlgeschlagen: {exc}") from exc

    _cache[key] = (time.time(), payload)
    return {**payload, "_cached": False, "_age_seconds": 0}


def cache_state() -> list[dict]:
    """Für die Diagnose: was liegt zwischengespeichert, wie alt ist es."""
    now = time.time()
    out = []
    for key, (ts, _) in _cache.items():
        provider = key.split(":", 1)[0]
        ttl = PROVIDERS.get(provider, {}).get("ttl", 0)
        age = int(now - ts)
        out.append({"provider": provider, "age_seconds": age, "stale": age > ttl})
    return out


def clear_cache() -> int:
    n = len(_cache)
    _cache.clear()
    return n
