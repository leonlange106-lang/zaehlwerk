"""Rohdaten-Export für externe Auswertung.

Abgrenzung zu den bestehenden Ausgaben – die drei Formate haben verschiedene
Aufgaben und sind bewusst nicht austauschbar:

* ``/api/systems/{id}/export.csv``  je System, **importkompatibel**. Der Weg
  zurück in Zählwerk. Spalten genau so, wie der Import sie erwartet.
* ``/api/export.zip``  Sicherung. Enthält je System eine importkompatible CSV
  plus Systemkonfiguration und Zähler-Metadaten.
* **Dieses Modul**  Auswertung in fremden Werkzeugen. Ein flaches CSV über
  alle Systeme beziehungsweise ein vollständiges JSON. Beide enthalten
  abgeleitete Größen wie Verbrauch, Tagesverbrauch und Kosten und sind
  **nicht** wieder einlesbar – sie sind Ausgabe, kein Austauschformat.

CSV-Voreinstellung ist das deutsche Excel-Format: Semikolon als Trennzeichen,
Komma als Dezimaltrennzeichen, UTF-8 mit BOM. Ohne BOM zeigt Excel Umlaute
falsch an, ohne Semikolon landet alles in einer Spalte. Wer nach pandas oder R
exportiert, stellt über ``dialect=international`` auf Komma und Punkt um.
"""
import csv
import io
import json
from datetime import date, datetime
from typing import Any, Optional

CSV_COLUMNS = [
    ("system", "System"),
    ("system_id", "System-ID"),
    ("typ", "Typ"),
    ("einheit", "Einheit"),
    ("datum", "Datum"),
    ("zaehlerstand", "Zählerstand"),
    ("zaehlertausch", "Zählertausch"),
    ("tage", "Tage seit Vorablesung"),
    ("verbrauch", "Verbrauch"),
    ("verbrauch_pro_tag", "Verbrauch/Tag"),
    ("ausreisser", "Ausreißer"),
    ("kosten_erfasst", "Kosten erfasst (€)"),
    ("kosten_effektiv", "Kosten effektiv (€)"),
    ("kosten_geschaetzt", "Kosten geschätzt"),
    ("kosten_tarif", "Kosten nach Tarif (€)"),
    ("kosten_tarif_arbeit", "davon Arbeitspreis (€)"),
    ("kosten_tarif_grund", "davon Grundpreis (€)"),
    ("tarif", "Tarif"),
    ("notiz", "Notiz"),
]

DIALECTS = {
    # Excel deutsch
    "de": {"delimiter": ";", "decimal": ",", "bom": True},
    # pandas, R, Excel englisch
    "international": {"delimiter": ",", "decimal": ".", "bom": False},
}


def _num(value: Optional[float], decimals: int, decimal_sep: str) -> str:
    if value is None:
        return ""
    text = f"{float(value):.{decimals}f}"
    return text.replace(".", decimal_sep) if decimal_sep != "." else text


def _row(system: dict, e: dict, sep: str) -> list[str]:
    datum = e.get("datum")
    if isinstance(datum, datetime):
        datum = datum.date()
    return [
        system["name"], system["id"], system["typ"], system["einheit"],
        datum.isoformat() if isinstance(datum, date) else "",
        _num(e.get("value"), 4, sep),
        "ja" if e.get("meter_replaced") else "",
        "" if e.get("days") is None else str(e["days"]),
        _num(e.get("consumption"), 4, sep),
        _num(e.get("consumption_per_day"), 6, sep),
        "ja" if e.get("is_outlier") else "",
        _num(e.get("cost"), 2, sep),
        _num(e.get("cost_effective"), 2, sep),
        "ja" if e.get("cost_estimated") else "",
        _num(e.get("cost_tariff"), 2, sep),
        _num(e.get("cost_tariff_energy"), 2, sep),
        _num(e.get("cost_tariff_base"), 2, sep),
        ", ".join(e.get("tariff_names") or []),
        (e.get("note") or "").replace("\n", " ").strip(),
    ]


