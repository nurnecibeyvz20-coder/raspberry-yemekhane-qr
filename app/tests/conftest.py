import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app
from app.db import Base, get_db

@pytest.fixture
def client():
    return TestClient(app, client=("127.0.0.1", 50000))

@pytest.fixture
def client_remote():
    return TestClient(app, client=("192.168.1.50", 50000))

def _make_engine():
    return create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

@pytest.fixture
def db_session():
    engine = _make_engine()
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()

@pytest.fixture
def admin_db():
    engine = _make_engine()
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False)
    session = TestingSession()

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield session
    app.dependency_overrides.pop(get_db, None)
    session.close()

@pytest.fixture
def seeded_db():
    from decimal import Decimal
    from app.auth import hash_password
    from app.models import User

    engine = _make_engine()
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False)

    session = TestingSession()
    user = User(
        sicil_no="1001",
        ad_soyad="Test Personel",
        role="personel",
        password_hash=hash_password("dogru123"),
        balance=Decimal("500.00"),
    )
    session.add(user)
    session.commit()

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield user.id
    app.dependency_overrides.pop(get_db, None)
    session.close()

@pytest.fixture
def seeded_db_low_balance():
    from decimal import Decimal
    from app.auth import hash_password
    from app.models import User

    engine = _make_engine()
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False)

    session = TestingSession()
    user = User(
        sicil_no="1003",
        ad_soyad="Az Bakiye",
        role="personel",
        password_hash=hash_password("dogru123"),
        balance=Decimal("50.00"),
    )
    session.add(user)
    session.commit()

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield session
    app.dependency_overrides.pop(get_db, None)
    session.close()
