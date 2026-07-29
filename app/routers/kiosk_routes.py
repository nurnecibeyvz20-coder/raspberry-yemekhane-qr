from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db import get_db
from app.deps import templates
from app.services.checkin import process_checkin

router = APIRouter()

def localhost_only(request: Request):
    host = request.client.host if request.client else ""
    if host not in ("127.0.0.1", "::1", "localhost"):
        raise HTTPException(status_code=403, detail="Yalnız kiosk")

class CheckinBody(BaseModel):
    token: str

@router.get("/kiosk", dependencies=[Depends(localhost_only)])
def kiosk_page(request: Request):
    return templates.TemplateResponse(request, "kiosk.html", {})

@router.post("/api/checkin", dependencies=[Depends(localhost_only)])
def checkin(body: CheckinBody, db: Session = Depends(get_db)):
    r = process_checkin(db, body.token)
    return {"ok": r.ok, "status": r.status, "message": r.message,
            "ad_soyad": r.ad_soyad,
            "balance": str(r.balance) if r.balance is not None else None}
