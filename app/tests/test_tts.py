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

def test_uret_cache(tmp_path, monkeypatch):
    monkeypatch.setattr("app.tts.CACHE_DIR", tmp_path)
    calls = []
    def fake_run(cmd, **kw):
        calls.append(cmd)
        # piper cikti dosyasini yazmis gibi yap
        from pathlib import Path
        Path(cmd[cmd.index("--output_file") + 1]).write_bytes(b"RIFF")
        class P: returncode = 0
        return P()
    monkeypatch.setattr("app.tts.subprocess.run", fake_run)
    p1 = uret("test metni")
    p2 = uret("test metni")
    assert p1 == p2 and p1.exists()
    assert len(calls) == 1  # ikinci cagri cache'ten

def test_uret_hata_cache_zehirlemez(tmp_path, monkeypatch):
    import subprocess as sp
    monkeypatch.setattr("app.tts.CACHE_DIR", tmp_path)
    def failing_run(cmd, **kw):
        # piper kismi cikti yazip patlar
        from pathlib import Path
        Path(cmd[cmd.index("--output_file") + 1]).write_bytes(b"RI")
        raise sp.CalledProcessError(1, cmd)
    monkeypatch.setattr("app.tts.subprocess.run", failing_run)
    import pytest as pt
    with pt.raises(sp.CalledProcessError):
        uret("hatali metin")
    assert list(tmp_path.iterdir()) == []  # ne .wav ne .tmp kalmali
    # retry basarili fake ile calisir
    def ok_run(cmd, **kw):
        from pathlib import Path
        Path(cmd[cmd.index("--output_file") + 1]).write_bytes(b"RIFF")
        class P: returncode = 0
        return P()
    monkeypatch.setattr("app.tts.subprocess.run", ok_run)
    p = uret("hatali metin")
    assert p.exists() and p.suffix == ".wav"
