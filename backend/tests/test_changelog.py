"""Changelog-Endpunkt: liefert die aktuelle Version + Verlaufseinträge; die
oberste Version stimmt mit APP_VERSION überein (Sicherheitsnetz gegen einen
vergessenen Eintrag beim Versions-Bump)."""
from app.version import APP_VERSION
from app import changelog as cl


def test_changelog_top_matches_app_version():
    assert cl.LATEST_LOGGED == APP_VERSION
    assert cl.current_matches_changelog()


def test_changelog_endpoint(client):
    r = client.get("/api/changelog")
    assert r.status_code == 200
    body = r.json()
    assert body["current"] == APP_VERSION
    assert body["entries"] and body["entries"][0]["version"] == APP_VERSION
    assert all("changes" in e for e in body["entries"])
