from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import (String, Numeric, Boolean, ForeignKey, Date,
                        DateTime, Integer, UniqueConstraint, func)
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
    registration_status: Mapped[str] = mapped_column(
        String(10), default="pending", server_default="pending")
    qr_secret: Mapped[str | None] = mapped_column(String(64), unique=True,
                                                   nullable=True)
    telefon: Mapped[str | None] = mapped_column(String(20), nullable=True)
    eposta: Mapped[str | None] = mapped_column(String(120), nullable=True)
    gizli_soru: Mapped[str | None] = mapped_column(String(200), nullable=True)
    gizli_cevap_hash: Mapped[str | None] = mapped_column(String(200), nullable=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False)
    session_version: Mapped[int] = mapped_column(Integer, default=0)
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

class ResetCode(Base):
    __tablename__ = "reset_codes"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    kanal: Mapped[str] = mapped_column(String(10))  # 'sms' | 'eposta'
    kod_hash: Mapped[str] = mapped_column(String(200))
    demo_gosterim: Mapped[str | None] = mapped_column(String(6), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

class Payment(Base):
    __tablename__ = "payments"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    tutar: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    durum: Mapped[str] = mapped_column(String(12))  # 'baslatildi'|'basarili'|'basarisiz'
    saglayici: Mapped[str] = mapped_column(String(20))
    saglayici_ref: Mapped[str] = mapped_column(String(100))
    transaction_id: Mapped[int | None] = mapped_column(ForeignKey("transactions.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now())

class FailedAttempt(Base):
    __tablename__ = "failed_attempts"
    id: Mapped[int] = mapped_column(primary_key=True)
    raw_qr: Mapped[str] = mapped_column(String(500))
    reason: Mapped[str] = mapped_column(String(20))
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
