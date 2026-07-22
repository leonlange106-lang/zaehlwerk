"""Manuelle Sortierung (TICKET-4.1): PUT /api/systems/reorder setzt sort_index
in einer Transaktion; die Liste folgt danach der neuen Reihenfolge."""


def test_reorder_changes_order(client):
    ids = []
    for name in ["Zebra", "Alpha", "Mango"]:
        ids.append(client.post("/api/systems", json={"name": name, "typ": "Strom", "einheit": "kWh"}).json()["id"])
    # Neu ordnen: Mango, Zebra, Alpha
    order = [{"id": ids[2], "sort_index": 0}, {"id": ids[0], "sort_index": 1}, {"id": ids[1], "sort_index": 2}]
    r = client.put("/api/systems/reorder", json={"order": order})
    assert r.status_code == 200 and r.json()["reordered"] == 3

    names = [s["name"] for s in client.get("/api/systems").json() if s["id"] in ids]
    assert names == ["Mango", "Zebra", "Alpha"]


def test_reorder_ignores_unknown_ids(client):
    r = client.put("/api/systems/reorder", json={"order": [{"id": "does-not-exist", "sort_index": 5}]})
    assert r.status_code == 200 and r.json()["reordered"] == 0
