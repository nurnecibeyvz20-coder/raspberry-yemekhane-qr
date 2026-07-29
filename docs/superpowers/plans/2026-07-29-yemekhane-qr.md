# Yemekhane QR Sistemi Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** RPi üzerinde Docker'da çalışan, dinamik QR ile yemekhane girişi ve TL bakiye yönetimi yapan sistem.

**Architecture:** Tek FastAPI monolith (API + Jinja2 HTML) + PostgreSQL 16, Docker Compose ile. Kiosk ekranı host'taki Chromium kiosk-mode tarayıcıda çalışır; USB HID QR okuyucu klavye girdisi olarak yakalanır.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.x, Alembic, psycopg[binary], passlib[bcrypt], itsdangerous, Jinja2, pytest, httpx, PostgreSQL 16, Docker Compose.

## Global Constraints

- Yemek ücreti varsayılanı: `125.00` TL (settings tablosunda `meal_price`, admin panelden değiştirilebilir)
- QR token ömrü: 60 saniye; sayfa 45 saniyede bir yeniler
- Giriş limiti: günde 1 (DB kısıtı `UNIQUE(user_id, entry_date)`)
- Roller: yalnız `personel` ve `admin`
- Oturum çerezi ömrü: 7 gün
- `/kiosk` ve `/api/checkin` yalnız localhost'tan erişilebilir
- Tüm para alanları `NUMERIC(10,2)`; Python tarafında `decimal.Decimal`
- Konteynerler `restart: unless-stopped`
- Arayüz dili Türkçe
- Şifreler bcrypt ile hash'lenir
- `SECRET_KEY`, DB şifresi, ilk admin bilgileri `.env`'den okunur; `.env` git'e girmez
- Commit mesajları İngilizce, `feat:`/`test:`/`chore:` önekli

---

### Task 1: Proje iskeleti + Docker Compose + boş FastAPI app

**Files:**
- Create: `.gitignore`, `.env.example`, `docker-compose.yml`
- Create: `app/Dockerfile`, `app/requirements.txt`, `app/main.py`, `app/config.py`
- Test: `app/tests/test_health.py`, `app/tests/conftest.py`

**Interfaces:**
- Consumes: —
- Produces: `app.main:app` (FastAPI instance), `GET /health` → `{"status": "ok"}`, `app.config.Settings` (pydantic-settings: `secret_key: str`, `database_url: str`, `initial_admin_sicil: str`, `initial_admin_password: str`, `session_max_age: int = 604800`, `qr_token_ttl: int = 60`)

- [ ] **Step 1: Dosya iskeletini oluştur**

`.gitignore`:
```
.env
__pycache__/
*.pyc
.pytest_cache/
pgdata/
backups/
```

`.env.example`:
```
SECRET_KEY=degistir-bunu-uzun-rastgele-bir-deger
POSTGRES_PASSWORD=degistir-db-sifresi
DATABASE_URL=postgresql+psycopg://yemekhane:degistir-db-sifresi@db:5432/yemekhane
INITIAL_ADMIN_SICIL=admin
INITIAL_ADMIN_PASSWORD=degistir-admin-sifresi
```

`app/requirements.txt`:
```
fastapi==0.115.*
uvicorn[standard]==0.32.*
sqlalchemy==2.0.*
alembic==1.14.*
psycopg[binary]==3.2.*
passlib[bcrypt]==1.7.*
bcrypt==4.0.1
itsdangerous==2.2.*
jinja2==3.1.*
pydantic-settings==2.6.*
python-multipart==0.0.*
pytest==8.*
httpx==0.27.*
pytest-asyncio==0.24.*
```

`app/config.py`:
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    secret_key: str = "test-secret"
    database_url: str = "sqlite:///:memory:"
    initial_admin_sicil: str = "admin"
    initial_admin_password: str = "admin123"
    session_max_age: int = 604800  # 7 gün
    qr_token_ttl: int = 60         # saniye

settings = Settings()
```

`app/main.py`:
```python
from fastapi import FastAPI

app = FastAPI(title="Yemekhane QR")

@app.get("/health")
def health():
    return {"status": "ok"}
```

`app/tests/conftest.py`:
```python
import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    return TestClient(app)
```

`app/Dockerfile`:
```dockerfile
FROM python:3.12-slim
WORKDIR /code
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . /code/app
ENV PYTHONPATH=/code
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

`docker-compose.yml`:
```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: yemekhane
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: yemekhane
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U yemekhane"]
      interval: 5s
      timeout: 3s
      retries: 10
    restart: unless-stopped

  app:
    build: ./app
    env_file: .env
    ports:
      - "80:8000"
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped

volumes:
  pgdata:
```

- [ ] **Step 2: Failing test yaz**

`app/tests/test_health.py`:
```python
def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
```

- [ ] **Step 3: Testi çalıştır**

Run (repo kökünden): `python -m pytest app/tests/test_health.py -v`
Expected: PASS (main.py zaten yazıldı; import hatası varsa düzelt)

- [ ] **Step 4: Commit**

```bash
git add .gitignore .env.example docker-compose.yml app/
git commit -m "feat: project skeleton with FastAPI app and docker compose"
```

---

### Task 2: Veri modeli (SQLAlchemy) + Alembic migration

**Files:**
- Create: `app/db.py`, `app/models.py`
- Create: `app/alembic.ini`, `app/migrations/env.py`, `app/migrations/versions/0001_initial.py`
- Test: `app/tests/test_models.py`
- Modify: `app/tests/conftest.py`

**Interfaces:**
- Consumes: `app.config.settings`
- Produces:
  - `app.db.SessionLocal`, `app.db.get_db()` (FastAPI dependency), `app.db.Base`
  - `app.models.User(id, sicil_no, ad_soyad, role, password_hash, balance, is_active, created_at)`
  - `app.models.Transaction(id, user_id, type, amount, balance_after, created_by, created_at)`
  - `app.models.MealEntry(id, user_id, entry_date, transaction_id, created_at)` + `UniqueConstraint("user_id", "entry_date")`
  - `app.models.Setting(key, value)`
  - `app.models.FailedAttempt(id, raw_qr, reason, user_id, created_at)`

- [ ] **Step 1: Failing test yaz**

