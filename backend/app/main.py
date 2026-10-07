from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, teams, invitations, conversations, websockets
import asyncio
from contextlib import asynccontextmanager
from app.core.realtime import manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    redis_task = asyncio.create_task(manager.listen_to_redis())
    yield
    # Shutdown
    redis_task.cancel()
    await manager.redis.close()

app = FastAPI(title="SynapseLM API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"], # Vite default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(teams.router, prefix="/api/teams", tags=["teams"])
app.include_router(invitations.router, prefix="/api/invitations", tags=["invitations"])
app.include_router(conversations.router, prefix="/api/conversations", tags=["conversations"])
app.include_router(websockets.router, tags=["websockets"]) # Websockets shouldn't necessarily have a prefix if it's just /ws

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "SynapseLM API"}
