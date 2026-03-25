from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.db.database import engine, Base
from app.db import models

# Create all tables on startup (safe to call repeatedly — only creates if missing)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    # Disable docs in production via env var for security
    docs_url="/docs" if getattr(settings, "ENVIRONMENT", "production") != "production" else None,
    redoc_url=None,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
# Vercel deploys have dynamic preview URLs, so we use allow_origin_regex for them.
# Render backend must have FRONTEND_URL set in its environment variables.

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "https://placment-prediction-model.vercel.app",
    "https://campushire.vercel.app",
]

if getattr(settings, "FRONTEND_URL", None):
    frontend = settings.FRONTEND_URL.rstrip("/")
    if frontend not in ALLOWED_ORIGINS:
        ALLOWED_ORIGINS.append(frontend)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    # Catches all Vercel preview deployments automatically
    allow_origin_regex=r"https://(placment-prediction-model|placment-prediction-model-.*|campushire.*)\.vercel\.app",
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With"],
)

# ── API router ────────────────────────────────────────────────────────────────
# MUST be registered before the OPTIONS catch-all below.
# MUST include whatif router before analysis router inside app/api/main.py
# so /analyse/whatif is matched before /analyse/{submission_id}.

from app.api.main import api_router
app.include_router(api_router, prefix=settings.API_V1_STR)


# ── Health check (used by Render's health check URL setting) ──────────────────

@app.get("/health")
def health_check():
    return {"status": "ok", "project": settings.PROJECT_NAME}


# ── Manual CORS preflight safety net ─────────────────────────────────────────
# CORSMiddleware handles preflights correctly; this is a fallback for
# edge cases where the middleware is bypassed. Must come AFTER routers.

@app.options("/{rest_of_path:path}")
async def preflight_handler(request: Request, rest_of_path: str):
    origin = request.headers.get("origin", "")
    return JSONResponse(
        content={"status": "ok"},
        headers={
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH",
            "Access-Control-Allow-Headers": "Authorization, Content-Type, Accept, Origin, X-Requested-With",
            "Access-Control-Max-Age": "86400",
        },
    )
