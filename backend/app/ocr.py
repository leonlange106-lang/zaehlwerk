"""Serverseitige Zählerstand-Erkennung.

**Warum serverseitig.** Bisher lief die Erkennung im Browser über
`tesseract.js`, geladen von einem Auslieferungsnetz. Das scheiterte im
Offline-Modus, brachte keine deutschen Sprachdaten mit und ließ sich nicht
vorverarbeiten. Serverseitig steht OpenCV zur Verfügung, und die letzte
funktionale Abhängigkeit von einem fremden Netz entfällt.

**Der eigentliche Gewinn liegt nicht in Tesseract, sondern davor.** Ein Foto
aus dem Keller ist schief, ungleichmäßig beleuchtet und kontrastarm. Ohne
Vorverarbeitung liefert Tesseract darauf nahezu unbrauchbare Zeichenfolgen.
Die Kette hier erzeugt mehrere Varianten und übernimmt jene mit der höchsten
Zeichensicherheit, statt sich auf eine Einstellung festzulegen.

**Mehrdeutigkeit löst der Vorwert.** Ein Zählerfoto enthält neben dem Zählwerk
oft Seriennummer, Eichjahr und Typenbezeichnung. Welche der erkannten Zahlen
der Zählerstand ist, lässt sich am zuverlässigsten am zuletzt erfassten Wert
entscheiden: der neue Stand liegt darüber und in plausibler Nähe.
"""
import io
import logging
import re
from typing import Optional

log = logging.getLogger("zaehlwerk.ocr")

# Obergrenzen. Ein Foto vom Handy liegt bei 2 bis 8 MB; darüber liegt entweder
# ein Missverständnis oder ein Versuch, den Dienst zu beschäftigen.
MAX_UPLOAD_BYTES = 12 * 1024 * 1024
MAX_PIXELS = 40_000_000          # Schutz vor Dekompressionsbomben
TARGET_WIDTH = 1600              # darüber bringt Tesseract keinen Zugewinn

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}


def deps_available() -> tuple[bool, str]:
    """Sind OpenCV, Pillow und Tesseract vorhanden?"""
    missing = []
    try:
        import cv2  # noqa: F401
    except ImportError:
        missing.append("opencv-python-headless")
    try:
        from PIL import Image  # noqa: F401
    except ImportError:
        missing.append("Pillow")
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
    except ImportError:
        missing.append("pytesseract")
    except Exception:  # noqa: BLE001
        missing.append("tesseract-ocr (Systempaket)")
    return (not missing), ", ".join(missing)


