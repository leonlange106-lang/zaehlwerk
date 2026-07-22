"""Strom/Gas/Wasser-Übersichtsbericht im VBA-Excel-Standard (TICKET-3.2).

Medienübergreifende Matrix über die gesamte Historie, in fünf Sichten
(Jahresverbrauch, Verbrauch pro Tag, Kosten pro Tag, Kosten pro Einheit,
Kosten im Jahr) – Layout an die Referenz-PDF angelehnt:

* graue Kopfzeile, fette Datumsspalte
* Zählertausch in Rot in der betroffenen Medienspalte (Gesamt zeigt „–")
* Gas immer mit grauer kWh-Umrechnung (m³ × Brennwert × Zustandszahl)
* pro-Tag-Sichten: graue Anzahl der Intervalltage vor dem Wert
* Kostenwährung nach Jahr: DM bis einschließlich 2001, danach €

Zusätzlich (über die Referenz hinaus) eine Auswertungsseite mit Grafiken:
Gesamtkosten pro Jahr und Kosten je Einheit im Zeitverlauf.

Reines reportlab – keine System-Bibliotheken.
"""
from datetime import date
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Flowable,
)
from reportlab.graphics.shapes import Drawing, Line, PolyLine, String, Circle

GREY = "#9aa0a6"
RED = colors.HexColor("#d0342c")
HEADER_BG = colors.HexColor("#d9d9d9")
INK = colors.HexColor("#1a1a1a")
GRID = colors.HexColor("#e6e6e6")

# Reihenfolge und Standardeinheiten der drei Medien.
MEDIA = ("strom", "gas", "wasser")
MEDIA_LABEL = {"strom": "Strom", "gas": "Gas", "wasser": "Wasser"}


# --------------------------------------------------------------------------
# Formatierung
# --------------------------------------------------------------------------
def de(n: Optional[float], dec: int = 2) -> str:
    """Deutsche Zahlformatierung (Komma, Tausenderpunkt)."""
    if n is None:
        return ""
    s = f"{n:,.{dec}f}"
    return s.replace(",", "␟").replace(".", ",").replace("␟", ".")


def _cur(year: int) -> str:
    return "DM" if year < 2002 else "€"


def _fmt_date(d: date) -> str:
    return d.strftime("%d.%m.%Y")


# --------------------------------------------------------------------------
# Zell-Styles (Rich-Text-Paragraphs für gemischte Farben/Größen)
# --------------------------------------------------------------------------
def _styles():
    cell = ParagraphStyle("cell", fontName="Helvetica", fontSize=8.5, leading=11, textColor=INK)
    date_c = ParagraphStyle("date", parent=cell, fontName="Helvetica-Bold")
    head = ParagraphStyle("head", parent=cell, fontName="Helvetica-Bold", fontSize=8.5)
    bold = ParagraphStyle("bold", parent=cell, fontName="Helvetica-Bold")
    title = ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=15, textColor=INK, spaceAfter=2)
    sub = ParagraphStyle("sub", fontName="Helvetica", fontSize=9, textColor=colors.HexColor("#555"))
    sect = ParagraphStyle("sect", fontName="Helvetica-Bold", fontSize=12, textColor=INK, spaceBefore=2, spaceAfter=4)
    return {"cell": cell, "date": date_c, "head": head, "bold": bold,
            "title": title, "sub": sub, "sect": sect}


def _grey(text: str, size: float = 6.5) -> str:
    return f'<font color="{GREY}" size="{size}">{text}</font>'


def _swap() -> str:
    return f'<font color="#d0342c">Zählertausch</font>'


# --------------------------------------------------------------------------
# Abschnitts-Tabellen
# --------------------------------------------------------------------------
def _table(header: list[str], body_rows: list[list], sty, col_widths, bold_last: bool = False) -> Table:
    head_cells = [Paragraph(h, sty["head"]) for h in header]
    data = [head_cells] + body_rows
    t = Table(data, colWidths=col_widths, repeatRows=1)
    style = [
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 0), (-1, 0), 0.6, colors.HexColor("#b8b8b8")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fafafa")]),
    ]
    t.setStyle(TableStyle(style))
    return t


