from typing import Protocol

from app.config import settings


class MessageProvider(Protocol):
    def gonder(self, hedef: str, kod: str) -> None: ...


class DemoMessageProvider:
    def gonder(self, hedef: str, kod: str) -> None:
        # Demo modda gerçek gönderim yok; kod reset servisinde
        # demo_gosterim alanına yazılır.
        pass


def get_sms_provider() -> MessageProvider:
    if settings.sms_provider == "demo":
        return DemoMessageProvider()
    raise ValueError(f"Bilinmeyen SMS sağlayıcısı: {settings.sms_provider}")


def get_mail_provider() -> MessageProvider:
    if settings.mail_provider == "demo":
        return DemoMessageProvider()
    raise ValueError(f"Bilinmeyen mail sağlayıcısı: {settings.mail_provider}")
