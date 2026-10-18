from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.config import AsyncSessionLocal
from app.db.seed import seed_tariffs
from app.routers import payment_router, tariff_router, webhook_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with AsyncSessionLocal() as db:
        await seed_tariffs(db)
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(tariff_router)
app.include_router(payment_router)
app.include_router(webhook_router)
