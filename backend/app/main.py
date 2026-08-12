import json
import logging
import logging.config
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.error_handler import global_exception_handler
from app.routers import ai_prompts, approvals, auth, dashboard, departments, drills, exams, libraries, question_banks, study_assignments, study_materials, tags, users, videos


def _configure_logging() -> None:
    if settings.LOG_FORMAT == "json":
        fmt = json.dumps(
            {
                "timestamp": "%(asctime)s",
                "level": "%(levelname)s",
                "module": "%(name)s",
                "message": "%(message)s",
            }
        )
    else:
        fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": fmt,
                    "datefmt": "%Y-%m-%dT%H:%M:%S",
                },
            },
            "handlers": {
                "default": {
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                    "formatter": "default",
                },
            },
            "root": {
                "level": settings.LOG_LEVEL,
                "handlers": ["default"],
            },
            "loggers": {
                "uvicorn": {"level": settings.LOG_LEVEL},
                "uvicorn.error": {"level": settings.LOG_LEVEL},
                "uvicorn.access": {"level": "WARNING"},
            },
        }
    )


_configure_logging()
logger = logging.getLogger(__name__)


async def _request_logging_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex[:12])
    start = datetime.now(timezone.utc)
    response = await call_next(request)
    elapsed = (datetime.now(timezone.utc) - start).total_seconds() * 1000
    logger.info(
        "method=%s path=%s status=%s duration=%.1fms request_id=%s",
        request.method,
        request.url.path,
        response.status_code,
        elapsed,
        request_id,
    )
    response.headers["X-Request-ID"] = request_id
    return response


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    try:
        from app.services.redis_store import get_redis, close_redis

        await get_redis()
    except Exception:
        pass
    yield
    try:
        from app.services.redis_store import close_redis

        await close_redis()
    except Exception:
        pass


app = FastAPI(
    title="Pomelo",
    description="基于文档的学习平台",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_exception_handler(Exception, global_exception_handler)

app.middleware("http")(_request_logging_middleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(libraries.router, prefix="/api")
app.include_router(departments.router, prefix="/api")
app.include_router(approvals.router, prefix="/api")
app.include_router(ai_prompts.router, prefix="/api")
app.include_router(study_materials.router, prefix="/api")
app.include_router(exams.router, prefix="/api")
app.include_router(study_assignments.router, prefix="/api")
app.include_router(tags.router, prefix="/api")
app.include_router(question_banks.router, prefix="/api")
app.include_router(drills.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(videos.router, prefix="/api")


@app.get("/health")
async def health_check():
    return JSONResponse({"status": "healthy"})


@app.get("/ready")
async def ready_check():
    return JSONResponse({"status": "ready"})