def _p(html: str, sty) -> Paragraph:
    return Paragraph(html or "", sty["cell"])


def _cell_value(entry, medium: str, gas_factor: float, sty, *, dec: int, per_day: bool,
                with_days: bool) -> Paragraph:
    """Verbrauchszelle (Jahresverbrauch / Verbrauch pro Tag)."""
    if entry is None:
        return _p("", sty)
    if entry.get("meter_replaced"):
        return _p(_swap(), sty)
    val = entry["consumption_per_day"] if per_day else entry.get("consumption")
    if val is None:
        return _p("", sty)
    parts = []
    if with_days and entry.get("days") is not None:
        parts.append(_grey(str(entry["days"])))
    parts.append(de(val, dec))
    if medium == "gas":
        parts.append(_grey(f'({de(val * gas_factor, dec)} kWh)'))
    return _p(" ".join(parts), sty)


def _cell_cost(entry, sty, *, mode: str, with_days: bool) -> Paragraph:
    """Kostenzelle. mode: 'per_day' | 'per_unit' | 'total'."""
    if entry is None:
        return _p("", sty)
    if entry.get("meter_replaced"):
        return _p(_swap(), sty)
    cost = entry.get("cost_effective")
    if cost is None:
        return _p("", sty)
    year = entry["datum"].year
    if mode == "per_day":
        days = entry.get("days")
        val = (cost / days) if days else None
    elif mode == "per_unit":
        cons = entry.get("consumption")
        val = (cost / cons) if cons else None
    else:
        val = cost
    if val is None:
        return _p("", sty)
    parts = []
    if with_days and entry.get("days") is not None:
        parts.append(_grey(str(entry["days"])))
    parts.append(f"{de(val, 2)} {_cur(year)}")
    return _p(" ".join(parts), sty)


def _gesamt(row, sty, *, mode: str) -> Paragraph:
    """Summenspalte über die drei Medien (Kosten pro Tag / im Jahr)."""
    swap = any((row.get(m) or {}).get("meter_replaced") for m in MEDIA)
    if swap:
        return _p('<font color="#d0342c">–</font>', sty)
    total = 0.0
    year = 2002
    found = False
    for m in MEDIA:
        e = row.get(m)
        if not e or e.get("cost_effective") is None:
            continue
        cost = e["cost_effective"]
        year = e["datum"].year
        if mode == "per_day":
            days = e.get("days")
            if days:
                total += cost / days
                found = True
        else:
            total += cost
            found = True
    if not found:
        return _p("", sty)
    return Paragraph(f"{de(total, 2)} {_cur(year)}", sty["bold"])


