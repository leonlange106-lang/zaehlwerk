"""Ablesungen, Statistik, Chart-Daten, Export, PDF – alles aus SQLite."""
import csv
import io
import json
import zipfile
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlmodel import Session, func, select

from .. import exporter, logic, report
from ..version import APP_VERSION
from ..due import system_due_entries
from ..database import get_session
from ..models import Meter, Reading, System, Tariff
from ..schemas import (READING_SOURCES_ALL, BulkDeleteRequest, ChartData,
                       ReadingCreate, ReadingRead, StatsRead)
from .settings import read_settings

router = APIRouter(tags=["readings"])


# ---------- Helfer ----------
def _require_system(system_id: str, session: Session) -> System:
    system = session.get(System, system_id)
    if not system:
        raise HTTPException(404, "System nicht gefunden")
    return system


def _reading_dict(r: Reading) -> dict:
    return {
        "id": r.id, "system_id": r.system_id, "datum": r.datum,
        "value": r.value, "cost": r.cost,
        "meter_replaced": r.meter_replaced,
        "meter_start": getattr(r, "meter_start", None),
        "note": r.note,
        "source": getattr(r, "source", None) or "manual",
    }


def _parse_sources(value: Optional[str]) -> Optional[set[str]]:
    """Komma-getrennte Herkunftsliste auswerten. Leer bedeutet: alle."""
    if not value:
        return None
    wanted = {s.strip().lower() for s in value.split(",") if s.strip()}
    valid = wanted & set(READING_SOURCES_ALL)
    return valid or None


def _query_readings(session: Session, system_id: str,
                    from_: Optional[date] = None, to: Optional[date] = None,
                    limit: Optional[int] = None,
                    sources: Optional[set[str]] = None) -> list[dict]:
    stmt = select(Reading).where(Reading.system_id == system_id)
    if sources:
        # Bestandsdaten vor 3.7.0 tragen 'manual'; NULL kann nach Migration 7
        # nicht mehr vorkommen, die Prüfung bleibt dennoch als Rückfallebene.
        stmt = stmt.where(Reading.source.in_(sources))
    if from_:
        stmt = stmt.where(Reading.datum >= datetime(from_.year, from_.month, from_.day))
    if to:
        stmt = stmt.where(Reading.datum <= datetime(to.year, to.month, to.day, 23, 59, 59))
    # meter_replaced sortiert bei Datumsgleichheit ans Ende:
    # erst Endstand ALTER Zähler (normale Ablesung), dann Startstand NEUER Zähler (Tausch)
    rows = session.exec(stmt.order_by(Reading.datum, Reading.meter_replaced)).all()
    out = [_reading_dict(r) for r in rows]
    if limit:
        out = out[-limit:]
    return out


def _price(system: System) -> Optional[float]:
    """Durchschnittspreis €/Einheit aus den System-Zusatzfeldern (Fallback-Kosten)."""
    try:
        p = float((system.zusatzfelder or {}).get("preis") or 0)
        return p if p > 0 else None
    except (TypeError, ValueError):
        return None


def _sigma(session: Session) -> float:
    """Ausreisser-Schwelle aus den Anwendungseinstellungen (Standard 2 sigma)."""
    return float(read_settings(session).get("outlier_sigma", logic.DEFAULT_SIGMA))


def _tariffs(session: Session, system_id: str) -> list[dict]:
    """Tarifperioden als schlichte Dicts – logic.py soll keine ORM-Objekte kennen."""
    rows = session.exec(
        select(Tariff).where(Tariff.system_id == system_id).order_by(Tariff.gueltig_ab)
    ).all()
    return [{"name": t.name, "anbieter": t.anbieter,
             "gueltig_ab": t.gueltig_ab, "gueltig_bis": t.gueltig_bis,
             "arbeitspreis": t.arbeitspreis, "grundpreis": t.grundpreis} for t in rows]


