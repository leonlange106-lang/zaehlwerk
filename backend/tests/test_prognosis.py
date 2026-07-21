"""Edge-Cases der Prognose-Engine (v3.18.0): 5-Jahres-Rolling-Average fürs
nächste Abrechnungsjahr, Abschlags-Schwelle, Datenlücken. Reine Funktionstests."""
from datetime import date, datetime

import pytest

from app import logic


def R(y, m, d, value, **extra):
    return {"datum": datetime(y, m, d), "value": float(value), **extra}


def T(ab, arbeit, grund=0.0):
    return {"name": "T", "anbieter": None, "gueltig_ab": ab, "gueltig_bis": None,
            "arbeitspreis": arbeit, "grundpreis": grund}


def _enriched(rows, tariffs):
    return logic.apply_tariffs(logic.compute_intervals(rows), tariffs)


# jährliche Ablesungen, konstant 3650/Jahr = 10/Tag
YEARLY = [R(y, 1, 1, (y - 2019) * 3650) for y in range(2019, 2027)]
TARIFF = [T(date(2018, 1, 1), 0.30, grund=120.0)]


def test_rolling_window_excludes_old_usage():
    """Ein hoher Altverbrauch vor dem 5-Jahres-Fenster darf die Prognose nicht
    verzerren."""
    rows = [
        R(2019, 1, 1, 0), R(2020, 1, 1, 7300),   # 20/Tag (alt, außerhalb Fenster)
        R(2021, 1, 1, 10950), R(2022, 1, 1, 14600), R(2023, 1, 1, 18250),
        R(2024, 1, 1, 21900), R(2025, 1, 1, 25550),  # je 10/Tag
    ]
    p = logic.rolling_prognosis(_enriched(rows, TARIFF), TARIFF, years=5,
                                reference_date=date(2025, 7, 1))
    assert p["avg_per_day"] == pytest.approx(10.0, abs=0.05)


def test_next_calendar_year_anchor():
    p = logic.rolling_prognosis(_enriched(YEARLY, TARIFF), TARIFF,
                                reference_date=date(2025, 7, 1))
    assert str(p["billing_year_start"]) == "2026-01-01"
    assert str(p["billing_year_end"]) == "2026-12-31"
    assert p["billing_days"] == 365


def test_billing_month_anchor_before_and_after_boundary():
    en = _enriched(YEARLY, TARIFF)
    before = logic.rolling_prognosis(en, TARIFF, billing_start_month=7,
                                     reference_date=date(2025, 6, 15))
    assert str(before["billing_year_start"]) == "2025-07-01"
    after = logic.rolling_prognosis(en, TARIFF, billing_start_month=7,
                                    reference_date=date(2025, 8, 1))
    assert str(after["billing_year_start"]) == "2026-07-01"


def test_abschlag_threshold_exceeded():
    p = logic.rolling_prognosis(_enriched(YEARLY, TARIFF), TARIFF, abschlag=90,
                                reference_date=date(2025, 7, 1))
    # ~3650 kWh * 0,30 + 120 = 1215 €/Jahr > 12*90 = 1080
    assert p["abschlag_annual"] == pytest.approx(1080.0)
    assert p["exceeds_abschlag"] is True
    assert p["shortfall"] == pytest.approx(p["projected_cost"] - 1080.0)


def test_abschlag_within_budget():
    p = logic.rolling_prognosis(_enriched(YEARLY, TARIFF), TARIFF, abschlag=150,
                                reference_date=date(2025, 7, 1))
    assert p["exceeds_abschlag"] is False


def test_insufficient_data_returns_none():
    rows = [R(2025, 1, 1, 0), R(2025, 1, 10, 90)]   # nur 9 Tage im Fenster
    p = logic.rolling_prognosis(_enriched(rows, TARIFF), TARIFF,
                                reference_date=date(2025, 2, 1))
    assert p is None


def test_no_tariff_projects_consumption_only():
    p = logic.rolling_prognosis(_enriched(YEARLY, []), [],
                                reference_date=date(2025, 7, 1))
    assert p["projected_consumption"] is not None
    assert p["projected_cost"] is None
    assert p["exceeds_abschlag"] is False
