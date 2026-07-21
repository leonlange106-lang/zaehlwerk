"""Zwei-Faktor (TOTP, RFC 6238) und die verschlüsselte Ablage der Secrets.

**Warum ein Schlüssel ausserhalb der Datenbank.** Die TOTP-Secrets werden
verschlüsselt gespeichert (Fernet/AES). Der Schlüssel liegt bewusst NICHT in der
SQLite-Datei, sondern daneben in `zaehlwerk.key` (bzw. in der Umgebungsvariable
`ZAEHLWERK_SECRET_KEY`). Grund: Die DB-Sicherungen (`.gz`) werden exportiert und
sind damit potenziell einsehbar – läge der Schlüssel in derselben Datei, wäre
die Verschlüsselung wertlos.

**Folge fürs Wiederherstellen.** Wird eine DB-Sicherung auf eine *fremde*
Instanz (mit anderem Schlüssel) eingespielt, lassen sich die alten TOTP-Secrets
nicht entschlüsseln – die betroffenen Nutzer richten 2FA dann neu ein. Auf
derselben Instanz (gleicher Schlüssel, persistentes Volume) funktioniert alles
unverändert weiter.
"""
from __future__ import annotations

import base64
import io
import logging
import os
from pathlib import Path
from typing import Optional

import pyotp
import qrcode
import qrcode.image.svg
from cryptography.fernet import Fernet, InvalidToken

from .config import settings

log = logging.getLogger("zaehlwerk.twofactor")

ISSUER = "Zählwerk"
KEY_ENV = "ZAEHLWERK_SECRET_KEY"

_fernet: Optional[Fernet] = None


def _key_path() -> Path:
    """Schlüsseldatei neben der Datenbank – also im selben persistenten Ort."""
    return Path(settings.sqlite_path).parent / "zaehlwerk.key"


def _load_fernet() -> Fernet:
    """Fernet-Instanz, einmal erzeugt und gecacht. Schlüsselquelle:
    ENV `ZAEHLWERK_SECRET_KEY` hat Vorrang, sonst die Datei; existiert keine,
    wird ein Schlüssel erzeugt und (nur für den Eigentümer lesbar) abgelegt."""
    global _fernet
    if _fernet is not None:
        return _fernet

    env_key = os.environ.get(KEY_ENV)
    if env_key:
        _fernet = Fernet(env_key.encode() if isinstance(env_key, str) else env_key)
        return _fernet

    path = _key_path()
    if path.exists():
        key = path.read_bytes().strip()
    else:
        key = Fernet.generate_key()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(key)
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
        log.info("Neuen Verschlüsselungsschlüssel erzeugt: %s", path)
    _fernet = Fernet(key)
    return _fernet


# --------------------------------------------------------------------------
# Verschlüsselung der Secrets
# --------------------------------------------------------------------------
def encrypt(plaintext: str) -> str:
    return _load_fernet().encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt(token: Optional[str]) -> Optional[str]:
    """Entschlüsselt; gibt None zurück, wenn das nicht möglich ist (leer, oder
    mit einem anderen Schlüssel verschlüsselt – z. B. nach dem Einspielen einer
    fremden Sicherung). Der Aufrufer behandelt None wie 'kein 2FA-Secret'."""
    if not token:
        return None
    try:
        return _load_fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError, TypeError):
        return None


# --------------------------------------------------------------------------
# TOTP
# --------------------------------------------------------------------------
def generate_secret() -> str:
    """Neues Base32-Secret (kompatibel mit gängigen Authenticator-Apps)."""
    return pyotp.random_base32()


def otpauth_uri(secret: str, username: str) -> str:
    return pyotp.totp.TOTP(secret).provisioning_uri(name=username, issuer_name=ISSUER)


def qr_data_uri(uri: str) -> str:
    """QR-Code als SVG-Data-URI. SVG statt PNG, weil das ohne Pillow-Rendering
    auskommt und im Frontend ohne externe Bibliothek (offline) anzeigbar ist."""
    img = qrcode.make(uri, image_factory=qrcode.image.svg.SvgPathImage, box_size=10, border=2)
    buf = io.BytesIO()
    img.save(buf)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/svg+xml;base64,{b64}"


def verify(secret: Optional[str], code: str) -> bool:
    """Prüft einen 6-stelligen Code. `valid_window=1` erlaubt ±30 s Drift –
    genug gegen unsaubere Uhren, ohne das Zeitfenster unnötig zu weiten."""
    if not secret or not code:
        return False
    code = code.strip().replace(" ", "")
    try:
        return pyotp.TOTP(secret).verify(code, valid_window=1)
    except Exception:  # noqa: BLE001 – ungültige Eingaben gelten als 'falsch'
        return False
