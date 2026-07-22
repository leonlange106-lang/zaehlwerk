"""Vertragsunterlagen zu Tarifen: Ablage, Textauszug und Feld-Vorschläge.

Die Datei wird lokal neben der Datenbank abgelegt (kein fremder Speicher nötig;
funktioniert auch offline). Für die Autofüllung wird Text gewonnen –
- aus PDFs mit Textebene direkt (PyMuPDF, keine OCR nötig),
- aus Bildern (und Scan-PDFs) über die vorhandene Tesseract-Pipeline (app/ocr.py)
– und daraus per Mustererkennung Anbieter, Arbeits-/Grundpreis, Laufzeit und
Kündigungsfrist geschätzt. Alle Vorschläge sind unverbindlich; die Weboberfläche
zeigt sie in einem Korrekturformular.
"""
from __future__ import annotations

import logging
import re
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from .config import settings

log = logging.getLogger("zaehlwerk.tariffdocs")

ALLOWED_TYPES = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/heic": ".heic",
    "image/heif": ".heif",
}
MAX_UPLOAD_BYTES = 20 * 1024 * 1024


def storage_dir() -> Path:
    """Ablageort: <db-Verzeichnis>/uploads/tariffs. Wird bei Bedarf angelegt."""
    base = Path(settings.sqlite_path).resolve().parent / "uploads" / "tariffs"
    base.mkdir(parents=True, exist_ok=True)
    return base


def save_document(data: bytes, content_type: str) -> tuple[str, str]:
    """Speichert die Datei und gibt (dateiname, abruf-url) zurück."""
    ext = ALLOWED_TYPES.get(content_type, "")
    if not ext:
        raise ValueError("Nicht unterstützter Dateityp")
    name = f"{uuid.uuid4().hex}{ext}"
    (storage_dir() / name).write_bytes(data)
    return name, f"/api/tariffs/documents/{name}"


def document_path(name: str) -> Optional[Path]:
    """Sicherer Pfad zu einer abgelegten Datei (kein Verzeichniswechsel)."""
    if "/" in name or "\\" in name or ".." in name:
        return None
    path = storage_dir() / name
    return path if path.is_file() else None


# --------------------------------------------------------------------------
# Textgewinnung
# --------------------------------------------------------------------------
def extract_text(data: bytes, content_type: str) -> tuple[str, bool]:
    """Text aus PDF (Textebene, sonst OCR der Seiten) oder Bild (OCR).
    Rückgabe: (text, ocr_verfügbar)."""
    if content_type == "application/pdf":
        return _pdf_text(data)
    # Bild -> vorhandene OCR-Pipeline
    return _image_text(data)


def _pdf_text(data: bytes) -> tuple[str, bool]:
    try:
        import fitz  # PyMuPDF
    except ImportError:
        log.info("PyMuPDF fehlt – PDF-Autofüllung übersprungen")
        return "", False
    text_parts: list[str] = []
    try:
        with fitz.open(stream=data, filetype="pdf") as doc:
            for page in doc:
                text_parts.append(page.get_text())
            joined = "\n".join(text_parts).strip()
            if len(joined) >= 40:
                return joined, True
            # Kaum Text -> vermutlich Scan: erste Seiten rendern und OCRn.
            images = []
            for page in doc[:3]:
                pix = page.get_pixmap(dpi=150)
                images.append(pix.tobytes("png"))
    except Exception as exc:  # noqa: BLE001
        log.warning("PDF nicht lesbar: %s", exc)
        return "", True
    ocr_parts = []
    for img in images:
        t, ok = _image_text(img)
        if not ok:
            return "", False
        ocr_parts.append(t)
    return "\n".join(ocr_parts).strip(), True


def _image_text(data: bytes) -> tuple[str, bool]:
    from . import ocr
    ok, _missing = ocr.deps_available()
    if not ok:
        return "", False
    try:
        variants = ocr.preprocess(data)
        results = ocr.run_tesseract(variants, lang="deu")
    except Exception as exc:  # noqa: BLE001
        log.warning("Bild-OCR fehlgeschlagen: %s", exc)
        return "", True
    if not results:
        return "", True
    # Variante mit der meisten Sicherheit gewinnt.
    best = max(results, key=lambda r: r.get("confidence", 0))
    return best.get("text", ""), True


# --------------------------------------------------------------------------
# Feld-Erkennung
# --------------------------------------------------------------------------
_NUM = r"(\d{1,3}(?:[.,]\d+)?)"