# --------------------------------------------------------------------------
# Grafiken (Auswertungsseite)
# --------------------------------------------------------------------------
class _LineChart(Flowable):
    """Schlichtes Mehrreihen-Liniendiagramm (Jahr auf X, Wert auf Y)."""

    def __init__(self, title, series, width=170 * mm, height=62 * mm):
        super().__init__()
        self.title = title
        self.series = series  # list of (label, color, [(x_year, y), ...])
        self.width = width
        self.height = height

    def draw(self):
        d = Drawing(self.width, self.height)
        pad_l, pad_b, pad_t = 34, 22, 16
        w, h = self.width, self.height
        xs = [x for _, _, pts in self.series for x, _ in pts]
        ys = [y for _, _, pts in self.series for _, y in pts if y is not None]
        if not xs or not ys:
            self.canv.setFont("Helvetica", 9)
            self.canv.drawString(0, h - 12, self.title)
            return
        xmin, xmax = min(xs), max(xs)
        ymax = max(ys) * 1.1 or 1
        def sx(x): return pad_l + (x - xmin) / max(1, (xmax - xmin)) * (w - pad_l - 8)
        def sy(y): return pad_b + (y / ymax) * (h - pad_b - pad_t)
        d.add(Line(pad_l, pad_b, w - 8, pad_b, strokeColor=colors.HexColor("#cccccc")))
        d.add(Line(pad_l, pad_b, pad_l, h - pad_t, strokeColor=colors.HexColor("#cccccc")))
        for frac in (0.5, 1.0):
            yy = pad_b + frac * (h - pad_b - pad_t)
            d.add(Line(pad_l, yy, w - 8, yy, strokeColor=colors.HexColor("#eeeeee")))
            d.add(String(4, yy - 3, de(ymax * frac, 0), fontName="Helvetica", fontSize=6,
                         fillColor=colors.HexColor("#999999")))
        for label, color, pts in self.series:
            pts = [(x, y) for x, y in pts if y is not None]
            if len(pts) >= 2:
                poly = []
                for x, y in pts:
                    poly.extend([sx(x), sy(y)])
                d.add(PolyLine(poly, strokeColor=colors.HexColor(color), strokeWidth=1.6))
            for x, y in pts:
                d.add(Circle(sx(x), sy(y), 1.6, fillColor=colors.HexColor(color), strokeColor=None))
        d.add(String(sx(xmin), pad_b - 12, str(xmin), fontName="Helvetica", fontSize=6, fillColor=colors.HexColor("#999999")))
        d.add(String(sx(xmax) - 12, pad_b - 12, str(xmax), fontName="Helvetica", fontSize=6, fillColor=colors.HexColor("#999999")))
        d.add(String(pad_l, h - 10, self.title, fontName="Helvetica-Bold", fontSize=9, fillColor=INK))
        lx = pad_l + 4
        for label, color, _ in self.series:
            d.add(Circle(lx, h - 24, 2.4, fillColor=colors.HexColor(color), strokeColor=None))
            d.add(String(lx + 5, h - 27, label, fontName="Helvetica", fontSize=7, fillColor=colors.HexColor("#555")))
            lx += 20 + 4 * len(label)
        d.drawOn(self.canv, 0, 0)


