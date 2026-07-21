"""Persönliches Dashboard: Layout je Konto und die Daten für die Kacheln.

Das Layout ist eine Liste von Kacheln mit Rasterkoordinaten::

    [{"id": "w1", "type": "line_chart", "x": 0, "y": 0, "w": 2, "h": 2,
      "system_id": "…", "title": "Strom"}]

Es wird als JSON-Zeichenkette in `users.dashboard_layout` abgelegt. Die
Prüfung erfolgt beim Schreiben, nicht beim Lesen: eine kaputte Zeichenkette in
der Datenbank würde sonst bei jedem Seitenaufruf einen Fehler auslösen, statt
einmal beim Speichern abgewiesen zu werden.

`GET /api/dashboard/data` liefert alles, was die Kacheln brauchen, in einem
Aufruf. Sonst stellte ein Dashboard mit acht Kacheln acht bis zwölf Anfragen –
bei jedem Öffnen der Startseite.
"""
import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from .. import logic
from ..auth import current_user
from ..database import get_session
from ..models import System, User
from ..schemas import DashboardLayout
from .readings import _enriched, _sigma, system_prognosis

log = logging.getLogger("zaehlwerk.dashboard")
router = APIRouter(tags=["dashboard"])


# --------------------------------------------------------------------------
# Layout
# --------------------------------------------------------------------------
def _default_layout(session: Session) -> list[dict]:
    """Startbelegung für Konten ohne eigenes Layout.

    Eine leere Startseite wirkt wie ein Fehler. Stattdessen bekommt jedes
    System eine Kachel mit dem letzten Stand, darüber eine Verteilung.
    """
    systems = session.exec(
        select(System).where(System.aktiv == True).order_by(System.name)  # noqa: E712
    ).all()[:6]

    tiles: list[dict] = []
    for i, s in enumerate(systems):
        tiles.append({"id": f"w_latest_{i}", "type": "latest_reading",
                      "x": i % 4, "y": 0, "w": 1, "h": 1, "system_id": s.id})
    if systems:
        tiles.append({"id": "w_line_0", "type": "line_chart", "x": 0, "y": 1,
                      "w": 2, "h": 2, "system_id": systems[0].id})
        tiles.append({"id": "w_cost_0", "type": "cost_summary", "x": 2, "y": 1,
                      "w": 1, "h": 1, "system_id": None})
        tiles.append({"id": "w_pie_0", "type": "pie_chart", "x": 3, "y": 1,
                      "w": 1, "h": 2, "system_id": None})
    return tiles


@router.get("/api/user/dashboard")
def get_dashboard(user: User = Depends(current_user),
                  session: Session = Depends(get_session)):
    if not user.dashboard_layout:
        return {"tiles": _default_layout(session), "is_default": True}
    try:
        tiles = json.loads(user.dashboard_layout)
        if not isinstance(tiles, list):
            raise ValueError("kein Feld")
    except (ValueError, TypeError) as exc:
        # Nicht scheitern: der Nutzer käme sonst nicht mehr auf seine Startseite
        # und hätte auch keine Möglichkeit, das Layout zurückzusetzen.
        log.warning("Layout von %s nicht lesbar (%s) – Vorgabe wird verwendet",
                    user.username, exc)
        return {"tiles": _default_layout(session), "is_default": True,
                "recovered": True}
    return {"tiles": tiles, "is_default": False}


@router.put("/api/user/dashboard")
def put_dashboard(payload: DashboardLayout,
                  user: User = Depends(current_user),
                  session: Session = Depends(get_session)):
    """Layout speichern. Die Feldprüfung steckt im Schema, hier folgt der
    Abgleich gegen den Datenbestand."""
    known = {s.id for s in session.exec(select(System)).all()}
    seen: set[str] = set()
    cleaned = []
    for tile in payload.tiles:
        if tile.id in seen:
            raise HTTPException(422, f"Doppelte Kachel-Kennung: {tile.id}")
        seen.add(tile.id)
        # Verweist eine Kachel auf ein gelöschtes System, wird der Verweis
        # entfernt statt die Kachel zu verwerfen – der Nutzer sieht dann eine
        # Kachel ohne Zuordnung und kann sie neu belegen.
        system_id = tile.system_id if tile.system_id in known else None
        # mode="json": range_from/range_to sind date-Objekte, die json.dumps
        # weiter unten ohne diese Umwandlung nicht serialisieren könnte.
        cleaned.append({**tile.model_dump(mode="json"), "system_id": system_id})

    user.dashboard_layout = json.dumps(cleaned, ensure_ascii=False)
    session.add(user)
    session.commit()
    return {"tiles": cleaned, "saved": len(cleaned)}


