"""Kritische Absicherung der Verbrauchs- und Abrechnungslogik (v3.18.0).

Reine Funktionstests gegen `app.logic` – ohne Datenbank, ohne HTTP. Abgedeckt
sind die im Ticket genannten Edge-Cases: Zählertausch bei unterjährigem
Tarifwechsel, Preissenkungen mitten im Intervall (z. B. eine MwSt.-Senkung, die
im Brutto-Modell als neue Tarifperiode erscheint) und Zeiträume ohne Ablesung.
"""
from datetime import date, datetime

import pytest

from app import logic


def R(y, m, d, value, **extra):
    """Kurzschreibweise für eine Ablesung als Dict (wie sie logic.py erwartet)."""
    return {"datum": datetime(y, m, d), "value": float(value), **extra}


def T(ab, bis, arbeit, grund=0.0, name="T"):
    return {"name": name, "anbieter": None, "gueltig_ab": ab,
            "gueltig_bis": bis, "arbeitspreis": arbeit, "grundpreis": grund}


def _cons(rows):
    return logic.compute_intervals(rows)


# ==========================================================================
# Verbrauch: Grundfälle
# ==========================================================================
def test_no_readings_is_empty():
    assert logic.compute_intervals([]) == []


def test_single_reading_has_no_interval():
    iv = _cons([R(2025, 1, 1, 100)])
    assert iv[0]["consumption"] is None
    assert iv[0]["consumption_per_day"] is None


def test_simple_consumption_and_per_day():
    iv = _cons([R(2025, 1, 1, 0), R(2025, 1, 11, 100)])
    assert iv[1]["consumption"] == 100
    assert iv[1]["days"] == 10
    assert iv[1]["consumption_per_day"] == 10


# ==========================================================================
# Zählertausch
# ==========================================================================
def test_meter_replacement_with_start_value():
    """Verbrauch = Ablesewert − Startstand des neuen Zählers."""
    iv = _cons([
        R(2025, 1, 1, 1000),
        R(2025, 7, 1, 1600),                              # alter Zähler +600
        R(2026, 1, 1, 300, meter_replaced=True, meter_start=50),  # neu: 300-50=250
    ])
    assert iv[1]["consumption"] == 600
    assert iv[2]["consumption"] == 250
    total = sum(e["consumption"] for e in iv if e["consumption"] is not None)
    assert total == 850


def test_meter_replacement_without_start_defaults_to_zero():
    """Ohne Startstand gilt die alte 0-Annahme (Rückwärtskompatibilität)."""
    iv = _cons([
        R(2025, 1, 1, 1000),
        R(2026, 1, 1, 300, meter_replaced=True),
    ])
    assert iv[1]["consumption"] == 300


def test_meter_zero_drop_never_negative():
    """Der abrupte Rücksprung auf einen kleinen Wert erzeugt keinen negativen
    Verbrauch – ohne Tausch wird ein Datenfehler zu None entschärft."""
    iv = _cons([R(2025, 1, 1, 5000), R(2025, 2, 1, 3)])   # Sturz ohne Tausch
    assert iv[1]["consumption"] is None                    # nicht negativ


def test_meter_start_above_reading_would_be_negative_guarded():
    iv = _cons([R(2025, 1, 1, 100),
                R(2025, 2, 1, 40, meter_replaced=True, meter_start=50)])  # 40-50 < 0
    assert iv[1]["consumption"] is None


# ==========================================================================
# Tarife: Arbeits- und Grundpreis (Jahresbetrag, taggenau)
# ==========================================================================
def test_yearly_base_fee_day_exact_normal_year():
    iv = logic.apply_tariffs(
        _cons([R(2025, 1, 1, 0), R(2026, 1, 1, 3650)]),          # 365 Tage
        [T(date(2020, 1, 1), None, 0.30, grund=120.0)])
    assert iv[1]["cost_tariff_energy"] == pytest.approx(1095.0)   # 3650*0.30
    assert iv[1]["cost_tariff_base"] == pytest.approx(120.0)      # 365/365


