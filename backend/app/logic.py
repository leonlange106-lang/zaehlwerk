"""Ableitungen aus den rohen Ablesungen.

REGEL Zählertausch: meter_replaced=True -> der Verbrauch des Tausch-Intervalls
ist value - meter_start. Fehlt meter_start (None), gilt die alte Annahme
"neuer Zähler startet bei 0", der Verbrauch ist dann der abgelesene Wert selbst.
So bleibt der abrupte Rücksprung des Zählerstands auf einen kleinen Wert ohne
negativen Verbrauch (Formel: Gesamt = (Endstand_Alt - Startstand_Alt) +
(Stand_Neu - Startstand_Neu), über die Intervalle aufsummiert).
Guard: Verbrauch wird nie negativ (fehlerhafte Daten werden auf None gesetzt
statt Statistiken zu verfälschen).

KOSTEN: Explizit erfasste Kosten haben Vorrang. Fehlen sie und ist ein
Durchschnittspreis (€/Einheit) am System hinterlegt, wird geschätzt:
cost_effective = consumption * preis. Geschätzte Werte werden markiert.

TARIFE (seit 2.16.0): Liegen Tarifperioden vor, wird der Verbrauch tageweise
dem jeweils gültigen Preis zugeordnet - siehe apply_tariffs() unten. Der
Grundpreis ist seit v3.18.0 ein JAHRESbetrag und wird taggenau umgelegt.

PROGNOSE (seit v3.18.0): rolling_prognosis() rechnet NICHT die gesamte Historie
hoch, sondern nur ein gleitendes Fenster (Standard: 5 Jahre) auf das nächste
Abrechnungsjahr - siehe unten.
"""
from datetime import date, timedelta
import statistics
from typing import Optional


def _days_in_year(year: int) -> int:
    """Kalendertage des Jahres (366 im Schaltjahr). Grundlage der taggenauen
    Jahresbetrags-Umlage: ein Schaltjahr verteilt den Grundpreis auf 366 Tage."""
    return 366 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 365


def compute_intervals(readings: list[dict], price: Optional[float] = None) -> list[dict]:
    """readings: chronologisch aufsteigend. Reichert an um consumption,
    consumption_per_day, cost_effective, cost_estimated."""
    out: list[dict] = []
    for i, r in enumerate(readings):
        e = dict(r)
        e["consumption"] = None
        e["consumption_per_day"] = None
        e["days"] = None
        e["prev_datum"] = None
        if i > 0:
            prev = readings[i - 1]
            days = (r["datum"] - prev["datum"]).total_seconds() / 86400
            e["days"] = int(round(days))
            e["prev_datum"] = prev["datum"]
            if r.get("meter_replaced"):
                # Neuer Zähler: Verbrauch = aktueller Stand - Startstand des
                # neuen Zählers. Ohne Startstand gilt weiter die 0-Annahme.
                start_new = r.get("meter_start")
                base_new = float(start_new) if start_new is not None else 0.0
                cons = float(r["value"]) - base_new
            else:
                cons = float(r["value"]) - float(prev["value"])
            if cons < 0:
                cons = None                                 # Datenfehler -> nicht verfälschen
            e["consumption"] = cons
            e["consumption_per_day"] = (cons / days) if (cons is not None and days > 0) else cons
        # Kosten: explizit > geschätzt (Preis) > None
        if e.get("cost") is not None:
            e["cost_effective"] = float(e["cost"])
            e["cost_estimated"] = False
        elif price and e["consumption"] is not None:
            e["cost_effective"] = e["consumption"] * price
            e["cost_estimated"] = True
        else:
            e["cost_effective"] = None
            e["cost_estimated"] = False
        out.append(e)
    return out


DEFAULT_SIGMA = 2.0

# Ab wie vielen Punkten ein Diagramm verdichtet wird. Chart.js zeichnet darüber
# hinaus spürbar träge, und ein Bildschirm hat ohnehin nicht mehr nutzbare
# Pixelspalten. Die Tabelle der Ablesungen bleibt davon unberührt – verdichtet
# wird ausschließlich die Diagramm-Reihe.
CHART_MAX_POINTS = 600


