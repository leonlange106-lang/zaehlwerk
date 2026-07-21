"""Regressionstest: Aussperrung nach Einspielen einer HA-Sicherung.

Aus einem Home-Assistant-Add-on übernommene Konten haben kein lokales Passwort
(`password_hash = None`) - dort meldet der Supervisor an. Wird eine solche
Sicherung in eine Standalone-Instanz eingespielt, existieren zwar Konten, aber
keines kann sich lokal anmelden. Vor dem Fix blieb die Instanz dauerhaft
ausgesperrt: `setup_required` prüfte nur `user_count == 0`, sah die HA-Konten
und bot deshalb keine Ersteinrichtung an - während zugleich niemand ein
Passwort hatte.
"""
from conftest import ADMIN
from sqlmodel import Session, select

from app import auth
from app.database import engine
from app.models import User


def test_setup_recovery_when_no_local_login(client):
    # HA-Zustand nachstellen: alle vorhandenen Konten verlieren ihr Passwort.
    with Session(engine) as s:
        users = s.exec(select(User)).all()
        original = {u.id: u.password_hash for u in users}
        for u in users:
            u.password_hash = None
            s.add(u)
        s.commit()

    try:
        # Ohne anmeldbares Konto muss die Einrichtung wieder greifen - und als
        # Wiederherstellungsfall gekennzeichnet sein (Konten sind ja vorhanden).
        with Session(engine) as s:
            assert auth.local_login_available(s) is False
            assert auth.setup_required(s) is True

        st = client.get("/api/auth/status").json()
        assert st["setup_required"] is True
        assert st["recovery"] is True

        # Einrichtung eines dezentralen Administrators muss jetzt zulässig sein.
        r = client.post("/api/auth/setup", json={
            "username": "recovery-admin", "password": "recovery-passwort-123"})
        assert r.status_code == 200, r.text

        with Session(engine) as s:
            assert auth.local_login_available(s) is True

        # Sobald ein anmeldbares Konto existiert, ist der Endpunkt wieder zu.
        r2 = client.post("/api/auth/setup", json={
            "username": "zweiter-admin", "password": "noch-ein-passwort-1"})
        assert r2.status_code == 409
    finally:
        # Aufräumen: der DB-Zustand ist session-weit. Wiederherstellungskonto
        # entfernen, Originalpasswörter zurückspielen, Client neu anmelden.
        with Session(engine) as s:
            for name in ("recovery-admin", "zweiter-admin"):
                rec = s.exec(select(User).where(User.username == name)).first()
                if rec:
                    s.delete(rec)
            for u in s.exec(select(User)).all():
                if u.id in original:
                    u.password_hash = original[u.id]
                    s.add(u)
            s.commit()
        client.post("/api/auth/login", json=ADMIN)


def test_adopt_existing_account_by_username(client):
    """Vergibt der Nutzer bei der Wiederherstellung denselben Benutzernamen wie
    das passwortlose (HA-)Konto, wird dieses übernommen statt dupliziert."""
    with Session(engine) as s:
        users = s.exec(select(User)).all()
        original = {u.id: u.password_hash for u in users}
        # Genau ein bekanntes, passwortloses Konto herstellen.
        target_name = "adopt-me"
        existing = s.exec(select(User).where(User.username == target_name)).first()
        if not existing:
            s.add(User(username=target_name, display_name="Adopt",
                       password_hash=None, role="admin", is_admin=True))
        for u in users:
            u.password_hash = None
            s.add(u)
        s.commit()

    try:
        before = None
        with Session(engine) as s:
            before = len(s.exec(select(User)).all())

        r = client.post("/api/auth/setup", json={
            "username": "adopt-me", "password": "adoptiertes-passwort-1"})
        assert r.status_code == 200, r.text

        with Session(engine) as s:
            after = s.exec(select(User)).all()
            # Kein zusätzliches Konto - das bestehende wurde übernommen.
            assert len(after) == before
            adopted = next(u for u in after if u.username == "adopt-me")
            assert adopted.password_hash is not None
            assert adopted.aktiv is True
    finally:
        with Session(engine) as s:
            for u in s.exec(select(User)).all():
                if u.username == "adopt-me" and u.id not in original:
                    s.delete(u)
                elif u.id in original:
                    u.password_hash = original[u.id]
                    s.add(u)
            s.commit()
        client.post("/api/auth/login", json=ADMIN)
