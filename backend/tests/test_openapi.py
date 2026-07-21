"""Die OpenAPI-Dokumentation muss vorhanden, vollständig und erreichbar sein.

FastAPI erzeugt das Schema automatisch. Diese Tests stellen sicher, dass es
nicht versehentlich abgeschaltet oder durch die statische Frontend-Auslieferung
verdeckt wird (der `/`-Mount könnte `/docs` sonst überschatten)."""


def test_openapi_json_served(client):
    r = client.get("/openapi.json")
    assert r.status_code == 200
    schema = r.json()
    assert schema["info"]["title"] == "Zählwerk API"
    assert schema["paths"], "OpenAPI enthält keine Pfade"
    assert "components" in schema and "schemas" in schema["components"]


def test_swagger_and_redoc_reachable(client):
    # Trotz StaticFiles-Mount unter "/" müssen die Doku-Oberflächen erreichbar
    # bleiben – die FastAPI-Routen werden vor dem Mount registriert.
    assert client.get("/docs").status_code == 200
    assert client.get("/redoc").status_code == 200


def test_core_paths_documented(client):
    """Eine Auswahl zentraler Endpunkte muss im Schema stehen. Fehlt einer,
    ist er entweder entfernt oder nicht mehr dokumentiert – beides soll
    auffallen."""
    paths = client.get("/openapi.json").json()["paths"]
    expected = [
        "/api/health",
        "/api/auth/status",
        "/api/systems",
        "/api/systems/{system_id}/readings",
        "/api/systems/{system_id}/dashboard",
        "/api/systems/{system_id}/tariffs",
        "/api/dashboard/data",
        "/api/user/dashboard",
    ]
    missing = [p for p in expected if p not in paths]
    assert not missing, f"Nicht dokumentierte Kern-Endpunkte: {missing}"


def test_every_operation_declares_a_response(client):
    """Jede dokumentierte Operation muss mindestens eine Antwort deklarieren –
    ein Endpunkt ohne beschriebene Antwort ist für einen Client wertlos."""
    paths = client.get("/openapi.json").json()["paths"]
    offenders = []
    for path, methods in paths.items():
        for method, op in methods.items():
            if method not in {"get", "post", "put", "delete", "patch"}:
                continue
            if not op.get("responses"):
                offenders.append(f"{method.upper()} {path}")
    assert not offenders, f"Operationen ohne Antwort-Definition: {offenders}"