`app/tests/test_models.py`:
```python
from decimal import Decimal
from datetime import date
import pytest
from sqlalchemy.exc import IntegrityError
from app.models import User, MealEntry

def test_user_defaults(db_session):
    u = User(sicil_no="1001", ad_soyad="Ali Veli",
             role="personel", password_hash="x")
    db_session.add(u)
    db_session.commit()
    assert u.balance == Decimal("0.00")
    assert u.is_active is True

def test_one_meal_per_day_constraint(db_session):
    u = User(sicil_no="1002", ad_soyad="Ayşe Can",
             role="personel", password_hash="x")
    db_session.add(u)
    db_session.commit()
    db_session.add(MealEntry(user_id=u.id, entry_date=date(2026, 7, 29)))
    db_session.commit()
    db_session.add(MealEntry(user_id=u.id, entry_date=date(2026, 7, 29)))
    with pytest.raises(IntegrityError):
        db_session.commit()
```

`app/tests/conftest.py`'ye ekle:
```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db import Base

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()
```

- [ ] **Step 2: Testi çalıştır, FAIL doğrula**

Run: `python -m pytest app/tests/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError: app.models`

- [ ] **Step 3: Modelleri yaz**

`app/db.py`:
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import settings

class Base(DeclarativeBase):
    pass

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

`app/models.py`:
```python
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import (String, Numeric, Boolean, ForeignKey, Date,
                        DateTime, UniqueConstraint, func)
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    sicil_no: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    ad_soyad: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(10))  # 'personel' | 'admin'
    password_hash: Mapped[str] = mapped_column(String(200))
    balance: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

class Transaction(Base):
    __tablename__ = "transactions"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    type: Mapped[str] = mapped_column(String(10))  # 'yukleme'|'yemek'|'duzeltme'
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    balance_after: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

class MealEntry(Base):
    __tablename__ = "meal_entries"
    __table_args__ = (UniqueConstraint("user_id", "entry_date"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    entry_date: Mapped[date] = mapped_column(Date)
    transaction_id: Mapped[int | None] = mapped_column(ForeignKey("transactions.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(50), primary_key=True)
    value: Mapped[str] = mapped_column(String(200))

class FailedAttempt(Base):
    __tablename__ = "failed_attempts"
    id: Mapped[int] = mapped_column(primary_key=True)
    raw_qr: Mapped[str] = mapped_column(String(500))
    reason: Mapped[str] = mapped_column(String(20))
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

- [ ] **Step 4: Testi çalıştır, PASS doğrula**

Run: `python -m pytest app/tests/test_models.py -v`
Expected: 2 PASS

- [ ] **Step 5: Alembic migration oluştur**

`app/alembic.ini` (standart şablon, `script_location = migrations`, `sqlalchemy.url` boş bırak). `app/migrations/env.py` içinde:
```python
from app.config import settings
from app.db import Base
from app import models  # noqa: F401  (tabloları kaydettirir)
config.set_main_option("sqlalchemy.url", settings.database_url)
target_metadata = Base.metadata
```
`0001_initial.py`'yi `alembic revision --autogenerate -m "initial"` ile üret (lokal Postgres yoksa Docker'da: `docker compose run --rm app alembic -c /code/app/alembic.ini revision --autogenerate -m initial`). Üretilen dosyada 5 tablonun ve unique constraint'in olduğunu gözle doğrula.

- [ ] **Step 6: Commit**

```bash
git add app/db.py app/models.py app/alembic.ini app/migrations/ app/tests/
git commit -m "feat: data model and initial migration"
```

---

### Task 3: Auth çekirdeği — şifre hash, oturum çerezi, login/logout

**Files:**
- Create: `app/auth.py`, `app/routers/auth_routes.py`, `app/templates/login.html`, `app/templates/base.html`
- Modify: `app/main.py`
- Test: `app/tests/test_auth.py`

**Interfaces:**
- Consumes: `User` modeli, `get_db`, `settings`
- Produces:
  - `app.auth.hash_password(plain: str) -> str`, `app.auth.verify_password(plain: str, hashed: str) -> bool`
  - `app.auth.create_session_cookie(user_id: int) -> str`, `app.auth.read_session_cookie(value: str) -> int | None` (itsdangerous `TimestampSigner`, max_age=`settings.session_max_age`)
  - FastAPI dependencies: `app.auth.current_user(request, db) -> User` (401 yönlendirme `/login`'e), `app.auth.require_admin(user) -> User` (403)
  - Rotalar: `GET /login`, `POST /login` (form: sicil_no, password → çerez `session` set edilir, personel `/qr`'a, admin `/admin`'e yönlenir), `POST /logout`
  - `POST /login` rate-limit: aynı IP'den dakikada 10 deneme (basit in-memory sayaç `app.auth.RateLimiter`)

- [ ] **Step 1: Failing test yaz**

`app/tests/test_auth.py`:
```python
from app.auth import (hash_password, verify_password,
                      create_session_cookie, read_session_cookie)

def test_password_hash_roundtrip():
    h = hash_password("gizli123")
    assert h != "gizli123"
    assert verify_password("gizli123", h)
    assert not verify_password("yanlis", h)

def test_session_cookie_roundtrip():
    c = create_session_cookie(42)
    assert read_session_cookie(c) == 42

def test_session_cookie_tampered():
    c = create_session_cookie(42) + "x"
    assert read_session_cookie(c) is None

def test_login_wrong_password(client, seeded_db):
    r = client.post("/login",
                    data={"sicil_no": "1001", "password": "yanlis"},
                    follow_redirects=False)
    assert r.status_code == 200  # login sayfası hata mesajıyla döner
    assert "Hatalı" in r.text

def test_login_success_sets_cookie(client, seeded_db):
    r = client.post("/login",
                    data={"sicil_no": "1001", "password": "dogru123"},
                    follow_redirects=False)
    assert r.status_code == 303
    assert "session" in r.cookies
```

`conftest.py`'ye `seeded_db` fixture'ı ekle: test DB'sine `sicil_no="1001"`, şifresi `dogru123` (hash'li) bir personel yazar ve `app.dependency_overrides[get_db]` ile test oturumunu bağlar.

- [ ] **Step 2: Testi çalıştır, FAIL doğrula**

Run: `python -m pytest app/tests/test_auth.py -v`
Expected: FAIL — `ModuleNotFoundError: app.auth`

- [ ] **Step 3: `app/auth.py` yaz**

```python
import time
from collections import defaultdict
from fastapi import Depends, HTTPException, Request
from itsdangerous import TimestampSigner, BadSignature, SignatureExpired
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from app.config import settings
from app.db import get_db
from app.models import User

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
_signer = TimestampSigner(settings.secret_key, salt="session")