def _enriched(session: Session, system: System,
              from_: Optional[date] = None, to: Optional[date] = None,
              sources: Optional[set[str]] = None) -> list[dict]:
    raw = _query_readings(session, system.id, from_, to, sources=sources)
    enriched = logic.mark_outliers(
        logic.compute_intervals(raw, price=_price(system)), _sigma(session)
    )
    # Tarifkosten treten NEBEN die erfassten Kosten, nicht an deren Stelle.
    enriched = logic.apply_tariffs(enriched, _tariffs(session, system.id))
    # Gas: m³-Werte zusätzlich in kWh ausweisen (TICKET-2.2).
    return logic.annotate_kwh(enriched, logic.gas_factor(system.typ, system.zusatzfelder))


def _latest(session: Session, system_id: str) -> Optional[Reading]:
    return session.exec(
        select(Reading).where(Reading.system_id == system_id).order_by(Reading.datum.desc())
    ).first()


def _abschlag_cfg(system: System) -> tuple[Optional[float], Optional[int]]:
    """Monatlicher Abschlag und Startmonat des Abrechnungsjahres aus den
    System-Zusatzfeldern. Ungültige/leere Angaben ergeben None (Kalenderjahr,
    keine Abschlagsprüfung)."""
    zf = system.zusatzfelder or {}
    def _f(v):
        try:
            return float(v) if v not in (None, "") else None
        except (TypeError, ValueError):
            return None
    def _i(v):
        try:
            n = int(v)
            return n if 1 <= n <= 12 else None
        except (TypeError, ValueError):
            return None
    return _f(zf.get("abschlag")), _i(zf.get("abrechnungsmonat"))


def system_prognosis(session: Session, system: System,
                     enriched: Optional[list[dict]] = None) -> Optional[dict]:
    """Prognose fürs nächste Abrechnungsjahr (5-Jahres-Rolling-Average). Nutzt
    die volle Historie – rolling_prognosis begrenzt selbst auf das Fenster."""
    if enriched is None:
        enriched = _enriched(session, system)
    abschlag, abr_month = _abschlag_cfg(system)
    return logic.rolling_prognosis(
        enriched, _tariffs(session, system.id),
        abschlag=abschlag, billing_start_month=abr_month,
    )


# ---------- Ablesungen ----------
@router.get("/api/systems/{system_id}/readings", response_model=list[ReadingRead])
def list_readings(
    system_id: str,
    from_: Optional[date] = Query(None, alias="from"),
    to: Optional[date] = Query(None),
    limit: Optional[int] = Query(None, ge=1, le=100000),
    session: Session = Depends(get_session),
):
    system = _require_system(system_id, session)
    enriched = _enriched(session, system, from_, to)
    if limit:
        enriched = enriched[-limit:]
    return enriched


@router.post("/api/systems/{system_id}/readings", response_model=ReadingRead, status_code=201)
def create_reading(system_id: str, payload: ReadingCreate, session: Session = Depends(get_session)):
    _require_system(system_id, session)
    if not payload.meter_replaced:
        latest = _latest(session, system_id)
        if latest and latest.value is not None and payload.value < latest.value:
            raise HTTPException(
                422,
                f"Wert {payload.value} < letzter Wert {latest.value}. "
                f"Bei Zählertausch 'meter_replaced' setzen.",
            )
    r = Reading(
        system_id=system_id,
        datum=datetime(payload.datum.year, payload.datum.month, payload.datum.day),
        value=payload.value,
        # Herkunft aus der Anfrage, aber nur aus dem zugelassenen Bereich:
        # 'manual' für Tastatureingabe, 'ha_api' für Übernahme aus einer
        # Home-Assistant-Entity. 'mqtt' setzt allein der Listener.
        source=payload.source,
        cost=payload.cost,
        meter_replaced=payload.meter_replaced,
        # Startstand nur bei Tausch übernehmen (Schema erzwingt das bereits).
        meter_start=payload.meter_start if payload.meter_replaced else None,
        note=payload.note,
    )
    session.add(r)
    session.commit()
    session.refresh(r)
    return ReadingRead(**_reading_dict(r))