def downsample_enriched(enriched: list[dict], max_points: int = CHART_MAX_POINTS) -> list[dict]:
    """Verdichtet eine lange Reihe angereicherter Ablesungen auf höchstens
    `max_points` Diagrammpunkte, ohne Verlauf oder Summe zu verfälschen.

    Verfahren: gleich große, aufeinanderfolgende Eimer über den Index. Je Eimer
    entsteht EIN Punkt:
      - datum/value  = Stand am Eimer-ENDE (kumulativer Zählerstand bleibt korrekt)
      - consumption  = Summe des Eimers (Fläche bleibt erhalten)
      - consumption_per_day = Summe/Summe-der-Tage (mengengewichteter Schnitt,
        formtreu statt eines einfachen Mittelwerts über ungleiche Intervalle)
      - is_outlier / meter_replaced = ODER über den Eimer (Marker gehen nicht verloren)

    Reicht die Reihe (<= max_points), wird sie unverändert zurückgegeben.
    """
    n = len(enriched)
    if not max_points or max_points <= 0 or n <= max_points:
        return enriched
    import math
    size = math.ceil(n / max_points)
    out: list[dict] = []
    for i in range(0, n, size):
        chunk = enriched[i:i + size]
        last = chunk[-1]
        cons_vals = [e["consumption"] for e in chunk if e.get("consumption") is not None]
        day_vals = [e["days"] for e in chunk if e.get("days")]
        total_cons = sum(cons_vals) if cons_vals else None
        total_days = sum(day_vals) if day_vals else None
        cpd = (total_cons / total_days) if (total_cons is not None and total_days) else None
        out.append({
            "datum": last["datum"],
            "value": last["value"],
            "consumption": round(total_cons, 4) if total_cons is not None else None,
            "consumption_per_day": round(cpd, 4) if cpd is not None else None,
            "is_outlier": any(e.get("is_outlier") for e in chunk),
            "meter_replaced": any(e.get("meter_replaced") for e in chunk),
        })
    return out


def outlier_threshold(enriched: list[dict], sigma: float = DEFAULT_SIGMA) -> Optional[float]:
    vals = [e["consumption_per_day"] for e in enriched if e["consumption_per_day"] is not None]
    if len(vals) < 2:
        return None
    return statistics.mean(vals) + sigma * statistics.pstdev(vals)


def mark_outliers(enriched: list[dict], sigma: float = DEFAULT_SIGMA) -> list[dict]:
    thr = outlier_threshold(enriched, sigma)
    for e in enriched:
        pd = e["consumption_per_day"]
        e["is_outlier"] = bool(thr is not None and pd is not None and pd > thr)
    return enriched


def compute_stats(enriched: list[dict], sigma: float = DEFAULT_SIGMA) -> dict:
    cons_vals = [e["consumption"] for e in enriched if e["consumption"] is not None]
    per_days = [
        (e["consumption_per_day"], e["datum"])
        for e in enriched if e["consumption_per_day"] is not None
    ]
    costs = [e["cost_effective"] for e in enriched if e.get("cost_effective") is not None]
    any_estimated = any(e.get("cost_estimated") for e in enriched)

    total_consumption = sum(cons_vals) if cons_vals else 0.0
    total_cost = sum(costs) if costs else 0.0

    total_days = 0.0
    if len(enriched) >= 2:
        total_days = (enriched[-1]["datum"] - enriched[0]["datum"]).total_seconds() / 86400

    avg_per_day = (total_consumption / total_days) if total_days > 0 else None
    cost_per_day = (total_cost / total_days) if total_days > 0 and total_cost else None
    cost_per_unit = (total_cost / total_consumption) if total_consumption and total_cost else None

    min_pd = max_pd = min_dt = max_dt = None
    if per_days:
        min_pd, min_dt = min(per_days, key=lambda x: x[0])
        max_pd, max_dt = max(per_days, key=lambda x: x[0])

    return {
        "total_consumption": round(total_consumption, 3),
        "total_cost": round(total_cost, 2),
        "total_days": round(total_days, 1),
        "avg_per_day": round(avg_per_day, 3) if avg_per_day is not None else None,
        "cost_per_day": round(cost_per_day, 4) if cost_per_day is not None else None,
        "cost_per_unit": round(cost_per_unit, 4) if cost_per_unit is not None else None,
        "min_per_day": round(min_pd, 3) if min_pd is not None else None,
        "min_per_day_datum": min_dt,
        "max_per_day": round(max_pd, 3) if max_pd is not None else None,
        "max_per_day_datum": max_dt,
        "outlier_threshold": outlier_threshold(enriched, sigma),
        "reading_count": len(enriched),
        "cost_estimated": any_estimated,
    }