# Arbeitspreis: meist in ct/kWh; €/kWh kommt vor. Wir liefern €/Einheit.
_ARBEITSPREIS_CT = re.compile(rf"Arbeitspreis[^0-9]{{0,40}}{_NUM}\s*(?:ct|cent)", re.I)
_ARBEITSPREIS_EUR = re.compile(rf"Arbeitspreis[^0-9]{{0,40}}{_NUM}\s*(?:€|EUR)\s*/?\s*kWh", re.I)
_GENERIC_CT_KWH = re.compile(rf"{_NUM}\s*(?:ct|cent)\s*/?\s*kWh", re.I)
# Grundpreis: €/Monat oder €/Jahr. Zielgröße ist €/Jahr.
_GRUND_MONAT = re.compile(rf"Grundpreis[^0-9]{{0,40}}{_NUM}\s*(?:€|EUR)?\s*/?\s*Monat", re.I)
_GRUND_JAHR = re.compile(rf"Grundpreis[^0-9]{{0,40}}{_NUM}\s*(?:€|EUR)?\s*/?\s*Jahr", re.I)
_KUENDIGUNG_MONAT = re.compile(rf"K[üu]ndigungsfrist[^0-9]{{0,30}}{_NUM}\s*Monat", re.I)
_KUENDIGUNG_WOCHE = re.compile(rf"K[üu]ndigungsfrist[^0-9]{{0,30}}{_NUM}\s*Woche", re.I)
_DATE = re.compile(r"(\d{1,2})[.\-/](\d{1,2})[.\-/](\d{2,4})")
_ANBIETER_HINTS = [
    "eprimo", "vattenfall", "eon", "e.on", "enbw", "rwe", "yello", "lichtblick",
    "stadtwerke", "montana", "grünwelt", "gruenwelt", "octopus", "1&1", "maingau",
    "naturstrom", "ewe", "innogy", "gasag", "n-ergo", "süwag", "suewag",
]


def _to_float(raw: str) -> Optional[float]:
    try:
        return float(raw.replace(".", "").replace(",", ".")) if "," in raw else float(raw)
    except ValueError:
        return None


def _parse_date(m: re.Match) -> Optional[date]:
    try:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if y < 100:
            y += 2000
        return date(y, mo, d)
    except (ValueError, TypeError):
        return None


def extract_fields(text: str) -> dict:
    """Beste-Aufwand-Schätzung der Tariffelder aus dem Text. Nie ein Fehler –
    fehlende Felder bleiben None."""
    out: dict = {}
    if not text:
        return out
    low = text.lower()

    # Arbeitspreis -> €/kWh
    if (m := _ARBEITSPREIS_EUR.search(text)):
        out["arbeitspreis"] = _to_float(m.group(1))
    elif (m := _ARBEITSPREIS_CT.search(text)):
        v = _to_float(m.group(1))
        out["arbeitspreis"] = round(v / 100, 4) if v is not None else None
    elif (m := _GENERIC_CT_KWH.search(text)):
        v = _to_float(m.group(1))
        out["arbeitspreis"] = round(v / 100, 4) if v is not None else None

    # Grundpreis -> €/Jahr
    if (m := _GRUND_JAHR.search(text)):
        out["grundpreis"] = _to_float(m.group(1))
    elif (m := _GRUND_MONAT.search(text)):
        v = _to_float(m.group(1))
        out["grundpreis"] = round(v * 12, 2) if v is not None else None

    # Kündigungsfrist -> Tage
    if (m := _KUENDIGUNG_MONAT.search(text)):
        v = _to_float(m.group(1))
        out["notice_period_days"] = int(round(v * 30)) if v is not None else None
    elif (m := _KUENDIGUNG_WOCHE.search(text)):
        v = _to_float(m.group(1))
        out["notice_period_days"] = int(round(v * 7)) if v is not None else None

    # Anbieter – mit Wortgrenzen, sonst träfe "rwe" in „verwertbares".
    for hint in _ANBIETER_HINTS:
        if re.search(rf"(?<![a-zäöü0-9]){re.escape(hint)}(?![a-zäöü0-9])", low):
            out["anbieter"] = hint.title().replace("E.On", "E.ON")
            break

    # Laufzeit: erstes Datum = Beginn, letztes = Ende (grobe Heuristik).
    dates = [d for d in (_parse_date(m) for m in _DATE.finditer(text)) if d]
    dates = [d for d in dates if 2000 <= d.year <= 2100]
    if dates:
        out["gueltig_ab"] = min(dates)
        if len(dates) > 1 and max(dates) != min(dates):
            out["gueltig_bis"] = max(dates)

    # Nur sinnvolle Werte behalten.
    if out.get("arbeitspreis") is not None and not (0 < out["arbeitspreis"] <= 100):
        out.pop("arbeitspreis")
    if out.get("grundpreis") is not None and not (0 <= out["grundpreis"] <= 5000):
        out.pop("grundpreis")
    return out


# --------------------------------------------------------------------------
# Vertragsende-Berechnung (für Cron + Endpunkt)
# --------------------------------------------------------------------------
def notice_deadline(gueltig_bis: Optional[date], notice_period_days: Optional[int]) -> Optional[date]:
    from datetime import timedelta
    if not gueltig_bis or not notice_period_days:
        return None
    return gueltig_bis - timedelta(days=notice_period_days)


def _naive_today() -> date:
    return datetime.utcnow().date()
