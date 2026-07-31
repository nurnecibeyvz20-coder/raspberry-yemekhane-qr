from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    secret_key: str = "test-secret"
    database_url: str = "sqlite:///:memory:"
    initial_admin_sicil: str = "admin"
    initial_admin_password: str = "admin123"
    session_max_age: int = 2592000     # imza max_age (en büyük süre)
    personel_session_age: int = 2592000  # 30 gün
    admin_session_age: int = 43200       # 12 saat
    qr_token_ttl: int = 60         # saniye
    sms_provider: str = "demo"
    mail_provider: str = "demo"
    payment_provider: str = "demo"

settings = Settings()
