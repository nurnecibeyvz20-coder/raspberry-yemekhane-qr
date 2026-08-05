from datetime import date, time

from app.guest_qr_token import generate_guest_token
from app.models import GuestRequest
from app.services.guest_requests import approve_request, use_guest_qr


def test_approved_guest_qr_consumes_each_meal_right(db_session, monkeypatch):
    from app.models import User
    user = User(sicil_no="guest-owner", ad_soyad="Owner", role="personel", password_hash="x")
    db_session.add(user); db_session.commit()
    request = GuestRequest(owner_id=1, ad="Misafir", soyad="Kişi",
                           telefon="05551234567", ziyaret_nedeni="Ziyaret",
                           ziyaret_tarihi=date.today(), yemek_adedi=2,
                           baslangic_saati=time(0), bitis_saati=time(23, 59))
    request.owner_id = user.id
    db_session.add(request); db_session.commit()
    approve_request(db_session, request, actor_id=1); db_session.commit()
    token = generate_guest_token(request.id, request.qr_secret)
    assert use_guest_qr(db_session, token).ok
    assert use_guest_qr(db_session, token).ok
    assert use_guest_qr(db_session, token).status == "misafir_gecersiz"