# --------------------------------------------------------------------------
# Aufbau
# --------------------------------------------------------------------------
def build_overview_pdf(rows: list[dict], units: dict, gas_factor: float,
                       stand_label: str) -> bytes:
    import io
    sty = _styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4,
                            leftMargin=14 * mm, rightMargin=14 * mm,
                            topMargin=12 * mm, bottomMargin=12 * mm,
                            title="Strom/Gas/Wasser Übersicht")
    flow: list = []

    # Kopf
    flow.append(Paragraph("Strom/Gas/Wasser Übersicht", sty["title"]))
    flow.append(Paragraph(f"Stand: {stand_label}", sty["sub"]))
    flow.append(Spacer(1, 6))

    cw5 = [30 * mm, 34 * mm, 40 * mm, 34 * mm, 34 * mm]
    cw4 = [30 * mm, 46 * mm, 50 * mm, 46 * mm]

    def date_cell(r):
        return Paragraph(_fmt_date(r["datum"]), sty["date"])

    # 1) Jahresverbrauch
    flow.append(Paragraph("Jahresverbrauch", sty["sect"]))
    header = ["Datum", f"Strom in {units['strom']}", f"Gas in {units['gas']}", f"Wasser in {units['wasser']}"]
    body = [[date_cell(r),
             _cell_value(r.get("strom"), "strom", gas_factor, sty, dec=0, per_day=False, with_days=False),
             _cell_value(r.get("gas"), "gas", gas_factor, sty, dec=0, per_day=False, with_days=False),
             _cell_value(r.get("wasser"), "wasser", gas_factor, sty, dec=0, per_day=False, with_days=False)]
            for r in rows]
    flow.append(_table(header, body, sty, cw4))
    flow.append(PageBreak())

    # 2) Verbrauch pro Tag
    flow.append(Paragraph("Verbrauch pro Tag", sty["sect"]))
    header = ["Datum", f"Strom {units['strom']}/Tag", f"Gas {units['gas']}/Tag", f"Wasser {units['wasser']}/Tag"]
    body = [[date_cell(r),
             _cell_value(r.get("strom"), "strom", gas_factor, sty, dec=2, per_day=True, with_days=True),
             _cell_value(r.get("gas"), "gas", gas_factor, sty, dec=2, per_day=True, with_days=True),
             _cell_value(r.get("wasser"), "wasser", gas_factor, sty, dec=2, per_day=True, with_days=True)]
            for r in rows]
    flow.append(_table(header, body, sty, cw4))
    flow.append(PageBreak())

    # 3) Kosten pro Tag (+ Gesamt)
    flow.append(Paragraph("Kosten pro Tag", sty["sect"]))
    header = ["Datum", "Strom K/Tag", "Gas K/Tag", "Wasser K/Tag", "Gesamt K/Tag"]
    body = [[date_cell(r),
             _cell_cost(r.get("strom"), sty, mode="per_day", with_days=True),
             _cell_cost(r.get("gas"), sty, mode="per_day", with_days=True),
             _cell_cost(r.get("wasser"), sty, mode="per_day", with_days=True),
             _gesamt(r, sty, mode="per_day")]
            for r in rows]
    flow.append(_table(header, body, sty, cw5, bold_last=True))
    flow.append(PageBreak())

    # 4) Kosten pro Einheit
    flow.append(Paragraph("Kosten pro Einheit", sty["sect"]))
    header = ["Datum", f"Strom K/{units['strom']}", f"Gas K/{units['gas']}", f"Wasser K/{units['wasser']}"]
    body = [[date_cell(r),
             _cell_cost(r.get("strom"), sty, mode="per_unit", with_days=False),
             _cell_cost(r.get("gas"), sty, mode="per_unit", with_days=False),
             _cell_cost(r.get("wasser"), sty, mode="per_unit", with_days=False)]
            for r in rows]
    flow.append(_table(header, body, sty, cw4))
    flow.append(PageBreak())

    # 5) Kosten im Jahr (+ Gesamt)
    flow.append(Paragraph("Kosten im Jahr", sty["sect"]))
    header = ["Datum", "Strom", "Gas", "Wasser", "Gesamt"]
    body = [[date_cell(r),
             _cell_cost(r.get("strom"), sty, mode="total", with_days=False),
             _cell_cost(r.get("gas"), sty, mode="total", with_days=False),
             _cell_cost(r.get("wasser"), sty, mode="total", with_days=False),
             _gesamt(r, sty, mode="total")]
            for r in rows]
    flow.append(_table(header, body, sty, cw5, bold_last=True))
    flow.append(PageBreak())

    # 6) Auswertung (Grafiken) – über die Referenz hinaus
    flow.append(Paragraph("Auswertung", sty["sect"]))
    cost_series = []
    for m, color in (("strom", "#f59f00"), ("gas", "#e8590c"), ("wasser", "#1c7ed6")):
        pts = []
        for r in rows:
            e = r.get(m)
            if e and not e.get("meter_replaced") and e.get("cost_effective") is not None:
                pts.append((e["datum"].year, e["cost_effective"]))
        if pts:
            cost_series.append((MEDIA_LABEL[m], color, pts))
    gesamt_pts = []
    for r in rows:
        if any((r.get(m) or {}).get("meter_replaced") for m in MEDIA):
            continue
        s = sum((r.get(m) or {}).get("cost_effective") or 0 for m in MEDIA)
        if s:
            gesamt_pts.append((r["datum"].year, s))
    if gesamt_pts:
        flow.append(_LineChart("Gesamtkosten pro Jahr", [("Gesamt", "#2b8a3e", gesamt_pts)]))
        flow.append(Spacer(1, 8))
    if cost_series:
        flow.append(_LineChart("Kosten pro Jahr je Medium", cost_series))
        flow.append(Spacer(1, 8))
    unit_series = []
    for m, color in (("strom", "#f59f00"), ("gas", "#e8590c"), ("wasser", "#1c7ed6")):
        pts = []
        for r in rows:
            e = r.get(m)
            if e and not e.get("meter_replaced") and e.get("cost_effective") and e.get("consumption"):
                pts.append((e["datum"].year, e["cost_effective"] / e["consumption"]))
        if pts:
            unit_series.append((MEDIA_LABEL[m], color, pts))
    if unit_series:
        flow.append(_LineChart("Kosten je Einheit im Zeitverlauf", unit_series))

    doc.build(flow)
    return buf.getvalue()
