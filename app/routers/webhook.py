from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.config import get_db
from app.db.models import ALLOWED_STATUS_TRANSITIONS, Payment
from app.db.schemas import BankWebhookIn
from app.utils import check_signature

webhook_router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@webhook_router.post("/bank", status_code=200, response_model=None)
async def bank_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_signature: str | None = Header(default=None, alias="X-Signature"),
):
    raw = await request.body()
    check_signature(raw, x_signature)

    try:
        body = BankWebhookIn.model_validate_json(raw)
    except ValidationError as exc:
        raise RequestValidationError(exc.errors()) from exc

    payment = await db.get(Payment, body.payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")

    allowed = ALLOWED_STATUS_TRANSITIONS.get(payment.status, set())
    if body.status not in allowed:
        return JSONResponse(
            status_code=409,
            content={"error": "invalid_transition"},
        )

    payment.status = body.status
    await db.commit()
    return {"result": "ok"}
