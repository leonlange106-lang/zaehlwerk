"""Fälligkeits-Berechnung – gemeinsam genutzt von /api/overview und dem HA-Notifier.
Konfiguriertes Intervall (zusatzfelder.ablese_intervall_tage) hat Vorrang, sonst Median."""
from datetime import datetime, timedelta
from statistics import median

from sqlmodel import Session, select

from .models import Reading, System


def system_due_entries(session: Session) -> list[dict]:
    systems = session.exec(select(System).where(System.aktiv == True)).all()  # noqa: E712
    ids = [s.id for s in systems]
    if not ids:
        return []
    rows = session.exec(
        select(Reading).where(Reading.system_id.in_(ids))
        .order_by(Reading.datum, Reading.meter_replaced)
    ).all()
    by_system: dict[str, list[Reading]] = {}
    for r in rows:
        by_system.setdefault(r.system_id, []).append(r)

    out = []
    now = datetime.now()
    for s in systems:
        rs = by_system.get(s.id, [])
        if not rs or rs[-1].value is None:
            continue
        last = rs[-1]
        entry = {"system": s, "value": last.value, "datum": last.datum}
        interval = None
        try:
            iv = float((s.zusatzfelder or {}).get("ablese_intervall_tage") or 0)
            interval = iv if iv > 0 else None
        except (TypeError, ValueError):
            interval = None
        if interval is None and len(rs) >= 2:
            gaps = [(rs[i].datum - rs[i - 1].datum).days for i in range(1, len(rs))]
            gaps = [g for g in gaps if g > 0]
            interval = median(gaps) if gaps else None
        if interval:
            nxt = last.datum + timedelta(days=interval)
            entry["next_expected"] = nxt
            entry["overdue_days"] = (now - nxt).days
        out.append(entry)
    return out
