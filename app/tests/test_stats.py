from datetime import date
from decimal import Decimal
from app.auth import hash_password
from app.models import User, Transaction, MealEntry, FailedAttempt
from app.services.stats import dashboard_stats, paginate

def make_user(db, sicil, balance="0.00", active=True):
    u = User(sicil_no=sicil, ad_soyad=f"Kisi {sicil}", role="personel",
             password_hash=hash_password("x"),
             balance=Decimal(balance), is_active=active)
    db.add(u); db.commit()
    return u

def test_dashboard_stats_counts(db_session):
    u1 = make_user(db_session, "s1", "300.00")
    u2 = make_user(db_session, "s2", "200.00")
    make_user(db_session, "s3", "999.00", active=False)  # pasif: toplama girmez
    db_session.add(MealEntry(user_id=u1.id, entry_date=date.today()))
    db_session.add(Transaction(user_id=u1.id, type="yemek",
                               amount=Decimal("-125.00"),
                               balance_after=Decimal("175.00")))
    db_session.add(Transaction(user_id=u2.id, type="yukleme",
                               amount=Decimal("200.00"),
                               balance_after=Decimal("200.00")))
    db_session.add(FailedAttempt(raw_qr="x", reason="gecersiz"))
    db_session.commit()
    s = dashboard_stats(db_session)
    assert s["bugun_yiyen"] == 1
    assert s["aktif_personel"] == 2
    assert s["toplam_bakiye"] == Decimal("500.00")
    assert s["bugun_ciro"] == Decimal("125.00")
    assert len(s["son_islemler"]) == 2
    assert len(s["son_hatalar"]) == 1

def test_bekleyen_kodlar_suresi_gecmis_gosterilmez(db_session):
    from datetime import datetime, timedelta
    from app.models import ResetCode
    u = make_user(db_session, "k1")
    simdi = datetime.now()
    db_session.add(ResetCode(user_id=u.id, kod_hash="h1", kanal="sms",
                             demo_gosterim="111111",
                             created_at=simdi - timedelta(minutes=5),
                             expires_at=simdi - timedelta(minutes=1)))
    db_session.add(ResetCode(user_id=u.id, kod_hash="h2", kanal="sms",
                             demo_gosterim="222222",
                             created_at=simdi - timedelta(minutes=2),
                             expires_at=simdi + timedelta(minutes=8)))
    db_session.commit()
    s = dashboard_stats(db_session)
    kodlar = [k["kod"] for k in s["bekleyen_kodlar"]]
    assert "222222" in kodlar
    assert "111111" not in kodlar

def test_paginate_basic(db_session):
    for i in range(120):
        make_user(db_session, f"p{i:03d}")
    q = db_session.query(User).order_by(User.sicil_no)
    p1 = paginate(q, page=1, per_page=50)
    assert p1.total == 120 and p1.pages == 3 and len(p1.items) == 50
    p3 = paginate(q, page=3, per_page=50)
    assert len(p3.items) == 20

def test_paginate_clamps_out_of_range(db_session):
    make_user(db_session, "tek")
    q = db_session.query(User)
    assert paginate(q, page=0).page == 1
    assert paginate(q, page=99).page == 1  # tek sayfa var

def test_paginate_empty(db_session):
    p = paginate(db_session.query(User), page=1)
    assert p.total == 0 and p.pages == 1 and p.items == []