@router.put("/api/readings/{reading_id}", response_model=ReadingRead)
def update_reading(reading_id: str, payload: ReadingCreate, session: Session = Depends(get_session)):
    r = session.get(Reading, reading_id)
    if not r:
        raise HTTPException(404, "Ablesung nicht gefunden")
    r.datum = datetime(payload.datum.year, payload.datum.month, payload.datum.day)
    r.value = payload.value
    r.cost = payload.cost
    r.meter_replaced = payload.meter_replaced
    r.meter_start = payload.meter_start if payload.meter_replaced else None
    r.note = payload.note
    session.add(r)
    session.commit()
    session.refresh(r)
    return ReadingRead(**_reading_dict(r))


@router.delete("/api/readings/{reading_id}", status_code=204)
def delete_reading(reading_id: str, session: Session = Depends(get_session)):
    r = session.get(Reading, reading_id)
    if r:
        session.delete(r)
        session.commit()


# ---------- Auswertung ----------
@router.get("/api/systems/{system_id}/stats", response_model=StatsRead)
def get_stats(
    system_id: str,
    from_: Optional[date] = Query(None, alias="from"),
    to: Optional[date] = Query(None),
    session: Session = Depends(get_session),
):
    system = _require_system(system_id, session)
    enriched = _enriched(session, system, from_, to)
    stats = logic.compute_stats(enriched, _sigma(session))
    stats.update(logic.tariff_summary(enriched))
    # Gas: Gesamt-/Tagesverbrauch zusätzlich in kWh (TICKET-2.2).
    factor = logic.gas_factor(system.typ, system.zusatzfelder)
    if factor:
        stats["kwh_factor"] = round(factor, 4)
        stats["total_consumption_kwh"] = round(stats["total_consumption"] * factor, 2)
        if stats.get("avg_per_day") is not None:
            stats["avg_per_day_kwh"] = round(stats["avg_per_day"] * factor, 3)
    return stats


def _chart_arrays(points: list[dict]) -> dict:
    """Baut die parallelen Diagramm-Arrays aus einer (ggf. bereits verdichteten)
    Punktliste. Eine Quelle für beide Chart-Endpunkte, damit sie nicht
    auseinanderlaufen."""
    return {
        "labels": [e["datum"].date().isoformat() for e in points],
        "values": [e["value"] for e in points],
        "consumption": [e.get("consumption") for e in points],
        "consumption_per_day": [e.get("consumption_per_day") for e in points],
        "outliers": [bool(e.get("is_outlier")) for e in points],
        "meter_replaced": [bool(e.get("meter_replaced")) for e in points],
    }


@router.get("/api/systems/{system_id}/chart-data", response_model=ChartData)
def get_chart_data(
    system_id: str,
    from_: Optional[date] = Query(None, alias="from"),
    to: Optional[date] = Query(None),
    session: Session = Depends(get_session),
):
    system = _require_system(system_id, session)
    enriched = _enriched(session, system, from_, to)
    # Lange Historien werden fürs Diagramm verdichtet – sonst überträgt und
    # zeichnet die Oberfläche tausende Punkte, die kein Bildschirm auflöst.
    points = logic.downsample_enriched(enriched)
    arrays = _chart_arrays(points)
    factor = logic.gas_factor(system.typ, system.zusatzfelder)
    cpd_kwh = ([round(v * factor, 3) if v is not None else None
                for v in arrays["consumption_per_day"]] if factor else [])
    return ChartData(
        system_id=system_id, name=system.name, unit=system.einheit,
        color=system.farbe, **arrays,
        consumption_per_day_kwh=cpd_kwh, kwh_factor=round(factor, 4) if factor else None,
    )


