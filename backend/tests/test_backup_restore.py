"""Regressionstest: Wiederherstellung muss die alte Sitzung sauber beenden.

Hintergrund: die wiederhergestellte Datenbank bringt ihren eigenen JWT-
Signaturschlüssel mit (app_settings.auth_jwt_secret). Das im Browser noch
vorhandene Sitzungscookie ist danach ungültig. Ohne explizites Löschen lief
der nächste - vom Frontend automatisch ausgelöste - Aufruf in einen stillen
401, den die Oberfläche fälschlich als "Wiederherstellung fehlgeschlagen"
meldete, obwohl die Wiederherstellung erfolgreich war. Dieser Test prüft die
serverseitige Absicherung: die Antwort auf eine erfolgreiche Wiederherstellung
muss das Sitzungscookie explizit löschen.
"""
from conftest import ADMIN


def test_restore_clears_session_cookie(client):
    # Sicherung vom aktuellen (gültigen) Stand erzeugen.
    run = client.post("/api/backup/run")
    assert run.status_code == 200
    filename = run.json()["file"]

    try:
        resp = client.post(f"/api/backup/restore/{filename}")
        assert resp.status_code == 200
        assert resp.json()["restored_from"] == filename

        # Das Backend muss das Sitzungscookie aktiv löschen (Max-Age=0),
        # statt es dem Client zu überlassen, das erst beim nächsten
        # fehlschlagenden Aufruf zu bemerken.
        set_cookie = resp.headers.get("set-cookie", "")
        assert "zw_session=" in set_cookie
        assert "Max-Age=0" in set_cookie or "max-age=0" in set_cookie.lower()
    finally:
        # Freundlich zu nachfolgenden Tests: der session-weite Client soll
        # angemeldet bleiben, unabhängig von der Reihenfolge der Testläufe.
        client.post("/api/auth/login", json=ADMIN)
        client.delete(f"/api/backup/{filename}")