def test_yearly_base_fee_leap_year():
    iv = logic.apply_tariffs(
        _cons([R(2024, 1, 1, 0), R(2025, 1, 1, 366)]),           # 366 Tage (Schaltjahr)
        [T(date(2020, 1, 1), None, 0.30, grund=120.0)])
    assert iv[1]["cost_tariff_base"] == pytest.approx(120.0)      # 366 * (120/366)


def test_no_tariff_no_tariff_cost():
    # Ohne Tarife kehrt apply_tariffs früh zurück und ergänzt die cost_tariff-
    # Felder gar nicht erst – .get() liefert dann None.
    iv = logic.apply_tariffs(_cons([R(2025, 1, 1, 0), R(2025, 2, 1, 100)]), [])
    assert iv[1].get("cost_tariff") is None


# ==========================================================================
# Unterjähriger Tarifwechsel / Preissenkung mitten im Intervall
# ==========================================================================
def test_mid_interval_tariff_split():
    """Ein Intervall über einen Tarifwechsel wird taggenau aufgeteilt.
    31 Tage Januar zu 0,40, 28 Tage Februar zu 0,30; 1/Tag Verbrauch."""
    tariffs = [
        T(date(2025, 1, 1), date(2025, 1, 31), 0.40, name="alt"),
        T(date(2025, 2, 1), None, 0.30, name="neu"),
    ]
    iv = logic.apply_tariffs(_cons([R(2025, 1, 1, 0), R(2025, 3, 1, 59)]), tariffs)  # 59 Tage, 1/Tag
    # Verbrauchstage sind die Tage NACH der Vorablesung (2.1.–1.3.):
    #   „alt“ (bis 31.1.) deckt 2.–31.1. = 30 Tage *1*0,40 = 12,00
    #   „neu“ (ab 1.2.)   deckt 1.–28.2. + 1.3. = 29 Tage *1*0,30 = 8,70
    assert iv[1]["cost_tariff_energy"] == pytest.approx(12.00 + 8.70, abs=1e-6)
    assert set(iv[1]["tariff_names"]) == {"alt", "neu"}
    assert iv[1]["tariff_coverage"] == pytest.approx(1.0)


def test_vat_cut_modeled_as_lower_tariff_period():
    """Eine MwSt.-Senkung ist im Brutto-Modell eine neue Tarifperiode mit
    niedrigerem Bruttopreis. Der Wechsel mitten im Intervall muss korrekt
    zugunsten des günstigeren Preises aufteilen."""
    tariffs = [
        T(date(2025, 1, 1), date(2025, 6, 30), 0.3570, name="19% MwSt"),
        T(date(2025, 7, 1), None, 0.3270, name="7% MwSt"),   # temporäre Senkung
    ]
    # ganzes Jahr, 2 kWh/Tag
    iv = logic.apply_tariffs(_cons([R(2025, 1, 1, 0), R(2026, 1, 1, 730)]), tariffs)
    e = iv[1]
    # Erste Jahreshälfte teurer als zweite -> Effektivpreis liegt zwischen den beiden.
    assert e["cost_tariff_energy"] is not None
    eff = e["cost_tariff_energy"] / e["consumption"]
    assert 0.3270 < eff < 0.3570


def test_meter_replacement_during_tariff_change():
    """Kombinierter Edge-Case: Zählertausch UND Tarifwechsel im selben Jahr.
    Der Verbrauch muss korrekt (über den Startstand) bestimmt und der
    Tarifwechsel taggenau angewendet werden."""
    tariffs = [
        T(date(2025, 1, 1), date(2025, 5, 31), 0.40, name="vor Wechsel"),
        T(date(2025, 6, 1), None, 0.30, name="nach Wechsel"),
    ]
    rows = [
        R(2025, 1, 1, 1000),
        R(2025, 5, 1, 1120),                                   # alter Zähler +120
        R(2025, 9, 1, 240, meter_replaced=True, meter_start=0),  # neuer Zähler 0->240
    ]
    iv = logic.apply_tariffs(_cons(rows), tariffs)
    # Verbrauch stimmt trotz Tausch
    assert iv[1]["consumption"] == 120
    assert iv[2]["consumption"] == 240
    # Das Tausch-Intervall (Mai..Sep) läuft über den Wechsel am 1.6. -> beide Tarife
    assert set(iv[2]["tariff_names"]) == {"vor Wechsel", "nach Wechsel"}


