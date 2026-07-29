from fastapi import FastAPI

app = FastAPI(title="Yemekhane QR")

@app.get("/health")
def health():
    return {"status": "ok"}
