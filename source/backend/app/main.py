from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api import router
from app.db import Base, engine, wait_for_db
from app.logging import configure_logging
from app.metrics import prometheus_payload
from app import models as _models  # noqa: F401 — register ORM tables on Base

configure_logging()

_ = _models


@asynccontextmanager
async def lifespan(_app: FastAPI):
    wait_for_db()
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Contributor Tracker", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix="/api")


@app.get("/metrics")
def metrics():
    body, media_type = prometheus_payload()
    return Response(content=body, media_type=media_type)
