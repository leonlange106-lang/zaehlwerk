"""Proxy zur Home-Assistant-API (Supervisor). Nur lesend: aktueller Entity-State."""
import json
import os
import urllib.request

from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["ha"])


@router.get("/api/ha/state/{entity_id}")
def ha_state(entity_id: str):
    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        raise HTTPException(501, "Nur im Home-Assistant-Add-on verfügbar")
    req = urllib.request.Request(
        f"http://supervisor/core/api/states/{entity_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            data = json.loads(r.read())
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"HA/Entity nicht erreichbar: {exc}")
    attrs = data.get("attributes") or {}
    return {
        "entity_id": entity_id,
        "state": data.get("state"),
        "unit": attrs.get("unit_of_measurement"),
        "name": attrs.get("friendly_name"),
    }
