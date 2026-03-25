from app.api.routes import whatif
from fastapi import APIRouter
from app.api.routes import auth, analysis, platform_proxy
from app.api.extras import router as extras_router


api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(whatif.router, prefix="/analyse", tags=["whatif"])
api_router.include_router(analysis.router, prefix="/analyse", tags=["analysis"])
api_router.include_router(platform_proxy.router, prefix="/platform", tags=["platform"])
api_router.include_router(extras_router)   # ✅ FIXED
