import asyncio
from contextlib import asynccontextmanager

import pytest
from app.main import app
from fastapi.testclient import TestClient

from tests.config import create_test_tables, delete_rows


@asynccontextmanager
async def noop_lifespan(app):
    yield


@pytest.fixture(autouse=True)
def prepare_db():
    asyncio.run(create_test_tables())
    yield
    asyncio.run(delete_rows())


@pytest.fixture
def client():
    original = app.router.lifespan_context
    app.router.lifespan_context = noop_lifespan
    with TestClient(app) as c:
        yield c
    app.router.lifespan_context = original