@router.delete("/api/user/dashboard", status_code=204)
def reset_dashboard(user: User = Depends(current_user),
                    session: Session = Depends(get_session)):
    """Auf die Vorgabe zurücksetzen."""
    user.dashboard_layout = None
    session.add(user)
    session.commit()


# --------------------------------------------------------------------------
# Daten für die Kacheln
# --------------------------------------------------------------------------
@router.get("/api/dashboard/data")
def dashboard_data(months: int = 24, session: Session = Depends(get_session)):
    """Kennzahlen und Verläufe aller aktiven Systeme in einem Aufruf."""
    from datetime import date, timedelta

    since: Optional[date] = None
    if months and months > 0:
        since = date.today() - timedelta(days=int(months * 30.44))

    sigma = _sigma(session)
    systems = session.exec(
        select(System).where(System.aktiv == True).order_by(System.name)  # noqa: E712
    ).all()

    out = []
    for s in systems:
        # Genau EINE Anreicherung je System über die volle Historie. Kachel
        # (auf `months` gefenstert) und Prognose (5-Jahres-Rolling-Average)
        # werden beide daraus abgeleitet – früher lief _enriched zweimal je
        # System (einmal gefenstert, einmal voll für die Prognose).
        enriched_full = _enriched(session, s)
        windowed = ([e for e in enriched_full if e["datum"].date() >= since]
                    if since else enriched_full)
        stats = logic.compute_stats(windowed, sigma)
        stats.update(logic.tariff_summary(windowed))
        points = [e for e in windowed if e.get("consumption_per_day") is not None]
        out.append({
            "id": s.id, "name": s.name, "typ": s.typ,
            "einheit": s.einheit, "farbe": s.farbe,
            "latest": enriched_full[-1]["value"] if enriched_full else None,
            "latest_datum": enriched_full[-1]["datum"].isoformat() if enriched_full else None,
            "total_consumption": stats.get("total_consumption"),
            "total_cost": stats.get("total_cost"),
            "total_cost_tariff": stats.get("total_cost_tariff"),
            "avg_per_day": stats.get("avg_per_day"),
            # Nur was ein Kachel-Diagramm zeichnen kann – der volle Datensatz
            # wäre bei 24 Jahren Historie ein Vielfaches der nötigen Menge.
            "series": [{"d": e["datum"].isoformat(),
                        "v": round(e["consumption_per_day"], 4)}
                       for e in points[-120:]],
            # Prognose aus derselben voll-historischen Anreicherung (das
            # Rolling-Fenster reicht weiter zurück als die Kachel-Monate).
            "prognosis": system_prognosis(session, s, enriched_full),
        })
    # Letzte Erfassungen über alle Systeme. Für die mobile Startseite und als
    # Grundlage der Trend-Kachel; bewusst hier und nicht als eigener Aufruf,
    # damit die Startseite mit einer einzigen Anfrage auskommt.
    from ..models import Reading
    recent_rows = session.exec(
        select(Reading).order_by(Reading.datum.desc(), Reading.id.desc()).limit(10)
    ).all()
    names = {s.id: s.name for s in systems}
    colors = {s.id: s.farbe for s in systems}
    units = {s.id: s.einheit for s in systems}
    recent = [{
        "id": r.id, "system_id": r.system_id,
        "system": names.get(r.system_id, "—"),
        "farbe": colors.get(r.system_id),
        "einheit": units.get(r.system_id, ""),
        "datum": r.datum.isoformat() if r.datum else None,
        "value": r.value,
        "source": getattr(r, "source", None) or "manual",
    } for r in recent_rows if r.system_id in names]

    return {"systems": out, "months": months, "recent": recent[:6]}
