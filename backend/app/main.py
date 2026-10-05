from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, teams, invitations, conversations

app = FastAPI(title="SynapseLM API", version="1.0.0")

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

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "SynapseLM API"}
