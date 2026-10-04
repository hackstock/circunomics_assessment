import os
from collections.abc import Generator
from contextlib import asynccontextmanager

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite://")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.providers.registry import get_provider
from tests.fakes import FakeProvider


engine = create_engine(
    "sqlite+pysqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@asynccontextmanager
async def _test_lifespan(_app):
    yield


app.router.lifespan_context = _test_lifespan


@pytest.fixture
def db() -> Generator[Session, None, None]:
    Base.metadata.create_all(bind=engine)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def provider() -> FakeProvider:
    return FakeProvider()


@pytest.fixture
def client(db: Session, provider: FakeProvider) -> Generator[TestClient, None, None]:
    def override_db():
        yield db

    def override_provider():
        return provider

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_provider] = override_provider
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