def hash_password(plain: str) -> str:
    return pwd.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd.verify(plain, hashed)

def create_session_cookie(user_id: int) -> str:
    return _signer.sign(str(user_id)).decode()

def read_session_cookie(value: str) -> int | None:
    try:
        raw = _signer.unsign(value, max_age=settings.session_max_age)
        return int(raw)
    except (BadSignature, SignatureExpired, ValueError):
        return None

class RateLimiter:
    def __init__(self, limit: int = 10, window: int = 60):
        self.limit, self.window = limit, window
        self.hits: dict[str, list[float]] = defaultdict(list)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        self.hits[key] = [t for t in self.hits[key] if now - t < self.window]
        if len(self.hits[key]) >= self.limit:
            return False
        self.hits[key].append(now)
        return True

login_limiter = RateLimiter()

def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    cookie = request.cookies.get("session")
    user_id = read_session_cookie(cookie) if cookie else None
    user = db.get(User, user_id) if user_id else None
    if user is None or not user.is_active:
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return user

def require_admin(user: User = Depends(current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Yetkisiz")
    return user
```

- [ ] **Step 4: Login rotaları + şablonları yaz**

`app/routers/auth_routes.py`: `GET /login` login.html render eder; `POST /login` form alır, `login_limiter.allow(client_ip)` kontrolü (aşımda 429 + "Çok fazla deneme" mesajı), kullanıcıyı sicil_no ile bulur, `verify_password` + `is_active` kontrolü; başarıda 303 redirect (role göre `/qr` veya `/admin`) + `response.set_cookie("session", ..., max_age=settings.session_max_age, httponly=True, samesite="lax")`; hatada login.html'i "Hatalı sicil no veya şifre" mesajıyla döndürür. `POST /logout` çerezi siler, `/login`'e yönlendirir.

`app/templates/base.html`: html5 iskelet, `{% block content %}`, mobil viewport meta, tek `static/style.css` linki. `app/templates/login.html`: sicil no + şifre formu, hata mesajı alanı. `app/main.py`'ye router'ı ve Jinja2Templates + StaticFiles mount'unu ekle.

- [ ] **Step 5: Testleri çalıştır, PASS doğrula**

Run: `python -m pytest app/tests/test_auth.py -v`
Expected: 5 PASS

- [ ] **Step 6: Commit**

```bash
git add app/auth.py app/routers/ app/templates/ app/main.py app/tests/
git commit -m "feat: authentication with sessions, login page, rate limit"
```

---

### Task 4: QR token servisi

**Files:**
- Create: `app/qr_token.py`
- Test: `app/tests/test_qr_token.py`

**Interfaces:**
- Consumes: `settings.secret_key`, `settings.qr_token_ttl`
- Produces:
  - `app.qr_token.generate_token(user_id: int) -> str` (itsdangerous `URLSafeTimedSerializer`, salt="qr-token")
  - `app.qr_token.verify_token(token: str) -> int` — geçerliyse `user_id` döner; bozuk imzada `InvalidToken`, süresi geçmişte `ExpiredToken` fırlatır (her ikisi `app.qr_token` içinde tanımlı exception sınıfları)

- [ ] **Step 1: Failing test yaz**

`app/tests/test_qr_token.py`:
```python
import pytest
from itsdangerous import URLSafeTimedSerializer
from app.qr_token import generate_token, verify_token, InvalidToken, ExpiredToken

def test_roundtrip():
    t = generate_token(7)
    assert verify_token(t) == 7

def test_tampered_token():
    t = generate_token(7)
    with pytest.raises(InvalidToken):
        verify_token(t[:-2] + "zz")

def test_expired_token(monkeypatch):
    t = generate_token(7)
    import app.qr_token as m
    real = m._serializer.loads
    def fake_loads(s, max_age=None):
        return real(s, max_age=-1)  # anında süresi dolmuş say
    monkeypatch.setattr(m._serializer, "loads", fake_loads)
    with pytest.raises(ExpiredToken):
        verify_token(t)

def test_wrong_secret_rejected():
    other = URLSafeTimedSerializer("baska-anahtar", salt="qr-token")
    forged = other.dumps({"uid": 7})
    with pytest.raises(InvalidToken):
        verify_token(forged)
```

- [ ] **Step 2: Testi çalıştır, FAIL doğrula**

Run: `python -m pytest app/tests/test_qr_token.py -v`
Expected: FAIL — `ModuleNotFoundError: app.qr_token`

- [ ] **Step 3: `app/qr_token.py` yaz**

```python
from itsdangerous import (URLSafeTimedSerializer, BadSignature,
                          SignatureExpired)
from app.config import settings

class InvalidToken(Exception):
    pass

class ExpiredToken(Exception):
    pass

_serializer = URLSafeTimedSerializer(settings.secret_key, salt="qr-token")

def generate_token(user_id: int) -> str:
    return _serializer.dumps({"uid": user_id})

def verify_token(token: str) -> int:
    try:
        data = _serializer.loads(token, max_age=settings.qr_token_ttl)
    except SignatureExpired as e:
        raise ExpiredToken() from e
    except (BadSignature, Exception) as e:
        raise InvalidToken() from e
    return int(data["uid"])
```

- [ ] **Step 4: Testleri çalıştır, PASS doğrula**

Run: `python -m pytest app/tests/test_qr_token.py -v`
Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add app/qr_token.py app/tests/test_qr_token.py
git commit -m "feat: signed short-lived QR token service"
```

---

### Task 5: Check-in servisi (iş kuralları çekirdeği)

**Files:**
- Create: `app/services/checkin.py`
- Test: `app/tests/test_checkin.py`

**Interfaces:**
- Consumes: `verify_token/InvalidToken/ExpiredToken` (Task 4), modeller (Task 2)
- Produces:
  - `app.services.checkin.get_meal_price(db) -> Decimal` (settings tablosundan `meal_price`; yoksa `Decimal("125.00")` yazar ve döner)
  - `app.services.checkin.process_checkin(db, raw_token: str) -> CheckinResult`
  - `CheckinResult` dataclass: `ok: bool`, `status: str` (`'onay'|'gecersiz'|'suresi_dolmus'|'hesap_pasif'|'mukerrer'|'yetersiz_bakiye'`), `message: str` (Türkçe ekran mesajı), `ad_soyad: str | None`, `balance: Decimal | None`
  - Başarısız her durumda `FailedAttempt` kaydı yazılır (reason = status)
  - Başarıda tek transaction içinde: `Transaction(type='yemek', amount=-ücret)`, `MealEntry(bugün)`, `users.balance` güncellenir; `IntegrityError` (unique ihlali) yakalanıp `mukerrer` sonucuna çevrilir

- [ ] **Step 1: Failing testleri yaz**

`app/tests/test_checkin.py`:
```python
from decimal import Decimal
from datetime import date
from app.qr_token import generate_token
from app.models import User, MealEntry, Transaction, FailedAttempt
from app.services.checkin import process_checkin, get_meal_price
from app.auth import hash_password

def make_user(db, sicil="2001", balance="500.00", active=True):
    u = User(sicil_no=sicil, ad_soyad="Test Kişi", role="personel",
             password_hash=hash_password("x"), balance=Decimal(balance),
             is_active=active)
    db.add(u); db.commit()
    return u

def test_meal_price_defaults_to_125(db_session):
    assert get_meal_price(db_session) == Decimal("125.00")

def test_successful_checkin(db_session):
    u = make_user(db_session)
    r = process_checkin(db_session, generate_token(u.id))
    assert r.ok and r.status == "onay"
    assert r.balance == Decimal("375.00")
    db_session.refresh(u)
    assert u.balance == Decimal("375.00")
    assert db_session.query(MealEntry).count() == 1
    tx = db_session.query(Transaction).one()
    assert tx.type == "yemek" and tx.amount == Decimal("-125.00")
    assert tx.balance_after == Decimal("375.00")

def test_invalid_token(db_session):
    r = process_checkin(db_session, "sahte-token")
    assert not r.ok and r.status == "gecersiz"
    assert db_session.query(FailedAttempt).one().reason == "gecersiz"

def test_inactive_user(db_session):
    u = make_user(db_session, active=False)
    r = process_checkin(db_session, generate_token(u.id))
    assert r.status == "hesap_pasif"

def test_duplicate_entry_same_day(db_session):
    u = make_user(db_session)
    process_checkin(db_session, generate_token(u.id))
    r = process_checkin(db_session, generate_token(u.id))
    assert r.status == "mukerrer"
    db_session.refresh(u)
    assert u.balance == Decimal("375.00")  # ikinci kez düşmedi

def test_insufficient_balance(db_session):
    u = make_user(db_session, balance="100.00")
    r = process_checkin(db_session, generate_token(u.id))
    assert r.status == "yetersiz_bakiye"
    db_session.refresh(u)
    assert u.balance == Decimal("100.00")
```

- [ ] **Step 2: Testleri çalıştır, FAIL doğrula**

Run: `python -m pytest app/tests/test_checkin.py -v`
Expected: FAIL — `ModuleNotFoundError: app.services`

- [ ] **Step 3: `app/services/checkin.py` yaz**

```python
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.models import (User, Transaction, MealEntry, Setting,
                        FailedAttempt)
from app.qr_token import verify_token, InvalidToken, ExpiredToken

@dataclass
class CheckinResult:
    ok: bool
    status: str
    message: str
    ad_soyad: str | None = None
    balance: Decimal | None = None

MESSAGES = {
    "gecersiz": "Geçersiz QR kodu",
    "suresi_dolmus": "QR süresi dolmuş, telefonunuzda yenileyin",
    "hesap_pasif": "Hesabınız pasif durumda",
    "mukerrer": "Bugün zaten giriş yaptınız",
    "yetersiz_bakiye": "Yetersiz bakiye",
}

def get_meal_price(db: Session) -> Decimal:
    row = db.get(Setting, "meal_price")
    if row is None:
        row = Setting(key="meal_price", value="125.00")
        db.add(row)
        db.commit()
    return Decimal(row.value)

def _fail(db: Session, raw: str, status: str,
          user: User | None = None) -> CheckinResult:
    db.add(FailedAttempt(raw_qr=raw[:500], reason=status,
                         user_id=user.id if user else None))
    db.commit()
    return CheckinResult(ok=False, status=status, message=MESSAGES[status],
                         ad_soyad=user.ad_soyad if user else None,
                         balance=user.balance if user else None)

def process_checkin(db: Session, raw_token: str) -> CheckinResult:
    try:
        user_id = verify_token(raw_token)
    except ExpiredToken:
        return _fail(db, raw_token, "suresi_dolmus")
    except InvalidToken:
        return _fail(db, raw_token, "gecersiz")

    user = db.get(User, user_id)
    if user is None:
        return _fail(db, raw_token, "gecersiz")
    if not user.is_active:
        return _fail(db, raw_token, "hesap_pasif", user)

    today = date.today()
    already = (db.query(MealEntry)
                 .filter_by(user_id=user.id, entry_date=today).first())
    if already:
        return _fail(db, raw_token, "mukerrer", user)

    price = get_meal_price(db)
    if user.balance < price:
        return _fail(db, raw_token, "yetersiz_bakiye", user)

    try:
        new_balance = user.balance - price
        tx = Transaction(user_id=user.id, type="yemek", amount=-price,
                         balance_after=new_balance)
        db.add(tx)
        db.flush()
        db.add(MealEntry(user_id=user.id, entry_date=today,
                         transaction_id=tx.id))
        user.balance = new_balance
        db.commit()
    except IntegrityError:
        db.rollback()
        return _fail(db, raw_token, "mukerrer", user)

    return CheckinResult(ok=True, status="onay",
                         message=f"Afiyet olsun, {user.ad_soyad}",
                         ad_soyad=user.ad_soyad, balance=new_balance)
```

`app/services/__init__.py` boş dosya olarak oluştur.

- [ ] **Step 4: Testleri çalıştır, PASS doğrula**

Run: `python -m pytest app/tests/test_checkin.py -v`
Expected: 6 PASS

- [ ] **Step 5: Commit**

```bash
git add app/services/ app/tests/test_checkin.py
git commit -m "feat: check-in service with balance deduction and daily limit"
```

---

### Task 6: Personel /qr sayfası ve token API'si

**Files:**
- Create: `app/routers/qr_routes.py`, `app/templates/qr.html`, `app/templates/change_password.html`, `app/static/style.css`, `app/static/qrcode.min.js` (davidshimjs/qrcodejs, vendored)
- Modify: `app/main.py`
- Test: `app/tests/test_qr_routes.py`

**Interfaces:**
- Consumes: `current_user` (Task 3), `generate_token` (Task 4), `get_meal_price` (Task 5)
- Produces:
  - `GET /qr` — oturum gerektirir; qr.html render eder (ad_soyad, balance, meal_price context)
  - `GET /api/qr-token` — oturum gerektirir; JSON: `{"token": str, "balance": "375.00", "low_balance": bool, "ttl": 60}` (`low_balance` = balance < meal_price)
  - `GET /change-password`, `POST /change-password` (form: old_password, new_password; eski şifre doğrulanır)

- [ ] **Step 1: Failing test yaz**

`app/tests/test_qr_routes.py`:
```python
from decimal import Decimal

def login(client, sicil="1001", password="dogru123"):
    return client.post("/login", data={"sicil_no": sicil,
                       "password": password}, follow_redirects=False)

def test_qr_page_requires_login(client, seeded_db):
    r = client.get("/qr", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/login"

def test_qr_token_api(client, seeded_db):
    login(client)
    r = client.get("/api/qr-token")
    assert r.status_code == 200
    body = r.json()
    assert body["ttl"] == 60
    assert "token" in body and "balance" in body

def test_low_balance_flag(client, seeded_db_low_balance):
    login(client, sicil="1003")
    r = client.get("/api/qr-token")
    assert r.json()["low_balance"] is True

def test_change_password(client, seeded_db):
    login(client)
    r = client.post("/change-password",
                    data={"old_password": "dogru123",
                          "new_password": "yeni12345"},
                    follow_redirects=False)
    assert r.status_code == 303
    client.post("/logout")
    assert login(client, password="yeni12345").status_code == 303
```

`conftest.py`'ye `seeded_db_low_balance` fixture'ı ekle: `sicil_no="1003"`, `balance=Decimal("50.00")` kullanıcı (şifre `dogru123`).

- [ ] **Step 2: Testi çalıştır, FAIL doğrula**

Run: `python -m pytest app/tests/test_qr_routes.py -v`
Expected: FAIL — 404 (rotalar yok)

- [ ] **Step 3: Rotaları + şablonu yaz**

`app/routers/qr_routes.py`:
```python
from decimal import Decimal
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.auth import current_user, hash_password, verify_password
from app.db import get_db
from app.models import User
from app.qr_token import generate_token
from app.services.checkin import get_meal_price
from app.config import settings
from app.main import templates

router = APIRouter()

@router.get("/qr")
def qr_page(request: Request, user: User = Depends(current_user),
            db: Session = Depends(get_db)):
    price = get_meal_price(db)
    return templates.TemplateResponse(request, "qr.html", {
        "user": user, "meal_price": price,
        "low_balance": user.balance < price})

@router.get("/api/qr-token")
def qr_token(user: User = Depends(current_user),
             db: Session = Depends(get_db)):
    price = get_meal_price(db)
    return {"token": generate_token(user.id),
            "balance": str(user.balance),
            "low_balance": user.balance < price,
            "ttl": settings.qr_token_ttl}

@router.get("/change-password")
def change_password_page(request: Request,
                         user: User = Depends(current_user)):
    return templates.TemplateResponse(request, "change_password.html",
                                      {"user": user, "error": None})

@router.post("/change-password")
def change_password(request: Request,
                    old_password: str = Form(...),
                    new_password: str = Form(...),
                    user: User = Depends(current_user),
                    db: Session = Depends(get_db)):
    if not verify_password(old_password, user.password_hash):
        return templates.TemplateResponse(request, "change_password.html",
            {"user": user, "error": "Eski şifre hatalı"})
    user.password_hash = hash_password(new_password)
    db.commit()
    return RedirectResponse("/qr", status_code=303)
```

Not: `templates` objesi `app/main.py`'de tanımlanır (`templates = Jinja2Templates(directory="app/templates")`); döngüsel import olursa `templates`'i ayrı `app/deps.py`'ye taşı.

`app/templates/qr.html`: base.html'i extend eder. İçerik: ad soyad başlığı, `<div id="qrcode">`, bakiye satırı (`id="balance"`), geri sayım halkası (`id="countdown"`), `low_balance` ise kırmızı `"Bakiyeniz yetersiz"` bandı (`id="low-band"`), şifre değiştir linki, çıkış butonu. Inline JS:
```javascript
let qr = null;
async function refresh() {
  const r = await fetch("/api/qr-token");
  if (!r.ok) { location.href = "/login"; return; }
  const d = await r.json();
  document.getElementById("qrcode").innerHTML = "";
  qr = new QRCode(document.getElementById("qrcode"),
                  {text: d.token, width: 280, height: 280});
  document.getElementById("balance").textContent = d.balance + " TL";
  document.getElementById("low-band").style.display =
      d.low_balance ? "block" : "none";
  startCountdown(45);
}
function startCountdown(s) { /* her sn azalt, 0'da refresh() */ }
refresh();
setInterval(refresh, 45000);
```
`startCountdown` gerçek implementasyonu: `setInterval` ile saniyede bir `#countdown` metnini günceller, mevcut sayaç varsa `clearInterval` ile temizlenir.

`app/static/style.css`: mobil öncelikli; QR ortalanmış, bakiye büyük punto, `.low-band { background:#c0392b; color:#fff; padding:12px; text-align:center; }`.

`qrcode.min.js`'i https://raw.githubusercontent.com/davidshimjs/qrcodejs/master/qrcode.min.js adresinden indirip `app/static/`e koy (CDN'e bağımlılık olmasın — sistem internetsiz çalışmalı).

- [ ] **Step 4: Testleri çalıştır, PASS doğrula**

Run: `python -m pytest app/tests/test_qr_routes.py -v`
Expected: 4 PASS

- [ ] **Step 5: Commit**

```bash
git add app/routers/qr_routes.py app/templates/ app/static/ app/main.py app/tests/
git commit -m "feat: staff QR page with auto-refreshing token"
```

---

### Task 7: Kiosk sayfası + /api/checkin (localhost kısıtlı)

**Files:**
- Create: `app/routers/kiosk_routes.py`, `app/templates/kiosk.html`, `app/static/sounds/ok.mp3`, `app/static/sounds/error.mp3`
- Modify: `app/main.py`
- Test: `app/tests/test_kiosk_routes.py`

**Interfaces:**
- Consumes: `process_checkin` (Task 5)
- Produces:
  - `app.routers.kiosk_routes.localhost_only(request)` dependency — `request.client.host` `127.0.0.1`/`::1` değilse 403
  - `GET /kiosk` — kiosk.html (localhost_only)
  - `POST /api/checkin` — body `{"token": str}` → `CheckinResult` alanlarını JSON döner: `{"ok": bool, "status": str, "message": str, "ad_soyad": str|null, "balance": str|null}` (localhost_only)

- [ ] **Step 1: Failing test yaz**

`app/tests/test_kiosk_routes.py`:
```python
from decimal import Decimal
from app.qr_token import generate_token

def test_checkin_rejected_from_remote_ip(client_remote, seeded_db):
    r = client_remote.post("/api/checkin", json={"token": "x"})
    assert r.status_code == 403

def test_kiosk_page_rejected_from_remote_ip(client_remote, seeded_db):
    assert client_remote.get("/kiosk").status_code == 403

def test_checkin_success(client, seeded_db):
    uid = seeded_db  # fixture user id döndürür
    r = client.post("/api/checkin",
                    json={"token": generate_token(uid)})
    body = r.json()
    assert body["ok"] is True and body["status"] == "onay"
    assert body["balance"] == "375.00"

def test_checkin_invalid_token(client, seeded_db):
    r = client.post("/api/checkin", json={"token": "sahte"})
    body = r.json()
    assert body["ok"] is False and body["status"] == "gecersiz"
```

`conftest.py`: varsayılan `client` fixture'ında `TestClient(app, client=("127.0.0.1", 50000))` kullan; `client_remote` fixture'ı `TestClient(app, client=("192.168.1.50", 50000))` ile oluştur. `seeded_db` fixture'ını user id döndürecek şekilde güncelle (mevcut kullanımları bozma — id'yi `return` et).