# ==========================================================================
# Tarifbasierte Kostenberechnung
# ==========================================================================
# Grundgedanke: Zwischen zwei Ablesungen ist nur der Gesamtverbrauch bekannt,
# nicht sein zeitlicher Verlauf. Er wird deshalb gleichmäßig über die Tage des
# Intervalls verteilt (`consumption_per_day`) und anschließend tageweise dem
# jeweils gültigen Tarif zugeordnet. Ein Intervall, das über einen Tarifwechsel
# hinweggeht, wird also korrekt aufgeteilt – genau der Fall, den eine simple
# Multiplikation mit einem einzigen Preis falsch berechnet.
#
# Der Grundpreis ist seit v3.18.0 ein JAHRESbetrag. Er wird taggenau umgelegt:
# je Verbrauchstag grundpreis / Tage-des-jeweiligen-Jahres. Ein Intervall über
# einen Jahreswechsel hinweg zahlt so für Tage in 2024 (Schaltjahr) 1/366 und
# für Tage in 2025 1/365 des Jahresbetrags - strikt tagesgenau statt pauschal.


def _tariff_for(tariffs: list[dict], day: date) -> Optional[dict]:
    """Erste Periode, die diesen Tag abdeckt. Perioden sind überschneidungsfrei
    (wird beim Speichern geprüft), daher ist die erste zugleich die einzige."""
    for t in tariffs:
        if t["gueltig_ab"] <= day and (t["gueltig_bis"] is None or day <= t["gueltig_bis"]):
            return t
    return None


def apply_tariffs(enriched: list[dict], tariffs: list[dict]) -> list[dict]:
    """Ergänzt je Intervall die tarifbasierten Kosten.

    Neue Felder je Eintrag:
      cost_tariff         Gesamt (Arbeits- + Grundpreis) oder None
      cost_tariff_energy  nur Arbeitspreis
      cost_tariff_base    nur Grundpreis
      tariff_coverage     Anteil der Tage mit hinterlegtem Tarif (0.0-1.0)
      tariff_names        beteiligte Tarife, für die Anzeige

    Die vorhandenen Felder `cost` (erfasst) und `cost_estimated` bleiben
    unangetastet – die Tarifrechnung tritt daneben, nicht an ihre Stelle.
    """
    if not tariffs:
        return enriched

    for e in enriched:
        e["cost_tariff"] = None
        e["cost_tariff_energy"] = None
        e["cost_tariff_base"] = None
        e["tariff_coverage"] = 0.0
        e["tariff_names"] = []

        per_day = e.get("consumption_per_day")
        days = e.get("days")
        prev = e.get("prev_datum")
        if per_day is None or not days or not prev:
            continue

        energy = 0.0
        base = 0.0
        covered = 0
        names = []
        # Verbrauchstage sind die Tage NACH der Vorablesung bis einschließlich
        # der aktuellen - die Vorablesung selbst gehört zum vorigen Intervall.
        for i in range(1, days + 1):
            day = prev + timedelta(days=i)
            # Tarifperioden sind datumsbasiert; Ablesedaten kommen als datetime.
            # Auf ein date normalisieren, damit der Vergleich in _tariff_for
            # nicht an gemischten Typen (datetime vs date) scheitert.
            day = day.date() if hasattr(day, "date") else day
            t = _tariff_for(tariffs, day)
            if not t:
                continue
            covered += 1
            energy += per_day * t["arbeitspreis"]
            # Jahresgrundpreis taggenau: durch die Kalendertage GENAU DIESES
            # Tages-Jahres teilen, damit Schaltjahre exakt aufgehen.
            base += (t.get("grundpreis") or 0.0) / _days_in_year(day.year)
            label = t.get("name") or t.get("anbieter") or "Tarif"
            if label not in names:
                names.append(label)

        if covered:
            e["cost_tariff_energy"] = round(energy, 2)
            e["cost_tariff_base"] = round(base, 2)
            e["cost_tariff"] = round(energy + base, 2)
            e["tariff_coverage"] = round(covered / days, 4)
            e["tariff_names"] = names
    return enriched