# ==========================================================================
# Zeiträume ohne Ablesung (Lücken)
# ==========================================================================
def test_gap_without_readings_spreads_consumption():
    """Eine lange Lücke ohne Ablesung: der Verbrauch wird gleichmäßig über alle
    Tage verteilt und tageweise dem gültigen Tarif zugeordnet."""
    tariffs = [T(date(2020, 1, 1), None, 0.25, grund=0.0)]
    iv = logic.apply_tariffs(_cons([R(2024, 1, 1, 0), R(2026, 1, 1, 7300)]), tariffs)  # 731 Tage
    assert iv[1]["days"] == 731
    assert iv[1]["consumption"] == 7300
    # voller Tarif-Deckungsgrad trotz fehlender Zwischenablesungen
    assert iv[1]["tariff_coverage"] == pytest.approx(1.0)
    assert iv[1]["cost_tariff_energy"] == pytest.approx(7300 * 0.25, abs=1e-6)


def test_partial_tariff_coverage():
    """Deckt der Tarif nur einen Teil des Intervalls ab, sinkt die Coverage
    entsprechend – Tage ohne Tarif tragen keine Tarifkosten."""
    tariffs = [T(date(2025, 2, 1), None, 0.30)]   # beginnt erst im Februar
    iv = logic.apply_tariffs(_cons([R(2025, 1, 1, 0), R(2025, 3, 1, 59)]), tariffs)
    assert 0.0 < iv[1]["tariff_coverage"] < 1.0


# ==========================================================================
# Statistik
# ==========================================================================
def test_stats_totals_and_outlier_threshold():
    iv = logic.mark_outliers(_cons([
        R(2025, 1, 1, 0), R(2025, 1, 11, 100), R(2025, 1, 21, 200),
    ]))
    stats = logic.compute_stats(iv)
    assert stats["total_consumption"] == 200
    assert stats["reading_count"] == 3
    assert stats["avg_per_day"] == pytest.approx(10.0)


# ==========================================================================
# Downsampling (v3.22.0): lange Reihen fürs Diagramm verdichten
# ==========================================================================
def test_downsample_reduces_and_preserves_total():
    # saubere, monoton steigende Tagesreihe über ~5,5 Jahre
    from datetime import timedelta
    base = datetime(2019, 1, 1)
    series = [{"datum": base + timedelta(days=i), "value": float(i * 10)} for i in range(2000)]
    enr = logic.compute_intervals(series)
    total_before = sum(e["consumption"] for e in enr if e["consumption"] is not None)

    ds = logic.downsample_enriched(enr, 600)
    assert len(ds) <= 600 < len(enr)
    total_after = sum(e["consumption"] for e in ds if e["consumption"] is not None)
    assert abs(total_before - total_after) < 1e-6      # Fläche bleibt erhalten
    # Endstand bleibt der letzte echte Wert
    assert ds[-1]["value"] == enr[-1]["value"]


def test_downsample_noop_for_short_series():
    enr = logic.compute_intervals([R(2025, 1, 1, 0), R(2025, 1, 2, 10)])
    assert logic.downsample_enriched(enr, 600) is enr


def test_downsample_keeps_markers():
    from datetime import timedelta
    base = datetime(2020, 1, 1)
    series = [{"datum": base + timedelta(days=i), "value": float(i * 10)} for i in range(1000)]
    series[500]["meter_replaced"] = True
    series[500]["meter_start"] = float(500 * 10)   # kein Sprung -> Verbrauch bleibt gültig
    enr = logic.compute_intervals(series)
    ds = logic.downsample_enriched(enr, 100)
    assert any(p["meter_replaced"] for p in ds)     # Tausch-Marker überlebt
