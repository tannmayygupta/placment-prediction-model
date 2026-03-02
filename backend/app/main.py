from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.db.database import engine, Base
from app.db import models
                                        
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# ✅ CORS — handles both localhost dev and Vercel production
# NOTE: Do NOT mix allow_origins with allow_origin_regex — use one or the other
# We use allow_origins with explicit list + wildcard fallback via middleware

ALLOWED_ORIGINS = [
    # Local development
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    # Vercel production — add ALL your Vercel URLs here
    "https://placment-prediction-model.vercel.app",
    "https://campushire.vercel.app",
]

# Add FRONTEND_URL from env if set
if getattr(settings, 'FRONTEND_URL', None):
    frontend = settings.FRONTEND_URL.rstrip("/")
    if frontend not in ALLOWED_ORIGINS:
        ALLOWED_ORIGINS.append(frontend)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"https://(placment-prediction-model|placment-prediction-model-.*|campushire.*)\.vercel\.app",
    allow_credentials=False,   # ✅ Must be False when using token auth (not cookies)
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With"],
)


@app.get("/health")
def health_check():
    return {"status": "ok", "project": settings.PROJECT_NAME}


# ✅ Manual CORS preflight handler as safety net
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
        }
    )


from app.api.main import api_router
app.include_router(api_router, prefix=settings.API_V1_STR)
