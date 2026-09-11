from app.routers.auth import router as auth_router
from app.routers.phase1_core import router as phase1_router
from app.routers.phase2_workflow import router as phase2_router
from app.routers.phase3_commerce import router as phase3_router
from app.routers.phase4_advanced import router as phase4_router
from app.routers.phase5_features import router as phase5_router
from app.routers.phase6_analytics import router as phase6_router

__all__ = [
    "auth_router",
    "phase1_router",
    "phase2_router",
    "phase3_router",
    "phase4_router",
    "phase5_router",
    "phase6_router"
]
