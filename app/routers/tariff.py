from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.config import get_db
from app.db.models import Tariff
from app.db.schemas import TariffOut

tariff_router = APIRouter(prefix="/tariffs", tags=["tariffs"])


@tariff_router.get("", response_model=list[TariffOut], status_code=200)
async def get_tariffs(db: AsyncSession = Depends(get_db)) -> list[Tariff]:
    result = await db.execute(select(Tariff))
    return result.scalars().all()