@router.get("/api/systems/{system_id}/dashboard")
def get_dashboard(
    system_id: str,
    from_: Optional[date] = Query(None, alias="from"),
    to: Optional[date] = Query(None),
    session: Session = Depends(get_session),
):
    """Kombiniert readings + stats + chart-data in EINEM Request/EINER Berechnung."""
    system = _require_system(system_id, session)
    enriched = _enriched(session, system, from_, to)
    stats = logic.compute_stats(enriched, _sigma(session))
    stats.update(logic.tariff_summary(enriched))
    # Diagramm verdichtet (schnelle Anzeige), Tabelle unverändert vollständig.
    chart_points = logic.downsample_enriched(enriched)
    chart = {
        "system_id": system_id, "name": system.name, "unit": system.einheit,
        "color": system.farbe,
        "downsampled": len(chart_points) < len(enriched),
        "points_total": len(enriched),
        **_chart_arrays(chart_points),
    }
    readings = [{**e, "datum": e["datum"].isoformat()} for e in enriched]

    # Anzahlen für die Reiterbeschriftung. Bewusst nur COUNT statt der
    # vollständigen Listen: die Oberfläche braucht beim Laden lediglich die
    # Zahl, die Datensätze selbst erst beim Öffnen des jeweiligen Reiters.
    # Zwei billige Aggregatabfragen sparen zwei zusätzliche Rundläufe.
    counts = {
        "meters": session.exec(
            select(func.count()).select_from(Meter)
            .where(Meter.system_id == system_id)).one(),
        "tariffs": session.exec(
            select(func.count()).select_from(Tariff)
            .where(Tariff.system_id == system_id)).one(),
    }
    # Prognose immer aus der vollen Historie, unabhängig vom angezeigten
    # Zeitraum – ein auf drei Monate gefiltertes Dashboard soll trotzdem eine
    # tragfähige Jahresprognose zeigen.
    prog_source = enriched if (from_ is None and to is None) else _enriched(session, system)
    prognosis = system_prognosis(session, system, prog_source)
    return {"readings": readings, "stats": stats, "chart": chart,
            "counts": counts, "prognosis": prognosis}


@router.get("/api/overview")
def get_overview(session: Session = Depends(get_session)):
    """Letzter Stand + Fälligkeit je aktivem System (gemeinsame Logik in due.py)."""
    out = {}
    for e in system_due_entries(session):
        entry = {"value": e["value"], "datum": e["datum"].isoformat()}
        if "overdue_days" in e:
            entry["next_expected"] = e["next_expected"].date().isoformat()
            entry["overdue_days"] = e["overdue_days"]
        out[e["system"].id] = entry
    return out


