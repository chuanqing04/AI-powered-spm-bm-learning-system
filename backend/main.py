import os
import asyncio
from pathlib import Path

import database

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from routers import essay, comprehension, speaking, auth, dashboard, home, latihan, listening
from AI_chatbot.router import router as ai_router
from jobs.session_expiry import session_expiry


app = FastAPI(
    title="BM SPM AI Assessment API",
    description="Backend for AI-powered Bahasa Melayu SPM assessment system",
    version="1.0.0",
)


# ─── STATIC AUDIO FILES ────────────────────
LISTENING_AUDIO_DIR = Path("uploads/listening")
LISTENING_AUDIO_DIR.mkdir(parents=True, exist_ok=True)

app.mount(
    "/audio/listening",
    StaticFiles(directory=str(LISTENING_AUDIO_DIR)),
    name="listening_audio",
)


# ─── DATABASE STARTUP ────────────────────
@app.on_event("startup")
def startup():
    database.connect_mongo()
    asyncio.create_task(session_expiry())


# ────── MIDDLEWARE ────────────────────
frontend_origins = [
    origin.strip()
    for origin in os.getenv("FRONTEND_ORIGINS", "").split(",")
    if origin.strip()
]

if not frontend_origins:
    frontend_origins = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=frontend_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ────── ROUTES ─────────────────────────
app.include_router(auth.router, prefix="/api/auth")
app.include_router(home.router, prefix="/api/home")
app.include_router(dashboard.router, prefix="/api/dashboard")
app.include_router(essay.router, prefix="/api/essay")
app.include_router(comprehension.router, prefix="/api/comprehension")
app.include_router(speaking.router, prefix="/api/speaking")
app.include_router(listening.router, prefix="/api/listening")
app.include_router(latihan.router, prefix="/api/latihan")
app.include_router(ai_router, prefix="/api/ai")


# ────── HEALTH CHECK ─────────────────────────
@app.get("/")
def root():
    return {"status": "ok", "message": "BM SPM API is running"}
