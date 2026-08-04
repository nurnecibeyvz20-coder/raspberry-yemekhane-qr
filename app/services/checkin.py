from dataclasses import dataclass
from datetime import date, datetime, time
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
    "saat_disi": "Yemekhane şu an kapalı",
}

def _parse_hhmm(s: str) -> time:
    return time.fromisoformat(s)

def get_meal_price(db: Session) -> Decimal:
    row = db.get(Setting, "meal_price")
    if row is None:
        row = Setting(key="meal_price", value="125.00")
        db.add(row)
        db.commit()
    return Decimal(row.value)

def get_service_hours(db: Session) -> tuple[time, time]:
    bas = db.get(Setting, "saat_baslangic")
    bit = db.get(Setting, "saat_bitis")
    if bas is None or bit is None:
        if bas is None:
            bas = Setting(key="saat_baslangic", value="12:00")
            db.add(bas)
        if bit is None:
            bit = Setting(key="saat_bitis", value="13:30")
            db.add(bit)
        db.commit()
    return _parse_hhmm(bas.value), _parse_hhmm(bit.value)

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
        user_id, qr_secret = verify_token(raw_token)
    except ExpiredToken:
        return _fail(db, raw_token, "suresi_dolmus")
    except InvalidToken:
        return _fail(db, raw_token, "gecersiz")

    user = db.get(User, user_id)
    if user is None or user.qr_secret != qr_secret:
        return _fail(db, raw_token, "gecersiz")
    if not user.is_active or user.registration_status != "approved":
        return _fail(db, raw_token, "hesap_pasif", user)

    bas, bit = get_service_hours(db)
    simdi = datetime.now().time()
    if not (bas <= simdi <= bit):
        return _fail(db, raw_token, "saat_disi", user)

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
