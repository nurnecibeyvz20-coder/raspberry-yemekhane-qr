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