# ---------- Export ----------
@router.get("/api/systems/{system_id}/export.csv")
def export_readings(
    system_id: str,
    from_: Optional[date] = Query(None, alias="from"),
    to: Optional[date] = Query(None),
    session: Session = Depends(get_session),
):
    """Alle Ablesungen als CSV – identisches Format wie der Import (Backup / Re-Import)."""
    system = _require_system(system_id, session)
    raw = _query_readings(session, system_id, from_, to)
    fname = f"zaehlwerk_{system.name.replace(' ', '_')}.csv"
    return Response(
        content=_readings_csv(raw), media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


def _readings_csv(raw: list[dict]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["datum", "wert", "kosten", "zaehlertausch", "notiz"])
    for r in raw:
        val, cost = r.get("value"), r.get("cost")
        w.writerow([
            r["datum"].date().isoformat(),
            ("" if val is None else (str(int(val)) if float(val).is_integer() else f"{val:.4f}".rstrip("0").rstrip("."))),
            ("" if cost is None else f"{cost:.2f}"),
            "ja" if r.get("meter_replaced") else "",
            r.get("note") or "",
        ])
    return buf.getvalue()


def _export_sections(session: Session, systems_param: Optional[str],
                     include_inactive: bool, from_: Optional[date],
                     to: Optional[date], with_meta: bool,
                     sources: Optional[set[str]] = None) -> list[dict]:
    """Systemauswahl auflösen und je System die angereicherten Daten bauen.
    Gemeinsame Grundlage von JSON- und CSV-Export – so können die beiden
    Formate nicht auseinanderlaufen."""
    stmt = select(System)
    if not include_inactive:
        stmt = stmt.where(System.aktiv == True)  # noqa: E712
    if systems_param:
        wanted = {s.strip() for s in systems_param.split(",") if s.strip()}
        if wanted:
            stmt = stmt.where(System.id.in_(wanted))

    sections = []
    for system in session.exec(stmt.order_by(System.name)).all():
        enriched = _enriched(session, system, from_, to, sources)
        stats = logic.compute_stats(enriched, _sigma(session))
        stats.update(logic.tariff_summary(enriched))
        section = {
            "system": {"id": system.id, "name": system.name, "typ": system.typ,
                       "einheit": system.einheit, "farbe": system.farbe,
                       "aktiv": system.aktiv, "zusatzfelder": system.zusatzfelder or {}},
            "enriched": enriched,
            "stats": stats,
        }
        if with_meta:
            section["meters"] = [{
                "hersteller": m.hersteller, "modell": m.modell,
                "zaehlernummer": m.zaehlernummer, "bauart": m.bauart,
                "baujahr": m.baujahr,
                "eichung_bis": m.eichung_bis.isoformat() if m.eichung_bis else None,
                "eingebaut_am": m.eingebaut_am.isoformat() if m.eingebaut_am else None,
                "ausgebaut_am": m.ausgebaut_am.isoformat() if m.ausgebaut_am else None,
            } for m in session.exec(
                select(Meter).where(Meter.system_id == system.id)).all()]
            section["tariffs"] = [{
                "name": t.name, "anbieter": t.anbieter,
                "gueltig_ab": t.gueltig_ab.isoformat(),
                "gueltig_bis": t.gueltig_bis.isoformat() if t.gueltig_bis else None,
                "arbeitspreis": t.arbeitspreis, "grundpreis": t.grundpreis,
            } for t in session.exec(
                select(Tariff).where(Tariff.system_id == system.id)
                .order_by(Tariff.gueltig_ab)).all()]
        sections.append(section)
    return sections


@router.post("/api/systems/{system_id}/readings/bulk-delete")
def bulk_delete_readings(system_id: str, payload: BulkDeleteRequest,
                         session: Session = Depends(get_session)):
    """Mehrere Ablesungen in einem Vorgang löschen.

    Bewusst ein eigener Endpunkt statt vieler Einzelaufrufe: nur so ist die
    Löschung atomar. Bräche ein Aufruf in der Mitte ab, bliebe ein halb
    bereinigter Bestand zurück – und weil sich jeder Verbrauchswert aus dem
    Abstand zur Vorablesung ergibt, wäre die Auswertung danach schlicht falsch.

    Die Kennungen werden gegen das System geprüft. Fremde oder unbekannte
    Kennungen entfallen still, statt den ganzen Vorgang scheitern zu lassen;
    die Antwort nennt die tatsächlich gelöschte Anzahl.
    """
    system = _require_system(system_id, session)
    ids = {i.strip() for i in payload.ids if i and i.strip()}
    if not ids:
        raise HTTPException(422, "Keine Kennungen übergeben")

    rows = session.exec(
        select(Reading).where(Reading.system_id == system.id, Reading.id.in_(ids))
    ).all()
    if not rows:
        raise HTTPException(404, "Keine passenden Ablesungen gefunden")

    # Ein Zählertausch markiert den Beginn eines neuen Zählwerks. Wird er
    # gelöscht, rechnet die Auswertung über die Tauschgrenze hinweg und
    # liefert einen sinnlosen Verbrauch. Die Antwort weist das aus.
    swaps = [r for r in rows if r.meter_replaced]

    for row in rows:
        session.delete(row)
    session.commit()

    return {"deleted": len(rows), "requested": len(ids),
            "meter_replacements_removed": len(swaps),
            "remaining": session.exec(
                select(func.count()).select_from(Reading)
                .where(Reading.system_id == system.id)).one()}


@router.get("/api/export/data.csv")
def export_flat_csv(
    from_: Optional[date] = Query(None, alias="from"),
    to: Optional[date] = Query(None),
    systems_param: Optional[str] = Query(None, alias="systems"),
    include_inactive: bool = Query(False),
    dialect: str = Query("de", pattern="^(de|international)$"),
    sources: Optional[str] = Query(None),
    session: Session = Depends(get_session),
):
    """Flaches CSV über alle Systeme – eine Zeile je Ablesung, mit abgeleiteten
    Größen. Für Tabellenkalkulation und Auswertungswerkzeuge, NICHT für den
    Re-Import; dafür bleibt `/api/systems/{id}/export.csv` zuständig."""
    sections = _export_sections(session, systems_param, include_inactive, from_, to,
                                False, _parse_sources(sources))
    data = exporter.build_csv(sections, dialect)
    stamp = date.today().isoformat()
    return Response(
        content=data, media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="zaehlwerk-daten_{stamp}.csv"'},
    )


@router.get("/api/export/data.json")
def export_full_json(
    from_: Optional[date] = Query(None, alias="from"),
    to: Optional[date] = Query(None),
    systems_param: Optional[str] = Query(None, alias="systems"),
    include_inactive: bool = Query(False),
    include_derived: bool = Query(True, description="Verbrauch, Kosten, Ausreißer mitgeben"),
    include_meta: bool = Query(True, description="Zähler-Metadaten und Tarife mitgeben"),
    pretty: bool = Query(True),
    sources: Optional[str] = Query(None),
    session: Session = Depends(get_session),
):
    """Vollständiger strukturierter Export."""
    from ..database import engine
    from ..migrations import schema_version

    sections = _export_sections(session, systems_param, include_inactive,
                                from_, to, include_meta, _parse_sources(sources))
    data = exporter.build_json(
        sections, app_version=APP_VERSION, schema_version=schema_version(engine),
        derived=include_derived, pretty=pretty, von=from_, bis=to,
    )
    stamp = date.today().isoformat()
    return Response(
        content=data, media_type="application/json; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="zaehlwerk-daten_{stamp}.json"'},
    )


@router.get("/api/export.zip")
def export_all(session: Session = Depends(get_session)):
    """Gesamt-Backup: alle Systeme als CSV (Import-Format) + Systemkonfiguration als JSON."""
    systems = session.exec(select(System).order_by(System.name)).all()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        cfg = [{
            "name": s.name, "typ": s.typ, "einheit": s.einheit, "farbe": s.farbe,
            "icon": s.icon, "zusatzfelder": s.zusatzfelder, "aktiv": s.aktiv,
        } for s in systems]
        z.writestr("systeme.json", json.dumps(cfg, ensure_ascii=False, indent=2))
        # Zaehler-Metadaten mitsichern: SETUP.md/MIGRATION.md verweisen auf
        # diesen Export als Backup-Weg - ohne sie waeren sie beim Neuaufbau weg.
        meters = session.exec(select(Meter).order_by(Meter.system_id)).all()
        by_id = {s.id: s.name for s in systems}
        z.writestr("zaehler.json", json.dumps([{
            "system": by_id.get(m.system_id, m.system_id),
            "hersteller": m.hersteller, "modell": m.modell,
            "zaehlernummer": m.zaehlernummer, "bauart": m.bauart,
            "baujahr": m.baujahr,
            "eichung_bis": m.eichung_bis.isoformat() if m.eichung_bis else None,
            "messstellenbetreiber": m.messstellenbetreiber,
            "stellen_vor": m.stellen_vor, "stellen_nach": m.stellen_nach,
            "eingebaut_am": m.eingebaut_am.isoformat() if m.eingebaut_am else None,
            "ausgebaut_am": m.ausgebaut_am.isoformat() if m.ausgebaut_am else None,
            "notiz": m.notiz,
        } for m in meters], ensure_ascii=False, indent=2))
        for sy in systems:
            raw = _query_readings(session, sy.id)
            z.writestr(f"zaehlwerk_{sy.name.replace(' ', '_')}.csv", _readings_csv(raw))
    return Response(
        content=buf.getvalue(), media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="zaehlwerk-backup.zip"'},
    )


# ---------- PDF ----------
def _theme_from_query(accent, ink, ink_soft, line, warn) -> dict:
    """Farbrollen aus der Anfrage einsammeln. Die Pruefung auf #RRGGBB passiert
    zentral in report._col() – hier wird nur weitergereicht, None bleibt None."""
    return {"accent": accent, "ink": ink, "ink_soft": ink_soft, "line": line, "warn": warn}


@router.get("/api/systems/{system_id}/report.pdf")
def get_report(
    system_id: str,
    from_: Optional[date] = Query(None, alias="from"),
    to: Optional[date] = Query(None),
    accent: Optional[str] = Query(None, max_length=7),
    ink: Optional[str] = Query(None, max_length=7),
    ink_soft: Optional[str] = Query(None, max_length=7),
    line: Optional[str] = Query(None, max_length=7),
    warn: Optional[str] = Query(None, max_length=7),
    system_colors: bool = Query(False, description="Diagramm in der Systemfarbe zeichnen"),
    include_chart: bool = Query(True),
    include_table: bool = Query(True),
    sources: Optional[str] = Query(None, description="Komma-getrennt: manual,mqtt,ha_api,import"),
    session: Session = Depends(get_session),
):
    system = _require_system(system_id, session)
    enriched = _enriched(session, system, from_, to, _parse_sources(sources))
    pdf = report.build_report_pdf(
        system={"name": system.name, "typ": system.typ, "einheit": system.einheit},
        enriched=enriched,
        stats=logic.compute_stats(enriched, _sigma(session)),
        from_label=from_.strftime("%d.%m.%Y") if from_ else None,
        to_label=to.strftime("%d.%m.%Y") if to else None,
        theme=_theme_from_query(accent, ink, ink_soft, line, warn),
        accent=system.farbe if system_colors else None,
        include_chart=include_chart, include_table=include_table,
    )
    fname = f"zaehlwerk-bericht_{system.name.replace(' ', '_')}.pdf"
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{fname}"'})


@router.get("/api/report.pdf")
def get_combined_report(
    from_: Optional[date] = Query(None, alias="from"),
    to: Optional[date] = Query(None),
    systems_param: Optional[str] = Query(None, alias="systems",
                                         description="Komma-getrennte System-IDs; leer = alle aktiven"),
    include_inactive: bool = Query(False),
    accent: Optional[str] = Query(None, max_length=7),
    ink: Optional[str] = Query(None, max_length=7),
    ink_soft: Optional[str] = Query(None, max_length=7),
    line: Optional[str] = Query(None, max_length=7),
    warn: Optional[str] = Query(None, max_length=7),
    system_colors: bool = Query(False),
    include_chart: bool = Query(True),
    include_table: bool = Query(True),
    sources: Optional[str] = Query(None, description="Komma-getrennt: manual,mqtt,ha_api,import"),
    session: Session = Depends(get_session),
):
    wanted_sources = _parse_sources(sources)
    stmt = select(System)
    if not include_inactive:
        stmt = stmt.where(System.aktiv == True)  # noqa: E712
    if systems_param:
        # Auswahl gegen die DB filtern statt der Eingabe zu vertrauen:
        # unbekannte IDs fallen still weg, statt einen Fehler auszuloesen.
        wanted = {s.strip() for s in systems_param.split(",") if s.strip()}
        if wanted:
            stmt = stmt.where(System.id.in_(wanted))
    systems = session.exec(stmt.order_by(System.name)).all()

    sections = []
    for system in systems:
        enriched = _enriched(session, system, from_, to, wanted_sources)
        sections.append({
            "system": {"name": system.name, "typ": system.typ,
                       "einheit": system.einheit, "farbe": system.farbe},
            "enriched": enriched,
            "stats": logic.compute_stats(enriched, _sigma(session)),
        })
    pdf = report.build_combined_report_pdf(
        sections,
        from_label=from_.strftime("%d.%m.%Y") if from_ else None,
        to_label=to.strftime("%d.%m.%Y") if to else None,
        theme=_theme_from_query(accent, ink, ink_soft, line, warn),
        system_colors=system_colors,
        include_chart=include_chart, include_table=include_table,
    )
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": 'inline; filename="zaehlwerk-gesamtbericht.pdf"'})


# --------------------------------------------------------------------------
# Strom/Gas/Wasser-Übersichtsbericht im VBA-Excel-Standard (TICKET-3.2)
# --------------------------------------------------------------------------
_MONTHS_DE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
              "August", "September", "Oktober", "November", "Dezember"]


