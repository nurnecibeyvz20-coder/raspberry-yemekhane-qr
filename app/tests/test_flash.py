from app.flash import set_flash, get_flash
from fastapi import Response, Request

def make_request_with_cookie(value):
    scope = {"type": "http", "headers": [
        (b"cookie", f"flash={value}".encode())]}
    return Request(scope)

def test_flash_roundtrip():
    resp = Response()
    set_flash(resp, "Kayıt eklendi", "basari")
    cookie = resp.headers["set-cookie"]
    value = cookie.split("flash=")[1].split(";")[0]
    req = make_request_with_cookie(value)
    f = get_flash(req)
    assert f == {"mesaj": "Kayıt eklendi", "tur": "basari"}

def test_flash_tampered_returns_none():
    req = make_request_with_cookie("sahte-deger")
    assert get_flash(req) is None

def test_flash_missing_returns_none():
    req = Request({"type": "http", "headers": []})
    assert get_flash(req) is None
