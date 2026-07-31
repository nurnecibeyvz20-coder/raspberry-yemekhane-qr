from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from app.config import settings


@dataclass
class OdemeSonucu:
    basarili: bool
    ref: str
    mesaj: str


class PaymentProvider(Protocol):
    def dogrula(self, kart_no: str, tutar: Decimal, ref: str) -> OdemeSonucu: ...


class DemoPos:
    def dogrula(self, kart_no: str, tutar: Decimal, ref: str) -> OdemeSonucu:
        temiz = kart_no.replace(" ", "")
        if temiz.startswith("4242"):
            return OdemeSonucu(True, ref, "Onaylandı")
        return OdemeSonucu(False, ref, "Kart reddedildi")


def get_payment_provider() -> PaymentProvider:
    if settings.payment_provider == "demo":
        return DemoPos()
    raise ValueError(f"Bilinmeyen ödeme sağlayıcısı: {settings.payment_provider}")
