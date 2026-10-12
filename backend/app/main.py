import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api import auth, teams, invitations, conversations, websockets, shares, requests
from app.api.endpoints import credentials
from app.core.config import settings
from app.core.realtime import manager
from app.db.session import SessionLocal
from app.services.llm.exceptions import ProviderConfigurationError

logger = logging.getLogger("synapselm.main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize background Redis listener
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION} in {settings.ENVIRONMENT} mode")
    redis_task = asyncio.create_task(manager.listen_to_redis())
    yield
    # Shutdown: Cleanly cancel background tasks and close Redis client
    logger.info("Shutting down SynapseLM API...")
    redis_task.cancel()
    try:
        await redis_task
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Error during redis listener cancellation: {type(e).__name__}")
    try:
        await manager.redis.aclose()
    except Exception as e:
        logger.error(f"Error closing redis connection: {type(e).__name__}")

app = FastAPI(
    title="SynapseLM API",
    version=settings.VERSION,
    lifespan=lifespan
)

@app.exception_handler(ProviderConfigurationError)
async def provider_configuration_exception_handler(request: Request, exc: ProviderConfigurationError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": exc.error_code,
            "provider": exc.provider,
            "detail": exc.detail
        },
    )

cors_origins = [orig.strip() for orig in settings.ALLOWED_ORIGINS.split(",") if orig.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(credentials.router, prefix="/api/credentials", tags=["credentials"])
app.include_router(teams.router, prefix="/api/teams", tags=["teams"])
app.include_router(invitations.router, prefix="/api/invitations", tags=["invitations"])
app.include_router(conversations.router, prefix="/api/conversations", tags=["conversations"])
app.include_router(shares.router, prefix="/api/shares", tags=["shares"])
app.include_router(requests.router, prefix="/api/requests", tags=["requests"])
app.include_router(websockets.router, tags=["websockets"])

@app.get("/health", tags=["health"])
def health_check():
    """Liveness probe: verifies the API process is alive and accepting requests."""
    return {"status": "ok", "service": "SynapseLM API"}

@app.get("/health/ready", tags=["health"])
async def readiness_check():
    """Readiness probe: verifies database and Redis connectivity without leaking secrets."""
    db_status = "ok"
    redis_status = "ok"
    
    # 1. Check PostgreSQL
    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
        finally:
            db.close()
    except Exception as e:
        db_status = f"unhealthy: {type(e).__name__}"
        
    # 2. Check Redis
    try:
        pong = await manager.redis.ping()
        if not pong:
            redis_status = "unhealthy: no response"
    except Exception as e:
        redis_status = f"unhealthy: {type(e).__name__}"
        
    is_ready = (db_status == "ok") and (redis_status == "ok")
    status_code = 200 if is_ready else 503
    
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if is_ready else "not_ready",
            "database": db_status,
            "redis": redis_status,
            "service": "SynapseLM API"
        }
    )
