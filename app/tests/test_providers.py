from decimal import Decimal

import pytest


# --- DemoPos ---

def test_demopos_4242_onaylanir():
    from app.providers.payment import DemoPos, OdemeSonucu
    sonuc = DemoPos().dogrula("4242424242424242", Decimal("50.00"), "ref-1")
    assert isinstance(sonuc, OdemeSonucu)
    assert sonuc.basarili is True
    assert sonuc.ref == "ref-1"
    assert sonuc.mesaj == "Onaylandı"


def test_demopos_4000_reddedilir():
    from app.providers.payment import DemoPos
    sonuc = DemoPos().dogrula("4000000000000002", Decimal("50.00"), "ref-2")
    assert sonuc.basarili is False
    assert sonuc.ref == "ref-2"
    assert sonuc.mesaj == "Kart reddedildi"


def test_demopos_bosluklu_kart_no():
    from app.providers.payment import DemoPos
    sonuc = DemoPos().dogrula("4242 4242 4242 4242", Decimal("10.00"), "ref-3")
    assert sonuc.basarili is True


# --- Factory'ler ---

def test_get_sms_provider_demo():
    from app.providers.messaging import DemoMessageProvider, get_sms_provider
    provider = get_sms_provider()
    assert isinstance(provider, DemoMessageProvider)
    # gonder hicbir sey yapmaz, hata da firlatmaz
    provider.gonder("05551234567", "123456")


def test_get_mail_provider_demo():
    from app.providers.messaging import DemoMessageProvider, get_mail_provider
    provider = get_mail_provider()
    assert isinstance(provider, DemoMessageProvider)


def test_get_payment_provider_demo():
    from app.providers.payment import DemoPos, get_payment_provider
    provider = get_payment_provider()
    assert isinstance(provider, DemoPos)


def test_bilinmeyen_provider_valueerror(monkeypatch):
    from app.config import settings
    from app.providers.messaging import get_mail_provider, get_sms_provider
    from app.providers.payment import get_payment_provider

    monkeypatch.setattr(settings, "sms_provider", "netgsm")
    monkeypatch.setattr(settings, "mail_provider", "smtp")
    monkeypatch.setattr(settings, "payment_provider", "iyzico")

    with pytest.raises(ValueError):
        get_sms_provider()
    with pytest.raises(ValueError):
        get_mail_provider()
    with pytest.raises(ValueError):
        get_payment_provider()
