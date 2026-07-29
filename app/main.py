from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routers import auth_routes, qr_routes

app = FastAPI(title="Yemekhane QR")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(auth_routes.router)
app.include_router(qr_routes.router)

@app.get("/health")
def health():
    return {"status": "ok"}
