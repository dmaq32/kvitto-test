from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Tariff

DEFAULT_TARIFFS = (
    ("basic", "Basic", 990_000),
    ("standard", "Standard", 1_990_000),
    ("premium", "Premium", 2_990_000),
)


async def seed_tariffs(db: AsyncSession) -> None:
    existing = set((await db.scalars(select(Tariff.id))).all())
    for tariff_id, title, price in DEFAULT_TARIFFS:
        if tariff_id not in existing:
            db.add(Tariff(id=tariff_id, title=title, price=price))
    await db.commit()
