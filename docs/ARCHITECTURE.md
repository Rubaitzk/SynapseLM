# Architecture

SynapseLM uses a **modular monolith** architecture for V1.

## Layers
- **Frontend**: React, TypeScript, Vite.
- **REST API / Backend**: Python, FastAPI, Pydantic, SQLAlchemy.
- **Realtime Layer**: WebSockets, Redis (for ephemeral state).
- **Database**: PostgreSQL (source of truth for persistent state).

## Data Flow
- REST API: Authentication, CRUD, retrieving history, persistent state modifications.
- WebSockets: Presence, typing indicators, real-time message notifications, AI streaming events.

## Invariants
1. PostgreSQL is authoritative for persistent domain state.
2. Redis is not authoritative for domain state.
3. REST and WebSockets have separate responsibilities.
4. The frontend never accesses the LLM provider directly.
5. Authorization is enforced server-side.
