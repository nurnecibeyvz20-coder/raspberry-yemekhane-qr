import pytest
from itsdangerous import URLSafeTimedSerializer
from app.qr_token import generate_token, verify_token, InvalidToken, ExpiredToken

def test_roundtrip():
    t = generate_token(7, "qr-secret")
    assert verify_token(t) == (7, "qr-secret")

def test_tampered_token():
    t = generate_token(7, "qr-secret")
    with pytest.raises(InvalidToken):
        verify_token(t[:-2] + "zz")

def test_expired_token(monkeypatch):
    t = generate_token(7, "qr-secret")
    import app.qr_token as m
    real = m._serializer.loads
    def fake_loads(s, max_age=None):
        return real(s, max_age=-1)  # anında süresi dolmuş say
    monkeypatch.setattr(m._serializer, "loads", fake_loads)
    with pytest.raises(ExpiredToken):
        verify_token(t)

def test_wrong_secret_rejected():
    other = URLSafeTimedSerializer("baska-anahtar", salt="qr-token")
    forged = other.dumps({"uid": 7, "qr": "qr-secret"})
    with pytest.raises(InvalidToken):
        verify_token(forged)


def test_token_requires_qr_secret():
    with pytest.raises(ValueError):
        generate_token(7, "")
