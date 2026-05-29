"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import get_settings
from app.core.database import SessionLocal, init_db
from app.services.backup_service import BackupService


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    settings = get_settings()
    if settings.backup_on_startup:
        with SessionLocal() as db:
            try:
                BackupService(db, settings=settings).create_backup(notes="startup")
            except Exception:
                pass
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title="Employee Dispatch Route Optimizer",
        description="Internal dispatch, assignment, and pickup route planning",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(api_router)
    return application


app = create_app()
