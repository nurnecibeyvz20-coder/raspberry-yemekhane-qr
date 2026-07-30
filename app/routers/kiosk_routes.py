import socket
import struct

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db import get_db
from app.deps import templates
from app.services.checkin import process_checkin
from app.tts import anons_metni, dogrula, imzala, uret

router = APIRouter()

_UNSET = object()
_cached_gateway = _UNSET

def _gateway_ip():
    """Docker bridge default gateway IP'sini döndürür (Linux), yoksa None.

    Host makineden docker-proxy üzerinden gelen bağlantılar bridge gateway
    IP'siyle görünür; bu IP kiosk (host) makinesinin kendisidir.
    """
    global _cached_gateway
    if _cached_gateway is _UNSET:
        _cached_gateway = _read_default_gateway()
    return _cached_gateway

def _read_default_gateway():
    try:
        with open("/proc/net/route") as f:
            for line in f.readlines()[1:]:
                fields = line.split()
                if len(fields) >= 3 and fields[1] == "00000000":
                    return socket.inet_ntoa(struct.pack("<L", int(fields[2], 16)))
    except (OSError, ValueError, struct.error):
        pass
    return None

def localhost_only(request: Request):
    host = request.client.host if request.client else ""
    if host in ("127.0.0.1", "::1", "localhost"):
        return
    gateway = _gateway_ip()
    if gateway is not None and host == gateway:
        return
    raise HTTPException(status_code=403, detail="Yalnız kiosk")

class CheckinBody(BaseModel):
    token: str

@router.get("/kiosk", dependencies=[Depends(localhost_only)])
def kiosk_page(request: Request):
    return templates.TemplateResponse(request, "kiosk.html", {})

@router.post("/api/checkin", dependencies=[Depends(localhost_only)])
def checkin(body: CheckinBody, db: Session = Depends(get_db)):
    r = process_checkin(db, body.token)
    metin = anons_metni(r)
    return {"ok": r.ok, "status": r.status, "message": r.message,
            "ad_soyad": r.ad_soyad,
            "balance": str(r.balance) if r.balance is not None else None,
            "anons": {"text": metin, "sig": imzala(metin)}}

@router.get("/api/tts", dependencies=[Depends(localhost_only)])
def tts_endpoint(text: str, sig: str):
    try:
        ok = dogrula(text, sig)
    except TypeError:
        ok = False
    if not ok:
        raise HTTPException(400, "Geçersiz imza")
    try:
        path = uret(text)
    except Exception:
        raise HTTPException(503, "Ses üretilemedi")
    return FileResponse(path, media_type="audio/wav")