def tariff_summary(enriched: list[dict]) -> dict:
    """Kennzahlen über alle Intervalle mit Tarifabdeckung."""
    rows = [e for e in enriched if e.get("cost_tariff") is not None]
    if not rows:
        return {"total_cost_tariff": None, "total_energy_cost": None,
                "total_base_cost": None, "avg_price_effective": None,
                "covered_intervals": 0, "coverage_ratio": 0.0}
    total = sum(r["cost_tariff"] for r in rows)
    energy = sum(r["cost_tariff_energy"] for r in rows)
    base = sum(r["cost_tariff_base"] for r in rows)
    consumption = sum(r["consumption"] for r in rows if r.get("consumption"))
    with_interval = [e for e in enriched if e.get("consumption") is not None]
    return {
        "total_cost_tariff": round(total, 2),
        "total_energy_cost": round(energy, 2),
        "total_base_cost": round(base, 2),
        # Effektivpreis inklusive Grundgebühr - die Zahl, die man mit dem
        # beworbenen Arbeitspreis vergleichen will.
        "avg_price_effective": round(total / consumption, 4) if consumption else None,
        "covered_intervals": len(rows),
        "coverage_ratio": round(len(rows) / len(with_interval), 4) if with_interval else 0.0,
    }


# ==========================================================================
# Prognose für das nächste Abrechnungsjahr (v3.18.0)
# ==========================================================================
# Bewusst KEINE klassische Jahreshochrechnung über den gesamten Bestand: ein
# Zähler kann Jahrzehnte alt sein, und Nutzungsmuster von vor einer Sanierung
# oder einem Umzug verzerren jede Vorhersage. Stattdessen ein gleitendes Fenster
# (Standard: fünf Jahre) als Grundlage und eine Projektion auf genau ein
# kommendes Abrechnungsjahr.
ROLLING_YEARS_DEFAULT = 5
_MIN_WINDOW_DAYS = 30            # darunter ist ein Mittelwert nicht aussagekräftig


def _current_tariff(tariffs: list[dict], ref: date) -> Optional[dict]:
    """Der am Stichtag gültige Tarif; ist keiner (mehr) gültig, der zuletzt
    beginnende. Grundlage der Kostenprojektion – prognostiziert wird mit dem
    Preis, der voraussichtlich weiter gilt, nicht mit einem historischen."""
    hit = _tariff_for(tariffs, ref)
    if hit:
        return hit
    dated = [t for t in tariffs if t.get("gueltig_ab")]
    return max(dated, key=lambda t: t["gueltig_ab"]) if dated else None


def _next_billing_year(ref: date, start_month: Optional[int]) -> tuple[date, date]:
    """Grenzen des nächsten Abrechnungsjahres. start_month=None -> Kalenderjahr.
    „Nächstes“ = der erste Abrechnungsbeginn NACH dem Stichtag."""
    m = start_month if start_month and 1 <= start_month <= 12 else 1
    start = date(ref.year, m, 1)
    if start <= ref:
        start = date(ref.year + 1, m, 1)
    end = date(start.year + 1, start.month, 1) - timedelta(days=1)
    return start, end


