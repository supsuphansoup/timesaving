from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .seed import seed_database
from .routers import auth, professors, rooms, courses, timetables, logs

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="동서대학교 강의실 시간표 배정 시스템 API",
    description="조교용 제약조건 기반 강의실 시간표 자동 배정, 비교, 반자동 수정 및 이력 관리 백엔드 API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(professors.router)
app.include_router(rooms.router)
app.include_router(courses.router)
app.include_router(timetables.router)
app.include_router(logs.router)

@app.on_event("startup")
def startup_event():
    # Auto-seed on startup if needed
    try:
        seed_database()
    except Exception as e:
        print("Startup seed warning:", e)

@app.get("/")
def root():
    return {
        "system": "동서대학교 강의실 시간표 배정 시스템 API",
        "status": "online",
        "docs_url": "/docs"
    }
