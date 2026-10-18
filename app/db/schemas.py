import uuid
from datetime import datetime
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, EmailStr, model_validator

from app.db.models import PaymentMethod, PaymentStatus


class TariffOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    price: int


class PaymentCreate(BaseModel):
    tariff_id: str
    email: EmailStr
    method: PaymentMethod
    installment_months: Literal[3, 6, 12] | None = None
    promo_code: str | None = None

    @model_validator(mode="after")
    def check_installment_months(self) -> Self:
        if self.method == PaymentMethod.installment:
            if self.installment_months is None:
                raise ValueError(
                    "installment_months is required when method is installment"
                )
        elif self.installment_months is not None:
            raise ValueError(
                "installment_months is only allowed when method is installment"
            )
        return self


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: PaymentStatus
    tariff_id: str
    amount: int
    discount: int
    method: PaymentMethod
    installment_months: int | None
    schedule: list[int] | None
    email: str
    created_at: datetime

class BankWebhookIn(BaseModel):
    payment_id: uuid.UUID
    status: PaymentStatus
