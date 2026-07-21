"""Externe Daten (Wetter, dynamische Stromtarife).

Jeder Endpunkt hier geht ausschließlich über `outbound.fetch_json()`. Direkte
`urllib`- oder `httpx`-Aufrufe sind in diesem Modul unzulässig – sie würden das
Anwendungs-Gate umgehen (der Socket-Guard griffe zwar trotzdem, aber dann als
harter Verbindungsfehler statt als saubere 503-Antwort).
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session

from .. import outbound
from ..database import get_session
from ..schemas import ExternalStatus, TariffRead, WeatherRead

router = APIRouter(prefix="/api/external", tags=["external"])


def _guard():
    """Übersetzt die Sperre in eine saubere HTTP-Antwort statt eines 500ers."""
    if outbound.is_offline():
        raise HTTPException(
            503,
            "Offline-Modus aktiv. Externe Abfragen sind gesperrt "
            "(Einstellungen → System → Internetzugriff).",
        )


@router.get("/status", response_model=ExternalStatus)
def status():
    """Immer erreichbar, auch offline – die Oberfläche muss den Zustand anzeigen
    können, ohne selbst nach draußen zu greifen."""
    return ExternalStatus(
        offline_mode=outbound.is_offline(),
        socket_guard_active=outbound._guard_installed,
        providers=[
            {"key": k, "label": v["label"], "host": v["host"],
             "ttl_seconds": v["ttl"], "privacy": v["privacy"]}
            for k, v in outbound.PROVIDERS.items()
        ],
        cache=outbound.cache_state(),
    )


@router.post("/cache/clear")
def clear_cache():
    return {"cleared": outbound.clear_cache()}


@router.get("/weather", response_model=WeatherRead)
def weather(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    days: int = Query(3, ge=1, le=7),
    session: Session = Depends(get_session),
):
    """Temperaturprognose. Fachlicher Zweck: Heizverbrauch gegen Außentemperatur
    einordnen – ein Gasverbrauch ist ohne Gradtagszahl kaum vergleichbar."""
    _guard()
    try:
        data = outbound.fetch_json("weather", {
            "latitude": round(lat, 3),      # Rundung: 3 Nachkommastellen ~110 m,
            "longitude": round(lon, 3),     # genauer muss der Anbieter es nicht wissen
            "daily": "temperature_2m_max,temperature_2m_min",
            "timezone": "Europe/Berlin",
            "forecast_days": days,
        })
    except outbound.OutboundBlocked as exc:
        raise HTTPException(503, str(exc))

    daily = data.get("daily") or {}
    return WeatherRead(
        latitude=data.get("latitude"), longitude=data.get("longitude"),
        dates=daily.get("time") or [],
        temp_max=daily.get("temperature_2m_max") or [],
        temp_min=daily.get("temperature_2m_min") or [],
        cached=bool(data.get("_cached")),
        stale=bool(data.get("_stale")),
        age_seconds=int(data.get("_age_seconds") or 0),
    )


@router.get("/tariff", response_model=TariffRead)
def tariff(
    market: str = Query("de", pattern="^(de|at)$"),
    hours: int = Query(24, ge=1, le=48),
    session: Session = Depends(get_session),
):
    """Day-Ahead-Börsenpreise. Nicht dein Endkundentarif – Netzentgelte,
    Abgaben und Marge des Versorgers kommen obendrauf."""
    _guard()
    provider = "tariff" if market == "de" else "tariff_at"
    start = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    try:
        data = outbound.fetch_json(provider, {
            "start": int(start.timestamp() * 1000),
            "end": int((start + timedelta(hours=hours)).timestamp() * 1000),
        })
    except outbound.OutboundBlocked as exc:
        raise HTTPException(503, str(exc))

    slots = []
    for row in (data.get("data") or []):
        # Anbieter liefert EUR/MWh -> ct/kWh ist die Einheit, in der Zählwerk rechnet
        slots.append({
            "start": datetime.fromtimestamp(row["start_timestamp"] / 1000, timezone.utc).isoformat(),
            "end": datetime.fromtimestamp(row["end_timestamp"] / 1000, timezone.utc).isoformat(),
            "ct_per_kwh": round(row["marketprice"] / 10.0, 3),
        })
    prices = [s["ct_per_kwh"] for s in slots]
    return TariffRead(
        market=market, slots=slots,
        min_ct=min(prices) if prices else None,
        max_ct=max(prices) if prices else None,
        avg_ct=round(sum(prices) / len(prices), 3) if prices else None,
        cached=bool(data.get("_cached")),
        stale=bool(data.get("_stale")),
        age_seconds=int(data.get("_age_seconds") or 0),
    )
