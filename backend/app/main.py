"""
FastAPI application entry point.

Run with:
    uvicorn app.main:app --reload
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import Base, engine
from app.routers import auth, courses, logs, professors, rooms, semesters, timetables


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables on startup (dev convenience; use Alembic in production)
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="동서대학교 강의실 시간표 배정 시스템 API",
    description="조교 전용 강의실 시간표 자동 생성 및 관리 시스템",
    version="2.0.0",
    lifespan=lifespan,
)

# ── CORS ───────────────────────────────────────────────────────────────────────
# Include 'null' to allow requests from HTML files opened via file:// in the browser
_cors_origins = settings.cors_origins_list + ["null", "http://localhost:8000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,  # Required for session cookies
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global exception handler ───────────────────────────────────────────────────
import logging
import traceback
_logger = logging.getLogger("uvicorn.error")

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    _logger.error("Unhandled exception: %s\n%s", exc, traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "status_code": 500,
            "error_code": "ER-09",
            "message": "일시적인 시스템 오류가 발생했습니다.",
            "detail": str(exc),      # visible in dev; remove in prod
        },
    )


# ── Routers ────────────────────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(semesters.router)
app.include_router(professors.router)
app.include_router(rooms.router)
app.include_router(courses.router)
app.include_router(timetables.router)
app.include_router(logs.router)


@app.get("/", tags=["헬스체크"])
def health_check():
    return {"success": True, "message": "동서대학교 시간표 배정 시스템이 정상 동작 중입니다."}


# ── Static files (test UI) — served at http://localhost:8000/test/ ─────────────
_test_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "test")
if os.path.isdir(_test_dir):
    app.mount("/test", StaticFiles(directory=_test_dir, html=True), name="test")
