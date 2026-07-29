from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import OperationalError

from app.db import SessionLocal
from app.routers import admin_routes, auth_routes, kiosk_routes, qr_routes
from app.startup import ensure_initial_admin

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
    yield

app = FastAPI(title="Yemekhane QR", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(auth_routes.router)
app.include_router(admin_routes.router)
app.include_router(qr_routes.router)
app.include_router(kiosk_routes.router)

@app.get("/health")
def health():
    return {"status": "ok"}
