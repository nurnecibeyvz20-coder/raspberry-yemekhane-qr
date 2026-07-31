import math
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models import User, Transaction, MealEntry, FailedAttempt

@dataclass
class Page:
    items: list
    total: int
    page: int
    pages: int

def paginate(query, page: int, per_page: int = 50) -> Page:
    total = query.count()
    pages = max(1, math.ceil(total / per_page))
    page = max(1, min(page, pages))
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return Page(items=items, total=total, page=page, pages=pages)

def dashboard_stats(db: Session) -> dict:
    today = date.today()
    bugun_yiyen = (db.query(func.count(MealEntry.id))
                     .filter(MealEntry.entry_date == today).scalar()) or 0
    aktif_personel = (db.query(func.count(User.id))
                        .filter(User.is_active.is_(True)).scalar()) or 0
    toplam_bakiye = (db.query(func.coalesce(func.sum(User.balance), 0))
                       .filter(User.is_active.is_(True)).scalar())
    bugun_ciro = (db.query(func.coalesce(func.sum(Transaction.amount), 0))
                    .filter(Transaction.type == "yemek",
                            func.date(Transaction.created_at) == today)
                    .scalar())
    bugun_yuklenen = (db.query(func.coalesce(func.sum(Transaction.amount), 0))
                        .filter(Transaction.type == "yukleme",
                                func.date(Transaction.created_at) == today)
                        .scalar())
    son_islemler = (db.query(Transaction)
                      .order_by(Transaction.created_at.desc(),
                                Transaction.id.desc())
                      .limit(10).all())
    son_hatalar = (db.query(FailedAttempt)
                     .order_by(FailedAttempt.created_at.desc(),
                               FailedAttempt.id.desc())
                     .limit(5).all())
    return {
        "bugun_yiyen": int(bugun_yiyen),
        "aktif_personel": int(aktif_personel),
        "toplam_bakiye": Decimal(toplam_bakiye),
        "bugun_ciro": abs(Decimal(bugun_ciro)),
        "bugun_yuklenen": Decimal(bugun_yuklenen),
        "son_islemler": son_islemler,
        "son_hatalar": son_hatalar,
    }
