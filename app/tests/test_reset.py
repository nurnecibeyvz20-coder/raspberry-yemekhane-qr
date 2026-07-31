import hashlib
from datetime import datetime, timedelta

import pytest

from app.auth import hash_password, verify_password
from app.models import ResetCode, User
from app.services.reset import (gizli_dogrula, kanallar, kod_dogrula,
                                kod_talep, normalize, sifre_sifirla)


def _kullanici(db, **kwargs):
    defaults = dict(sicil_no="9001", ad_soyad="Reset Test", role="personel",
                    password_hash=hash_password("eski123"))
    defaults.update(kwargs)
    user = User(**defaults)
    db.add(user)
    db.commit()
    return user


# --- normalize ---

def test_normalize_turkce_kucultme():
    assert normalize("İstanbul") == "istanbul"
    assert normalize("IĞDIR") == "ığdır"


def test_normalize_strip():
    assert normalize("  Ali  ") == "ali"


# --- kanallar ---

def test_kanallar_tum_yontemler(db_session):
    user = _kullanici(
        db_session,
        telefon="05321234512",
        eposta="ali@ornek.com",
        gizli_soru="İlk evcil hayvanınız?",
        gizli_cevap_hash=hash_password(normalize("Boncuk")),
    )
    liste = kanallar(user)
    assert liste == [
        {"kanal": "sms", "maske": "05** *** **12"},
        {"kanal": "eposta", "maske": "a***@o**.com"},
        {"kanal": "gizli_soru", "soru": "İlk evcil hayvanınız?"},
    ]


def test_kanallar_hicbiri_yok(db_session):
    user = _kullanici(db_session)
    assert kanallar(user) == []


# --- kod talep + dogrula ---

def test_kod_talep_ve_dogrula_turu(db_session):
    user = _kullanici(db_session, telefon="05321234512")
    kod = kod_talep(db_session, user, "sms")
    assert kod is not None
    assert len(kod) == 6 and kod.isdigit()

    satir = (db_session.query(ResetCode)
             .filter_by(user_id=user.id).order_by(ResetCode.id.desc()).first())
    assert satir.kanal == "sms"
    assert satir.demo_gosterim == kod  # demo saglayici

    assert kod_dogrula(db_session, user, kod) is True
    # kullanildi; ayni kod tekrar gecmez
    assert kod_dogrula(db_session, user, kod) is False


def test_yanlis_kod_besinci_denemede_iptal(db_session):
    user = _kullanici(db_session, telefon="05321234512")
    kod = kod_talep(db_session, user, "sms")
    for _ in range(5):
        assert kod_dogrula(db_session, user, "000000" if kod != "000000"
                           else "111111") is False
    # 5. denemede kod iptal edildi; dogru kod artik gecmez
    assert kod_dogrula(db_session, user, kod) is False


def test_saatte_uc_talep_siniri(db_session):
    user = _kullanici(db_session, telefon="05321234512")
    for _ in range(3):
        assert kod_talep(db_session, user, "sms") is not None
    assert kod_talep(db_session, user, "sms") is None


def test_suresi_gecmis_kod_reddedilir(db_session):
    user = _kullanici(db_session, telefon="05321234512")
    kod = "123456"
    db_session.add(ResetCode(
        user_id=user.id, kanal="sms",
        kod_hash=hashlib.sha256(f"{user.id}:{kod}".encode()).hexdigest(),
        expires_at=datetime.now() - timedelta(minutes=1),
        created_at=datetime.now(),
    ))
    db_session.commit()
    assert kod_dogrula(db_session, user, kod) is False


# --- gizli soru ---

def test_gizli_dogrula_dogru_ve_yanlis(db_session):
    user = _kullanici(
        db_session,
        gizli_soru="Dogdugunuz sehir?",
        gizli_cevap_hash=hash_password(normalize("İstanbul")),
    )
    assert gizli_dogrula(user, "istanbul") is True
    assert gizli_dogrula(user, "  İstanbul  ") is True
    assert gizli_dogrula(user, "ankara") is False


def test_gizli_dogrula_tanimsiz(db_session):
    user = _kullanici(db_session)
    assert gizli_dogrula(user, "istanbul") is False


# --- sifre sifirla ---

def test_sifre_sifirla_surum_artar_bayrak_temizlenir(db_session):
    user = _kullanici(db_session, must_change_password=True)
    eski_surum = user.session_version
    sifre_sifirla(db_session, user, "yeni12345")
    assert verify_password("yeni12345", user.password_hash)
    assert user.must_change_password is False
    assert user.session_version == eski_surum + 1
