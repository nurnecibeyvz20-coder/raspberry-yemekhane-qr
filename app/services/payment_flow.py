from decimal import Decimal
from uuid import uuid4

from sqlalchemy import update as sa_update
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Payment, Transaction, User
from app.providers.payment import get_payment_provider

TUTAR_ALT = Decimal("50")
TUTAR_UST = Decimal("5000")


def baslat(db: Session, user: User, tutar: Decimal) -> Payment:
    if not tutar.is_finite() or tutar < TUTAR_ALT or tutar > TUTAR_UST:
        raise ValueError("Tutar 50-5000 TL arasında olmalı")
    payment = Payment(
        user_id=user.id,
        tutar=tutar,
        durum="baslatildi",
        saglayici=settings.payment_provider,
        saglayici_ref=uuid4().hex[:16],
    )
    db.add(payment)
    db.commit()
    return payment


def tamamla(db: Session, payment_id: int, kart_no: str) -> Payment:
    payment = db.get(Payment, payment_id)
    if payment.durum != "baslatildi":
        return payment  # idempotent: sağlayıcı çağrılmaz, bakiye değişmez

    # Atomik claim: yarışan isteklerden yalnız biri satırı 'isleniyor' yapar.
    claimed = db.execute(
        sa_update(Payment)
        .where(Payment.id == payment_id, Payment.durum == "baslatildi")
        .values(durum="isleniyor")
    ).rowcount
    db.commit()
    if claimed == 0:
        db.refresh(payment)
        return payment  # başka istek kazandı ya da zaten bitti

    db.refresh(payment)
    try:
        provider = get_payment_provider()
        sonuc = provider.dogrula(kart_no, payment.tutar,
                                 payment.saglayici_ref)
    except Exception:
        # Sağlayıcı hatası: claim'i geri al, ödeme tekrar denenebilir kalsın.
        db.rollback()
        payment.durum = "baslatildi"
        db.commit()
        raise

    if sonuc.basarili:
        user = db.get(User, payment.user_id)
        new_balance = user.balance + payment.tutar
        tx = Transaction(user_id=user.id, type="yukleme",
                         amount=payment.tutar, balance_after=new_balance,
                         created_by=None)
        db.add(tx)
        db.flush()
        payment.durum = "basarili"
        payment.transaction_id = tx.id
        user.balance = new_balance
        db.commit()
    else:
        payment.durum = "basarisiz"
        db.commit()
    return payment
