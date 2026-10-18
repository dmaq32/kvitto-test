from app.db.config import engine_test, get_db
from app.db.models import Base
from app.db.seed import seed_tariffs
from app.main import app
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

AsyncSessionLocalTest = async_sessionmaker(
    bind=engine_test,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db_test():
    db = AsyncSessionLocalTest()
    try:
        yield db
    finally:
        await db.close()


app.dependency_overrides[get_db] = get_db_test


async def create_test_tables():
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocalTest() as db:
        await seed_tariffs(db)


async def delete_rows():
    async with engine_test.begin() as conn:
        await conn.execute(text("DELETE FROM payments"))
        await conn.execute(text("DELETE FROM tariffs"))
