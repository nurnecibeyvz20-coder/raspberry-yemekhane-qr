from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    secret_key: str = "test-secret"
    database_url: str = "sqlite:///:memory:"
    initial_admin_sicil: str = "admin"
    initial_admin_password: str = "admin123"
    session_max_age: int = 604800  # 7 gün
    qr_token_ttl: int = 60         # saniye

settings = Settings()
