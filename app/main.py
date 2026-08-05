import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import OperationalError

from app.db import SessionLocal
from app.routers import (admin_routes, auth_routes, kiosk_routes,
                          payment_routes, qr_routes)
from app.routers import guest_routes
from app.startup import ensure_initial_admin
from app.tts import preload_voice

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        db = SessionLocal()
        try:
            ensure_initial_admin(db)
        finally:
            db.close()
    except OperationalError:
        pass
    # TTS modelini arka planda yukle (ilk anons ~12 sn gecikmesin)
    threading.Thread(target=preload_voice, daemon=True).start()
    yield

app = FastAPI(title="Yemekhane QR", lifespan=lifespan)
app.mount("/static",
          StaticFiles(directory=str(Path(__file__).resolve().parent / "static")),
          name="static")
app.include_router(auth_routes.router)
app.include_router(admin_routes.router)
app.include_router(qr_routes.router)
app.include_router(kiosk_routes.router)
app.include_router(payment_routes.router)
app.include_router(guest_routes.router)

@app.get("/sw.js", include_in_schema=False)
def service_worker():
    # Kökten servis: SW kök kapsam alır (/static kapsamında kalmasın)
    return FileResponse(
        str(Path(__file__).resolve().parent / "static" / "sw.js"),
        media_type="application/javascript")

@app.get("/health")
def health():
    return {"status": "ok"}