def rolling_prognosis(enriched: list[dict], tariffs: list[dict], *,
                      years: int = ROLLING_YEARS_DEFAULT,
                      abschlag: Optional[float] = None,
                      billing_start_month: Optional[int] = None,
                      reference_date: Optional[date] = None) -> Optional[dict]:
    """Prognose des Verbrauchs und der Kosten für das nächste Abrechnungsjahr.

    Grundlage ist der mittlere Tagesverbrauch der letzten `years` Jahre
    (gleitendes Fenster, NIE die gesamte Historie). Reicht die Datenlage im
    Fenster nicht (< 30 abgedeckte Tage), wird None zurückgegeben.

    Ist ein monatlicher `abschlag` gesetzt, prüft die Funktion zusätzlich, ob
    die Jahresprognose den Jahresabschlag (12 × abschlag) übersteigt.
    """
    ref = reference_date or date.today()
    window_start = ref - timedelta(days=int(years * 365.25))

    def _as_date(v):
        return v.date() if hasattr(v, "date") else v

    total_cons = 0.0
    total_days = 0
    for e in enriched:
        cpd = e.get("consumption_per_day")
        prev = e.get("prev_datum")
        cur = e.get("datum")
        if cpd is None or prev is None or cur is None:
            continue
        iv_start = _as_date(prev)
        iv_end = _as_date(cur)
        # Intervall auf das Fenster [window_start, ref] beschneiden – so zählt
        # ein Intervall, das in das Fenster hineinragt, anteilig mit.
        ov_start = max(iv_start, window_start)
        ov_end = min(iv_end, ref)
        ov_days = (ov_end - ov_start).days
        if ov_days <= 0:
            continue
        total_cons += cpd * ov_days
        total_days += ov_days

    if total_days < _MIN_WINDOW_DAYS:
        return None

    avg_per_day = total_cons / total_days
    b_start, b_end = _next_billing_year(ref, billing_start_month)
    billing_days = (b_end - b_start).days + 1
    projected_consumption = avg_per_day * billing_days

    tariff = _current_tariff(tariffs, ref)
    projected_energy = projected_base = projected_cost = None
    if tariff:
        projected_energy = projected_consumption * tariff["arbeitspreis"]
        # Jahresgrundpreis, auf die tatsächliche Länge des Abrechnungsjahres
        # skaliert (Schaltjahr: 366 Tage).
        projected_base = (tariff.get("grundpreis") or 0.0) * billing_days / _days_in_year(b_start.year)
        projected_cost = projected_energy + projected_base

    abschlag_annual = None
    exceeds = False
    shortfall = None
    if abschlag and abschlag > 0:
        abschlag_annual = abschlag * 12
        if projected_cost is not None:
            shortfall = projected_cost - abschlag_annual
            exceeds = shortfall > 0

    return {
        "window_years": years,
        "window_from": window_start,
        "window_to": ref,
        "window_days": total_days,
        "avg_per_day": round(avg_per_day, 4),
        "billing_year_start": b_start,
        "billing_year_end": b_end,
        "billing_days": billing_days,
        "projected_consumption": round(projected_consumption, 2),
        "projected_energy_cost": round(projected_energy, 2) if projected_energy is not None else None,
        "projected_base_cost": round(projected_base, 2) if projected_base is not None else None,
        "projected_cost": round(projected_cost, 2) if projected_cost is not None else None,
        "abschlag_monthly": round(abschlag, 2) if abschlag else None,
        "abschlag_annual": round(abschlag_annual, 2) if abschlag_annual is not None else None,
        "exceeds_abschlag": exceeds,
        "shortfall": round(shortfall, 2) if shortfall is not None else None,
    }