def build_csv(sections: list[dict], dialect: str = "de") -> bytes:
    """Ein flaches CSV über alle Systeme, eine Zeile je Ablesung."""
    cfg = DIALECTS.get(dialect, DIALECTS["de"])
    buf = io.StringIO(newline="")
    # QUOTE_MINIMAL genügt: Notizen können das Trennzeichen enthalten und
    # werden dann automatisch eingefasst.
    writer = csv.writer(buf, delimiter=cfg["delimiter"], quoting=csv.QUOTE_MINIMAL,
                        lineterminator="\r\n")
    writer.writerow([label for _, label in CSV_COLUMNS])
    for sec in sections:
        system = sec["system"]
        for e in sec["enriched"]:
            writer.writerow(_row(system, e, cfg["decimal"]))
    text = buf.getvalue()
    return (("\ufeff" + text) if cfg["bom"] else text).encode("utf-8")


def _jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    if isinstance(value, date):
        return value.isoformat()
    return value


def _reading_json(e: dict, derived: bool) -> dict:
    out = {
        "datum": _jsonable(e.get("datum")),
        "zaehlerstand": e.get("value"),
        "zaehlertausch": bool(e.get("meter_replaced")),
        "kosten_erfasst": e.get("cost"),
        "notiz": e.get("note") or None,
    }
    if not derived:
        return out
    out["abgeleitet"] = {
        "tage": e.get("days"),
        "verbrauch": e.get("consumption"),
        "verbrauch_pro_tag": e.get("consumption_per_day"),
        "ausreisser": bool(e.get("is_outlier")),
        "kosten_effektiv": e.get("cost_effective"),
        "kosten_geschaetzt": bool(e.get("cost_estimated")),
        "kosten_tarif": e.get("cost_tariff"),
        "kosten_tarif_arbeit": e.get("cost_tariff_energy"),
        "kosten_tarif_grund": e.get("cost_tariff_base"),
        "tarife": e.get("tariff_names") or [],
    }
    return out


def build_json(sections: list[dict], *, app_version: str, schema_version: int,
               derived: bool = True, pretty: bool = True,
               von: Optional[date] = None, bis: Optional[date] = None) -> bytes:
    """Vollständiger strukturierter Export.

    Der Kopf trägt Format- und Schemaversion mit. Wer den Export in einem
    fremden Werkzeug einliest, kann daran erkennen, ob sich der Aufbau
    geändert hat, statt es an den Feldern zu erraten.
    """
    doc = {
        "format": "zaehlwerk-export",
        "format_version": 1,
        "app_version": app_version,
        "schema_version": schema_version,
        "erstellt_am": datetime.now().isoformat(timespec="seconds"),
        "zeitraum": {"von": von.isoformat() if von else None,
                     "bis": bis.isoformat() if bis else None},
        "enthaelt_abgeleitete_werte": derived,
        "hinweis": "Ausgabeformat für externe Auswertung. Für den Re-Import nach "
                   "Zählwerk die systemweise CSV bzw. den ZIP-Export verwenden.",
        "systeme": [],
    }
    for sec in sections:
        s = sec["system"]
        doc["systeme"].append({
            "id": s["id"],
            "name": s["name"],
            "typ": s["typ"],
            "einheit": s["einheit"],
            "farbe": s.get("farbe"),
            "aktiv": s.get("aktiv", True),
            "zusatzfelder": s.get("zusatzfelder") or {},
            "statistik": {k: _jsonable(v) for k, v in (sec.get("stats") or {}).items()},
            "zaehler": sec.get("meters") or [],
            "tarife": sec.get("tariffs") or [],
            "ablesungen": [_reading_json(e, derived) for e in sec["enriched"]],
        })
    text = json.dumps(doc, ensure_ascii=False, indent=2 if pretty else None,
                      default=_jsonable)
    return text.encode("utf-8")
