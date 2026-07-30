from decimal import Decimal
from unittest.mock import patch
from app.services.checkin import CheckinResult
from app.tts import anons_metni, imzala, dogrula, uret

def R(status, ok=False, ad=None, bal=None):
    return CheckinResult(ok=ok, status=status, message="",
                         ad_soyad=ad, balance=bal)

def test_anons_onay():
    r = R("onay", ok=True, ad="Ali Veli", bal=Decimal("375.00"))
    assert anons_metni(r) == "Afiyet olsun Ali Veli. Kalan bakiyeniz 375 lira."

def test_anons_yetersiz_ve_mukerrer():
    assert anons_metni(R("yetersiz_bakiye", ad="Ayşe")) == "Ayşe, bakiyeniz yetersiz."
    assert anons_metni(R("mukerrer", ad="Can")) == "Can, bugün zaten giriş yaptınız."
    assert anons_metni(R("yetersiz_bakiye")) == "Bakiyeniz yetersiz."

def test_anons_sabitler():
    assert anons_metni(R("suresi_dolmus")) == "QR kodun süresi dolmuş, lütfen yenileyin."
    assert anons_metni(R("gecersiz")) == "Geçersiz QR kodu."
    assert anons_metni(R("hesap_pasif")) == "Hesabınız pasif durumda."

def test_saat_okunusu():
    from datetime import time as t
    from app.tts import saat_okunusu
    assert saat_okunusu(t(12, 0)) == "on iki"
    assert saat_okunusu(t(13, 30)) == "on üç otuz"
    assert saat_okunusu(t(9, 15)) == "dokuz on beş"
    assert saat_okunusu(t(0, 5)) == "sıfır beş"

def test_anons_saat_disi():
    from datetime import time as t
    r = R("saat_disi")
    assert anons_metni(r) == "Yemekhane şu an kapalı."
    assert anons_metni(r, saatler=(t(12, 0), t(13, 30))) == \
        "Yemekhane şu an kapalı. Servis saatleri on iki, on üç otuz arasıdır."

def test_imza_dogrulama():
    s = imzala("merhaba")
    assert dogrula("merhaba", s)
    assert not dogrula("merhaba", s + "x")
    assert not dogrula("baska", s)

def test_imza_noktali_metin_roundtrip():
    t = "Afiyet olsun Ali. Kalan bakiyeniz 375 lira."
    assert dogrula(t, imzala(t))

def test_imza_nokta_kaydirma_reddedilir():
    # T="A.B" icin gecerli imza, text="A", sig="B."+imza olarak sunulamaz
    s = imzala("A.B")
    assert not dogrula("A", "B." + s)

class FakeVoice:
    """PiperVoice yerine: synthesize_wav cagrilarini sayar."""
    def __init__(self, fail=False):
        self.calls = 0
        self.fail = fail

    def synthesize_wav(self, text, wf):
        self.calls += 1
        if self.fail:
            # kismi cikti yazip patla (wave header'i yazilmis olur)
            raise RuntimeError("sentez hatasi")
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(22050)
        wf.writeframes(b"\x00\x00" * 100)

def test_uret_cache(tmp_path, monkeypatch):
    monkeypatch.setattr("app.tts.CACHE_DIR", tmp_path)
    fake = FakeVoice()
    monkeypatch.setattr("app.tts._get_voice", lambda: fake)
    p1 = uret("test metni")
    p2 = uret("test metni")
    assert p1 == p2 and p1.exists()
    assert fake.calls == 1  # ikinci cagri cache'ten

def test_uret_hata_cache_zehirlemez(tmp_path, monkeypatch):
    monkeypatch.setattr("app.tts.CACHE_DIR", tmp_path)
    monkeypatch.setattr("app.tts._get_voice", lambda: FakeVoice(fail=True))
    import pytest as pt
    with pt.raises(Exception):
        uret("hatali metin")
    assert list(tmp_path.iterdir()) == []  # ne .wav ne .tmp kalmali
    # retry basarili fake ile calisir
    monkeypatch.setattr("app.tts._get_voice", lambda: FakeVoice())
    p = uret("hatali metin")
    assert p.exists() and p.suffix == ".wav"