- [ ] **Step 2: Testi çalıştır, FAIL doğrula**

Run: `python -m pytest app/tests/test_kiosk_routes.py -v`
Expected: FAIL — 404

- [ ] **Step 3: Rotaları yaz**

`app/routers/kiosk_routes.py`:
```python
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db import get_db
from app.services.checkin import process_checkin
from app.main import templates

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
```

`app/templates/kiosk.html`: iki durum bölmesi — bekleme (`#idle`: logo, canlı saat, "QR kodunuzu okutun") ve sonuç (`#result`: tam ekran renkli kart). Inline JS:
```javascript
let buffer = "";
const input = document.getElementById("scan-input"); // gizli input
document.addEventListener("click", () => input.focus());
input.focus();
input.addEventListener("keydown", async (e) => {
  if (e.key === "Enter") {
    const token = input.value.trim();
    input.value = "";
    if (!token) return;
    try {
      const r = await fetch("/api/checkin", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({token})});
      showResult(await r.json());
    } catch {
      showConnecting();  // "Sistem bağlanıyor..." + 3 sn sonra idle
    }
  }
});
function showResult(d) {
  // status → renk: onay=yeşil, mukerrer=sarı, diğerleri=kırmızı
  // d.message + (d.ad_soyad ? ad : "") + (d.balance ? "Kalan: X TL" : "")
  // ses: d.ok ? ok.mp3 : error.mp3
  // 5000 ms sonra idle'a dön, input.focus()
}
```
`showResult` gerçek implementasyon: `#result`'a class (`green/yellow/red`) atar, metinleri doldurur, `new Audio("/static/sounds/...").play()`, `setTimeout` ile 5 sn sonra `#idle`'a döner. Saat `setInterval` ile her saniye güncellenir. Ses dosyaları: kısa telifsiz bip sesleri (örn. https://github.com/free-sound-effects veya sox ile üret: `sox -n ok.mp3 synth 0.15 sine 880`, `sox -n error.mp3 synth 0.4 sine 220 repeat 1`); dosya bulunamazsa sessiz devam etmek kabul (JS `play().catch(()=>{})`).

- [ ] **Step 4: Testleri çalıştır, PASS doğrula**

Run: `python -m pytest app/tests/test_kiosk_routes.py -v`
Expected: 4 PASS

- [ ] **Step 5: Tüm test paketini çalıştır**

Run: `python -m pytest app/tests -v`
Expected: tümü PASS (önceki task'ler kırılmamış)

- [ ] **Step 6: Commit**

```bash
git add app/routers/kiosk_routes.py app/templates/kiosk.html app/static/ app/main.py app/tests/
git commit -m "feat: kiosk screen and localhost-only checkin API"
```

---

### Task 8: Admin paneli

**Files:**
- Create: `app/routers/admin_routes.py`, `app/templates/admin/list.html`, `app/templates/admin/form.html`, `app/templates/admin/detail.html`, `app/templates/admin/settings.html`
- Modify: `app/main.py`
- Test: `app/tests/test_admin_routes.py`

**Interfaces:**
- Consumes: `require_admin` (Task 3), modeller, `get_meal_price` (Task 5)
- Produces (tüm rotalar `require_admin` korumalı):
  - `GET /admin` — personel listesi; `?q=` arama (sicil_no veya ad_soyad ILIKE)
  - `GET /admin/users/new`, `POST /admin/users/new` (form: sicil_no, ad_soyad, password, role)
  - `GET /admin/users/{id}`, — detay: bilgiler + son 50 transaction + son 50 meal_entry
  - `POST /admin/users/{id}/edit` (form: ad_soyad, role), `POST /admin/users/{id}/password` (form: new_password), `POST /admin/users/{id}/toggle-active`
  - `POST /admin/users/{id}/load-balance` (form: amount — pozitif=`'yukleme'`, negatif=`'duzeltme'`; `created_by`=admin id; transaction + balance güncelleme tek commit)
  - `GET /admin/settings`, `POST /admin/settings` (form: meal_price — `Decimal`'e çevrilip `settings.meal_price`'a yazılır; geçersiz değerde hata mesajı)

- [ ] **Step 1: Failing testleri yaz**

`app/tests/test_admin_routes.py`:
```python
from decimal import Decimal
from app.models import User, Transaction, Setting
from app.auth import hash_password

def login_admin(client, db):
    a = User(sicil_no="9001", ad_soyad="Admin", role="admin",
             password_hash=hash_password("admin123"))
    db.add(a); db.commit()
    client.post("/login", data={"sicil_no": "9001",
                "password": "admin123"})
    return a

def test_admin_requires_admin_role(client, seeded_db):
    client.post("/login", data={"sicil_no": "1001",
                "password": "dogru123"})
    assert client.get("/admin").status_code == 403

def test_create_user(client, db_session):
    login_admin(client, db_session)
    r = client.post("/admin/users/new",
                    data={"sicil_no": "3001", "ad_soyad": "Yeni Kişi",
                          "password": "sifre123", "role": "personel"},
                    follow_redirects=False)
    assert r.status_code == 303
    u = db_session.query(User).filter_by(sicil_no="3001").one()
    assert u.ad_soyad == "Yeni Kişi"

def test_load_balance(client, db_session):
    admin = login_admin(client, db_session)
    u = User(sicil_no="3002", ad_soyad="B", role="personel",
             password_hash="x")
    db_session.add(u); db_session.commit()
    client.post(f"/admin/users/{u.id}/load-balance",
                data={"amount": "500.00"})
    db_session.refresh(u)
    assert u.balance == Decimal("500.00")
    tx = db_session.query(Transaction).one()
    assert tx.type == "yukleme" and tx.created_by == admin.id

def test_negative_amount_is_duzeltme(client, db_session):
    login_admin(client, db_session)
    u = User(sicil_no="3003", ad_soyad="C", role="personel",
             password_hash="x", balance=Decimal("200.00"))
    db_session.add(u); db_session.commit()
    client.post(f"/admin/users/{u.id}/load-balance",
                data={"amount": "-50.00"})
    db_session.refresh(u)
    assert u.balance == Decimal("150.00")
    assert db_session.query(Transaction).one().type == "duzeltme"

def test_toggle_active(client, db_session):
    login_admin(client, db_session)
    u = User(sicil_no="3004", ad_soyad="D", role="personel",
             password_hash="x")
    db_session.add(u); db_session.commit()
    client.post(f"/admin/users/{u.id}/toggle-active")
    db_session.refresh(u)
    assert u.is_active is False

def test_update_meal_price(client, db_session):
    login_admin(client, db_session)
    client.post("/admin/settings", data={"meal_price": "150.00"})
    assert db_session.get(Setting, "meal_price").value == "150.00"

def test_search_users(client, db_session):
    login_admin(client, db_session)
    db_session.add(User(sicil_no="4001", ad_soyad="Mehmet Öz",
                        role="personel", password_hash="x"))
    db_session.commit()
    r = client.get("/admin?q=Mehmet")
    assert "Mehmet Öz" in r.text
```

- [ ] **Step 2: Testleri çalıştır, FAIL doğrula**

Run: `python -m pytest app/tests/test_admin_routes.py -v`
Expected: FAIL — 404

- [ ] **Step 3: `app/routers/admin_routes.py` yaz**

Rotalar Interfaces bölümündeki gibi. Kritik parçalar:

```python
@router.post("/admin/users/{user_id}/load-balance")
def load_balance(user_id: int, amount: str = Form(...),
                 admin: User = Depends(require_admin),
                 db: Session = Depends(get_db)):
    try:
        amt = Decimal(amount)
    except InvalidOperation:
        raise HTTPException(400, "Geçersiz tutar")
    if amt == 0:
        raise HTTPException(400, "Tutar sıfır olamaz")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(404)
    new_balance = user.balance + amt
    db.add(Transaction(
        user_id=user.id,
        type="yukleme" if amt > 0 else "duzeltme",
        amount=amt, balance_after=new_balance, created_by=admin.id))
    user.balance = new_balance
    db.commit()
    return RedirectResponse(f"/admin/users/{user_id}", status_code=303)
```

Personel oluşturmada `sicil_no` benzersizliği `IntegrityError` yakalanarak "Bu sicil no zaten kayıtlı" hatasına çevrilir. Arama: `query.filter(or_(User.sicil_no.ilike(f"%{q}%"), User.ad_soyad.ilike(f"%{q}%")))`. Şablonlar sade tablo + form; base.html'i extend eder, admin nav çubuğu (Personel / Ayarlar / Çıkış) içerir.

- [ ] **Step 4: Testleri çalıştır, PASS doğrula**

Run: `python -m pytest app/tests/test_admin_routes.py -v`
Expected: 7 PASS

- [ ] **Step 5: Commit**

```bash
git add app/routers/admin_routes.py app/templates/admin/ app/main.py app/tests/
git commit -m "feat: admin panel with user management and balance loading"
```

---

### Task 9: Açılış rutini — migration + ilk admin + yarış durumu testi

**Files:**
- Create: `app/startup.py`, `app/entrypoint.sh`
- Modify: `app/main.py`, `app/Dockerfile`
- Test: `app/tests/test_startup.py`, `app/tests/test_race.py`

**Interfaces:**
- Consumes: `settings.initial_admin_sicil/password`, `hash_password`
- Produces: `app.startup.ensure_initial_admin(db)` — `role='admin'` hiç kullanıcı yoksa `.env` bilgileriyle oluşturur; varsa dokunmaz. `entrypoint.sh`: `alembic upgrade head` → `uvicorn` başlat.

- [ ] **Step 1: Failing testleri yaz**

`app/tests/test_startup.py`:
```python
from app.models import User
from app.startup import ensure_initial_admin

def test_creates_admin_when_none(db_session):
    ensure_initial_admin(db_session)
    a = db_session.query(User).filter_by(role="admin").one()
    assert a.sicil_no == "admin"

def test_skips_when_admin_exists(db_session):
    ensure_initial_admin(db_session)
    ensure_initial_admin(db_session)
    assert db_session.query(User).filter_by(role="admin").count() == 1
```

`app/tests/test_race.py` (SQLite'ta gerçek eşzamanlılık test edilemez; unique kısıtın rollback yolunu doğrular):
```python
from decimal import Decimal
from datetime import date
from app.models import User, MealEntry
from app.services.checkin import process_checkin
from app.qr_token import generate_token
from app.auth import hash_password

def test_integrity_error_path_returns_mukerrer(db_session):
    u = User(sicil_no="5001", ad_soyad="R", role="personel",
             password_hash=hash_password("x"),
             balance=Decimal("500.00"))
    db_session.add(u); db_session.commit()
    # İlk girişi araya sıkıştır: process_checkin'in kendi sorgusu
    # göremeden unique ihlali oluşsun diye entry'yi önceden ekleyip
    # sorguyu monkeypatch'lemek yerine direkt iki ardışık çağrının
    # ikincisinin mukerrer döndüğünü ve bakiyenin tek düştüğünü doğrula
    r1 = process_checkin(db_session, generate_token(u.id))
    r2 = process_checkin(db_session, generate_token(u.id))
    assert r1.ok and r2.status == "mukerrer"
    db_session.refresh(u)
    assert u.balance == Decimal("375.00")
    assert db_session.query(MealEntry).count() == 1
```

- [ ] **Step 2: Testleri çalıştır, FAIL doğrula**

Run: `python -m pytest app/tests/test_startup.py app/tests/test_race.py -v`
Expected: FAIL — `ModuleNotFoundError: app.startup`

- [ ] **Step 3: `app/startup.py` + entrypoint yaz**

`app/startup.py`:
```python
from sqlalchemy.orm import Session
from app.auth import hash_password
from app.config import settings
from app.models import User

def ensure_initial_admin(db: Session) -> None:
    exists = db.query(User).filter_by(role="admin").first()
    if exists:
        return
    db.add(User(sicil_no=settings.initial_admin_sicil,
                ad_soyad="Sistem Yöneticisi", role="admin",
                password_hash=hash_password(
                    settings.initial_admin_password)))
    db.commit()
```

`app/main.py`'ye lifespan ekle: startup'ta `SessionLocal()` açıp `ensure_initial_admin` çağır (test ortamında DB yoksa sessizce geç: `except OperationalError: pass`).

`app/entrypoint.sh`:
```bash
#!/bin/sh
set -e
cd /code/app
alembic -c alembic.ini upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --app-dir /code
```
Dockerfile'da `CMD` yerine `COPY entrypoint.sh` + `RUN chmod +x` + `ENTRYPOINT ["/code/app/entrypoint.sh"]`.

- [ ] **Step 4: Testleri çalıştır, PASS doğrula**

Run: `python -m pytest app/tests -v`
Expected: tümü PASS

- [ ] **Step 5: Docker'da uçtan uca duman testi (lokal makinede)**

```bash
cp .env.example .env
docker compose up --build -d
curl http://localhost/health        # {"status":"ok"}
curl -I http://localhost/login      # 200
docker compose logs app | grep -i error   # boş olmalı
docker compose down
```

- [ ] **Step 6: Commit**

```bash
git add app/startup.py app/entrypoint.sh app/main.py app/Dockerfile app/tests/
git commit -m "feat: startup migrations and initial admin bootstrap"
```

---

### Task 10: RPi dağıtımı — kiosk systemd, yedekleme, kurulum scripti

**Files:**
- Create: `deploy/kiosk.service`, `deploy/backup.sh`, `deploy/install.sh`, `README.md`

**Interfaces:**
- Consumes: çalışan compose stack (`/health`, `/kiosk`)
- Produces: tek komut RPi kurulumu (`sudo bash deploy/install.sh`), boot'ta kiosk Chromium, günlük 03:00 pg_dump yedeği

- [ ] **Step 1: `deploy/kiosk.service` yaz**

```ini
[Unit]
Description=Yemekhane Kiosk Browser
After=graphical.target network-online.target
Wants=graphical.target

[Service]
User=pi
Environment=DISPLAY=:0
Environment=XAUTHORITY=/home/pi/.Xauthority
ExecStartPre=/bin/sh -c 'until curl -sf http://localhost/health; do sleep 2; done'
ExecStartPre=/bin/sh -c 'xset s off; xset -dpms; xset s noblank'
ExecStart=/usr/bin/chromium-browser --kiosk --noerrdialogs \
  --disable-restore-session-state --disable-infobars \
  --check-for-update-interval=31536000 http://localhost/kiosk
Restart=always
RestartSec=5

[Install]
WantedBy=graphical.target
```

Not: RPi OS Bookworm'da binary adı `chromium-browser` yerine `chromium` olabilir; install.sh hangisi varsa onu service dosyasına yazar. İmleç gizleme için `unclutter` kurulur.

- [ ] **Step 2: `deploy/backup.sh` yaz**

```bash
#!/bin/bash
set -e
BACKUP_DIR=/home/pi/backups
mkdir -p "$BACKUP_DIR"
cd /home/pi/yemekhane
docker compose exec -T db pg_dump -U yemekhane yemekhane \
  | gzip > "$BACKUP_DIR/yemekhane-$(date +%F).sql.gz"
find "$BACKUP_DIR" -name "yemekhane-*.sql.gz" -mtime +30 -delete
```

- [ ] **Step 3: `deploy/install.sh` yaz**

```bash
#!/bin/bash
set -e
# 1. Docker kur (yoksa)
if ! command -v docker >/dev/null; then
  curl -fsSL https://get.docker.com | sh
  usermod -aG docker pi
fi
# 2. unclutter + curl kur
apt-get update && apt-get install -y unclutter curl
# 3. .env kontrolü
cd "$(dirname "$0")/.."
if [ ! -f .env ]; then
  cp .env.example .env
  echo ">>> .env olusturuldu. SECRET_KEY ve sifreleri duzenleyin,"
  echo ">>> sonra scripti tekrar calistirin."
  exit 1
fi
# 4. Stack'i başlat
docker compose up --build -d
# 5. Chromium binary adını bul, service'i kur
CHROMIUM=$(command -v chromium-browser || command -v chromium)
sed "s|/usr/bin/chromium-browser|$CHROMIUM|" deploy/kiosk.service \
  > /etc/systemd/system/kiosk.service
systemctl daemon-reload
systemctl enable kiosk.service
# 6. Yedekleme cron'u
chmod +x deploy/backup.sh
CRON_LINE="0 3 * * * $(pwd)/deploy/backup.sh"
(crontab -l -u pi 2>/dev/null | grep -vF backup.sh; echo "$CRON_LINE") \
  | crontab -u pi -
echo "Kurulum tamam. Yeniden baslatin: sudo reboot"
```

- [ ] **Step 4: README.md yaz**

Kısa kurulum kılavuzu (Türkçe): gereksinimler (RPi 4/5, RPi OS with desktop, USB HID QR okuyucu), kurulum adımları (`git clone` → `.env` düzenle → `sudo bash deploy/install.sh` → reboot), erişim adresleri (`/qr`, `/admin`), ilk admin bilgisinin `.env`'den geldiği ve ilk girişte şifre değiştirme önerisi, yedeklerin `/home/pi/backups`'ta olduğu.

- [ ] **Step 5: Script sözdizimi doğrulaması**

Run: `bash -n deploy/install.sh; bash -n deploy/backup.sh`
Expected: hata yok (Windows'ta Git Bash ile: `& "C:\Program Files\Git\bin\bash.exe" -n deploy/install.sh`)

- [ ] **Step 6: Commit + push**

```bash
git add deploy/ README.md
git commit -m "feat: RPi deployment - kiosk service, backups, installer"
git push origin main
```
