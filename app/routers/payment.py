import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.config import get_db
from app.db.models import Payment, PaymentStatus, Tariff
from app.db.schemas import PaymentCreate, PaymentOut
from app.utils import generate_schedule

payment_router = APIRouter(prefix="/payments", tags=["payments"])


@payment_router.get("", response_model=list[PaymentOut])
async def list_payments(
    db: AsyncSession = Depends(get_db),
    email: str | None = None,
    payment_status: PaymentStatus | None = Query(default=None, alias="status"),
) -> list[Payment]:
    stmt = select(Payment)
    if email is not None:
        stmt = stmt.where(Payment.email == email)
    if payment_status is not None:
        stmt = stmt.where(Payment.status == payment_status)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@payment_router.post("", response_model=PaymentOut, status_code=201)
async def create_payment(
    data: PaymentCreate,
    response: Response,
    db: AsyncSession = Depends(get_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> Payment:
    if idempotency_key is not None:
        existing = await db.scalar(
            select(Payment).where(Payment.idempotency_key == idempotency_key)
        )
        if existing is not None:
            response.status_code = status.HTTP_200_OK
            return existing

    tariff = await db.get(Tariff, data.tariff_id)
    if tariff is None:
        raise HTTPException(404, "Tariff not found")

    price = tariff.price
    discount = 0
    schedule = None
    if data.promo_code is not None:
        if data.promo_code.upper() != "KVITTO10":
            raise HTTPException(422, "Unknown promocode")
        discount = price * 10 // 100

    amount = price - discount
    if data.installment_months is not None:
        schedule = generate_schedule(amount, data.installment_months)

    payment = Payment(
        status=PaymentStatus.pending,
        tariff_id=tariff.id,
        amount=amount,
        discount=discount,
        method=data.method,
        installment_months=data.installment_months,
        schedule=schedule,
        email=str(data.email),
        idempotency_key=idempotency_key,
    )
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    return payment

@payment_router.get("/{payment_id}", response_model=PaymentOut)
async def get_payment(
    payment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Payment:
    payment = await db.get(Payment, payment_id)
    if payment is None:
        raise HTTPException(404, "Payment not found")
    return payment