# --------------------------------------------------------------------------
# Vorverarbeitung
# --------------------------------------------------------------------------
def preprocess(data: bytes) -> list[tuple[str, "object"]]:
    """Liefert benannte Bildvarianten, absteigend nach erwarteter Eignung.

    Vier Varianten, weil sich Zählwerke grundlegend unterscheiden:

    * ``adaptive``  Adaptives Schwellwertverfahren. Beste Wahl bei
      ungleichmäßiger Beleuchtung, also bei fast jedem Kellerfoto.
    * ``otsu``      Globaler Schwellwert. Überlegen bei gleichmäßig
      ausgeleuchteten Rollenzählwerken mit klarem Hell-Dunkel-Kontrast.
    * ``inverted``  Wie ``otsu``, aber invertiert – LCD-Anzeigen zeigen helle
      Ziffern auf dunklem Grund, was Tesseract sonst als Rauschen liest.
    * ``clahe``     Nur Kontrastanhebung ohne Binarisierung. Rettet Fälle, in
      denen der Schwellwert Ziffernkanten wegschneidet.
    """
    import cv2
    import numpy as np
    from PIL import Image, ImageOps

    Image.MAX_IMAGE_PIXELS = MAX_PIXELS
    pil = Image.open(io.BytesIO(data))
    # Aufnahmerichtung berücksichtigen: ein hochkant fotografiertes Zählwerk
    # liegt in den Rohdaten quer, und gedrehte Ziffern erkennt Tesseract nicht.
    pil = ImageOps.exif_transpose(pil).convert("RGB")

    img = np.array(pil)[:, :, ::-1]                      # RGB -> BGR
    h, w = img.shape[:2]
    if w > TARGET_WIDTH:
        scale = TARGET_WIDTH / w
        img = cv2.resize(img, (TARGET_WIDTH, int(h * scale)), interpolation=cv2.INTER_AREA)
    elif w < 700:
        # Kleine Aufnahmen hochskalieren: Tesseract braucht rund 30 Pixel
        # Zeichenhöhe, darunter bricht die Erkennung ein.
        scale = 700 / w
        img = cv2.resize(img, (700, int(h * scale)), interpolation=cv2.INTER_CUBIC)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Kantenerhaltende Glättung: entfernt Sensorrauschen, ohne die Ziffern
    # weichzuzeichnen – ein einfacher Weichzeichner täte genau das.
    gray = cv2.bilateralFilter(gray, 7, 55, 55)

    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8)).apply(gray)

    adaptive = cv2.adaptiveThreshold(
        clahe, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 11)
    _, otsu = cv2.threshold(clahe, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    inverted = cv2.bitwise_not(otsu)

    # Feine Lücken in Ziffern schließen, ohne benachbarte zu verbinden.
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
    adaptive = cv2.morphologyEx(adaptive, cv2.MORPH_CLOSE, kernel)

    return [("adaptive", adaptive), ("otsu", otsu),
            ("inverted", inverted), ("clahe", clahe)]


# --------------------------------------------------------------------------
# Texterkennung
# --------------------------------------------------------------------------
# Nur Ziffern und Trennzeichen zulassen. Ohne diese Einschränkung liest
# Tesseract Ziffern regelmäßig als Buchstaben – 0 als O, 1 als I, 5 als S.
TESS_CONFIGS = [
    ("psm7", "--oem 3 --psm 7 -c tessedit_char_whitelist=0123456789.,"),
    ("psm6", "--oem 3 --psm 6 -c tessedit_char_whitelist=0123456789.,"),
    ("psm11", "--oem 3 --psm 11 -c tessedit_char_whitelist=0123456789.,"),
]


def run_tesseract(variants, lang: str = "deu") -> list[dict]:
    """Jede Bildvariante mit jeder Konfiguration lesen."""
    import pytesseract

    results = []
    for vname, image in variants:
        for cname, config in TESS_CONFIGS:
            try:
                data = pytesseract.image_to_data(
                    image, lang=lang, config=config,
                    output_type=pytesseract.Output.DICT)
            except Exception as exc:  # noqa: BLE001
                log.debug("Tesseract %s/%s fehlgeschlagen: %s", vname, cname, exc)
                continue
            words, confs = [], []
            for text, conf in zip(data.get("text", []), data.get("conf", [])):
                text = (text or "").strip()
                try:
                    conf = float(conf)
                except (TypeError, ValueError):
                    conf = -1.0
                if text and conf >= 0:
                    words.append(text)
                    confs.append(conf)
            if not words:
                continue
            results.append({
                "variant": vname, "config": cname,
                "text": " ".join(words),
                "confidence": round(sum(confs) / len(confs), 1),
            })
    return results


# --------------------------------------------------------------------------
# Zahlenextraktion
# --------------------------------------------------------------------------
# Tokenweise statt über den ganzen Text: ein Ausdruck, der Leerzeichen
# einschließt, verbindet benachbarte Zahlen zu einer einzigen. Aus
# "2021 11298.5" würde sonst 20211298.5.
TOKEN_RE = re.compile(r"[\d][\d.,]*")

# OBIS-Kennzahlen stehen auf modernen Zählern direkt neben dem Wert und werden
# sonst als Zählerstand gelesen.
OBIS_RE = re.compile(r"^[12][.,]8[.,][0-9]$")

# Ziffernrollen zerfallen in der Erkennung häufig in Gruppen. Zusammengefasst
# werden nur kurze, reine Ziffergruppen – "2021 11298" bleibt getrennt, weil
# die zweite Gruppe für eine Rolle zu lang ist.
MAX_MERGE_GROUP = 3


def _interpret(token: str) -> list[float]:
    """Zeichenfolge in eine oder zwei plausible Zahlen überführen.

    Der schwierige Teil ist das Trennzeichen, weil Punkt sowohl Dezimal- als
    auch Tausendertrenner sein kann:

    * Mehrere Trenner und alle Folgegruppen genau dreistellig
      (``1.234.567``)  ->  ausschließlich Tausendertrenner.
    * Mehrere Trenner, letzte Gruppe ein- bis zweistellig
      (``1.234,5``)    ->  letzter Trenner ist der Dezimaltrenner.
    * Ein Trenner mit genau drei Folgeziffern (``11.265``) ist echt
      mehrdeutig – 11265 oder 11,265. Beide Lesarten werden zurückgegeben;
      welche gilt, entscheidet später der Vorwert.
    """
    raw = token.strip().strip(".,")
    if not raw or not raw[0].isdigit() or OBIS_RE.match(raw):
        return []

    parts = re.split(r"[.,]", raw)
    if any(not p.isdigit() for p in parts if p):
        return []
    parts = [p for p in parts if p]
    if not parts:
        return []

    if len(parts) == 1:
        return [float(parts[0])]

    head, tail = parts[:-1], parts[-1]
    joined = "".join(parts)

    # Tausendertrennung setzt voraus, dass ALLE Folgegruppen dreistellig sind
    # UND die erste höchstens dreistellig ist. Ohne die zweite Bedingung würde
    # "11265.043" als 11.265.043 gelesen – eine fünfstellige Tausendergruppe
    # gibt es nicht.
    if all(len(p) == 3 for p in parts[1:]) and 1 <= len(parts[0]) <= 3:
        values = [float(joined)]
        # Bei genau einem Trenner bleibt die Dezimallesart möglich
        if len(parts) == 2:
            values.append(float(f"{head[0]}.{tail}"))
        return values

    if 1 <= len(tail) <= 3:
        return [float(f"{''.join(head)}.{tail}")]
    return [float(joined)]


def extract_candidates(text: str) -> list[dict]:
    """Alle plausiblen Zahlen aus einer erkannten Zeichenfolge."""
    tokens = TOKEN_RE.findall(text or "")
    out: list[dict] = []

    def add(raw: str, value: float, digits: int, merged: bool = False):
        # Ein- und zweistellige Funde sind fast immer Eichjahr, Tarifnummer
        # oder Bruchstücke – kein Zählwerk hat weniger als drei Stellen.
        if digits < 3 or value <= 0:
            return
        out.append({"raw": raw, "value": value, "digits": digits, "merged": merged})

    for tok in tokens:
        digits = len(re.sub(r"\D", "", tok))
        for value in _interpret(tok):
            add(tok, value, digits)

    # Zusammenhängende kurze Ziffergruppen zusätzlich als eine Zahl anbieten
    run: list[str] = []
    for tok in tokens + [""]:
        if tok.isdigit() and len(tok) <= MAX_MERGE_GROUP:
            run.append(tok)
            continue
        if len(run) >= 2:
            joined = "".join(run)
            add(" ".join(run), float(joined), len(joined), merged=True)
        run = []

    # Doppelte Werte zusammenführen, längste Ziffernfolge behalten
    best: dict[float, dict] = {}
    for c in out:
        prev = best.get(c["value"])
        if prev is None or c["digits"] > prev["digits"]:
            best[c["value"]] = c
    return sorted(best.values(), key=lambda c: (-c["digits"], -c["value"]))


def pick_best(candidates: list[dict], previous: Optional[float] = None,
              max_factor: float = 3.0) -> Optional[dict]:
    """Den wahrscheinlichsten Zählerstand auswählen.

    Ohne Vorwert bleibt nur die Stellenzahl: das Zählwerk ist üblicherweise die
    längste Ziffernfolge im Bild.

    Mit Vorwert wird deutlich schärfer entschieden. Ein Zählerstand läuft
    aufwärts, springt aber nicht um ein Vielfaches. Kandidaten unterhalb des
    Vorwerts oder oberhalb des Vielfachen entfallen; aus dem Rest gewinnt der
    nächstliegende.
    """
    if not candidates:
        return None

    if previous is None or previous <= 0:
        return sorted(candidates, key=lambda c: (-c["digits"], -c["value"]))[0]

    plausible = [c for c in candidates
                 if previous <= c["value"] <= previous * max_factor]
    if plausible:
        best = min(plausible, key=lambda c: c["value"] - previous)
        return {**best, "matched_previous": True}

    # Nichts passt. Dann nicht die längste Folge nehmen – das wäre bei einem
    # Foto mit Seriennummer regelmäßig die falsche –, sondern die Zahl mit der
    # ähnlichsten Größenordnung. Gekennzeichnet als unplausibel, damit die
    # Oberfläche zur Prüfung auffordert.
    import math
    fallback = min(candidates,
                   key=lambda c: abs(math.log10(c["value"] / previous)))
    return {**fallback, "matched_previous": False}


def analyze(data: bytes, previous: Optional[float] = None,
            lang: str = "deu") -> dict:
    """Gesamter Ablauf: Vorverarbeitung, Erkennung, Auswahl."""
    variants = preprocess(data)
    readings = run_tesseract(variants, lang)
    if not readings:
        return {"value": None, "confidence": 0.0, "candidates": [],
                "attempts": [], "reason": "Keine Zeichen erkannt"}

    # Beste Lesung zuerst bewerten, aber Kandidaten aus ALLEN Durchläufen
    # sammeln: eine Variante mit mittlerer Sicherheit trifft den Zählerstand
    # nicht selten genauer als die formal beste.
    readings.sort(key=lambda r: -r["confidence"])
    seen: dict[float, dict] = {}
    for r in readings:
        for cand in extract_candidates(r["text"]):
            prev = seen.get(cand["value"])
            if prev is None or r["confidence"] > prev["confidence"]:
                seen[cand["value"]] = {**cand, "confidence": r["confidence"],
                                       "variant": r["variant"], "config": r["config"]}

    candidates = sorted(seen.values(), key=lambda c: (-c["digits"], -c["confidence"]))
    best = pick_best(candidates, previous)
    return {
        "value": best["value"] if best else None,
        "confidence": best.get("confidence", 0.0) if best else 0.0,
        "matched_previous": best.get("matched_previous") if best else None,
        "variant": best.get("variant") if best else None,
        "candidates": candidates[:8],
        "attempts": [{"variant": r["variant"], "config": r["config"],
                      "confidence": r["confidence"], "text": r["text"][:120]}
                     for r in readings[:6]],
        "raw_text": readings[0]["text"][:400],
    }
