import hashlib
import hmac

from fastapi import HTTPException

from app.db.config import WEBHOOK_SECRET


def generate_schedule(total_amount: int, months: int) -> list[int]:
    if months <= 0:
        raise ValueError("Количество месяцев должно быть больше нуля")

    quotient, remainder = divmod(total_amount, months)

    return [quotient + 1 if i < remainder else quotient for i in range(months)]


def check_signature(body: bytes, signature: str | None) -> None:
    if signature is None:
        raise HTTPException(status_code=401, detail="Missing X-Signature")
    expected = hmac.new(
        WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=401, detail="Invalid X-Signature")
