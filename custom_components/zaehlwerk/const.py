"""Konstanten der Zählwerk-Integration."""
from datetime import timedelta

DOMAIN = "zaehlwerk"

# Betriebsmodus: der Umschalter, um den es im Umzug geht.
#   intern    -> Zählwerk läuft noch als Add-on in DIESER HA-Instanz.
#   dezentral -> Zählwerk läuft ausgelagert (eigene VM/LXC), über URL erreichbar.
# Beide Modi sprechen dieselbe REST-API; der Modus setzt nur sinnvolle
# Vorgaben (lokale URL vs. externe URL, optionale Cloudflare-Access-Header).
MODE_INTERN = "intern"
MODE_DEZENTRAL = "dezentral"
MODES = [MODE_INTERN, MODE_DEZENTRAL]

CONF_MODE = "mode"
CONF_URL = "url"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_VERIFY_SSL = "verify_ssl"
# Cloudflare Access Service-Token (nur dezentral, optional): schützt die Origin,
# bevor eine Anfrage sie erreicht. Leer lassen, wenn kein Access davor sitzt.
CONF_CF_CLIENT_ID = "cf_access_client_id"
CONF_CF_CLIENT_SECRET = "cf_access_client_secret"

# Vorgabe-URL im internen Modus: der Add-on-Slug ist im HA-Netz auflösbar.
DEFAULT_INTERN_URL = "http://a0d7b954-zaehlwerk:8000"
DEFAULT_SCAN_INTERVAL = timedelta(minutes=5)

# Die MQTT-Ingestion schreibt höchstens eine Ablesung je System und Tag –
# häufiger als alle paar Minuten zu pollen brächte keine neuen Werte.
MIN_SCAN_INTERVAL = timedelta(minutes=1)
