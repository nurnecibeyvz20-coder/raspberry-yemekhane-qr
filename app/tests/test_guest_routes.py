from datetime import date


def _login(client):
    client.post("/login", data={"sicil_no": "1001", "password": "dogru123"})


def test_personnel_creates_pending_guest_request(client, seeded_db):
    _login(client)
    r = client.post("/misafir", data={"ad": "Ayşe", "soyad": "Yılmaz", "telefon": "05551234567",
        "ziyaret_nedeni": "Ziyaret", "ziyaret_tarihi": str(date.today()), "yemek_adedi": "1"}, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/misafir"


def test_guest_page_requires_login(client, seeded_db):
    r = client.get("/misafir", follow_redirects=False)
    assert r.status_code == 303