def _gas_factor(system: Optional[System]) -> float:
    """kWh-Umrechnungsfaktor je m³ = Brennwert × Zustandszahl (konfigurierbar in
    den Zusatzfeldern des Gas-Systems; Standard 11,0 × 0,95). Vgl. TICKET-2.2."""
    zf = (system.zusatzfelder or {}) if system else {}
    def _num(key, default):
        try:
            return float(zf.get(key, default))
        except (TypeError, ValueError):
            return default
    return _num("brennwert", 11.0) * _num("zustandszahl", 0.95)


@router.get("/api/report/overview.pdf")
def overview_report(session: Session = Depends(get_session)):
    """Medienübergreifende Übersicht (Strom/Gas/Wasser) über die gesamte
    Historie – fünf Sichten + Grafiken, Layout nach VBA-Excel-Standard."""
    from .. import report_overview

    systems = session.exec(select(System).where(System.aktiv == True)).all()  # noqa: E712

    def pick(keyword: str) -> Optional[System]:
        return next((s for s in systems if keyword in s.typ.lower()), None)

    picked = {"strom": pick("strom"), "gas": pick("gas"), "wasser": pick("wasser")}

    # Angereicherte Ablesungen je Medium, indiziert nach Tagesdatum.
    per_medium: dict[str, dict] = {}
    units: dict[str, str] = {}
    for key, sysobj in picked.items():
        units[key] = sysobj.einheit if sysobj else {"strom": "kWh", "gas": "m³", "wasser": "m³"}[key]
        if sysobj is None:
            per_medium[key] = {}
            continue
        enriched = _enriched(session, sysobj, None, None, None)
        per_medium[key] = {e["datum"].date(): e for e in enriched}

    # Zeilen = Vereinigung aller Ablesedaten, chronologisch.
    all_dates = sorted({d for m in per_medium.values() for d in m.keys()})
    rows = [{
        "datum": d,
        "strom": per_medium["strom"].get(d),
        "gas": per_medium["gas"].get(d),
        "wasser": per_medium["wasser"].get(d),
    } for d in all_dates]

    now = datetime.now()
    stand = f"{now.day}.{_MONTHS_DE[now.month - 1]} {now.year} {now:%H:%M}"
    pdf = report_overview.build_overview_pdf(
        rows, units=units, gas_factor=_gas_factor(picked["gas"]), stand_label=stand)
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": 'inline; filename="zaehlwerk-uebersicht.pdf"'})
