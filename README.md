# SynapseLM

A real-time collaborative AI workspace where teams construct and interact with a shared AI context in real-time.

## Overview

SynapseLM is a full-stack application for team-based AI collaboration. Users register, form teams, create conversations, and collaborate in real time with AI-assisted streaming responses. All messages, presence, and typing indicators are synchronized live across participants via WebSockets.

## Features

### V1 (Implemented)
- **Authentication** – JWT-based registration, login, and logout
- **Teams** – Create teams, invite members, manage memberships
- **Conversations** – Create conversations within teams, manage participants
- **Real-time Messaging** – WebSocket-based message delivery with live broadcasts
- **AI Streaming** – Async LLM generation with token-by-token streaming
- **Real-time Presence** – Online status and typing indicators
- **Authorization** – Server-side enforcement for every protected resource
- **Reconnect Recovery** – Clients rehydrate state from PostgreSQL on reconnect

### V2 (Planned)
- **Conversation Sharing** – Secure share links with token-based access
- **Branch Isolation** – Recipients create isolated conversation branches with snapshot-in-time context
- **Access Requests** – Request to join canonical conversations from a branch
- **Collaborative Prompting** – Shared live prompt/draft composition
- **Member Suggestions** – AI-powered conversation improvement suggestions

## Architecture

SynapseLM follows a **modular monolith** pattern to reduce operational complexity while maintaining clean separation of concerns.

```
┌─────────────────────────────────────┐
│  Frontend: React + TypeScript + Vite │
├─────────────────────────────────────┤
│  REST API: Python + FastAPI         │
│  (Auth, CRUD, history retrieval)     │
├─────────────────────────────────────┤
│  Realtime Layer: WebSockets + Redis │
│  (Presence, typing, AI streaming)   │
├─────────────────────────────────────┤
│  PostgreSQL (Source of Truth)       │
│  Redis (Ephemeral Coordination)     │
└─────────────────────────────────────┘
```

### Core Invariants
- PostgreSQL is authoritative for all persistent domain state.
- Redis is used only for ephemeral coordination (presence, typing).
- REST and WebSockets have separate, clear responsibilities.
- The frontend never accesses the LLM provider directly; all AI calls go through the backend.
- Authorization is enforced server-side for every protected resource.

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React, TypeScript, Vite, Tailwind CSS |
| **Backend API** | Python, FastAPI, Pydantic, SQLAlchemy, Alembic |
| **Real-time** | WebSockets, Redis |
| **Database** | PostgreSQL |
| **Authentication** | JWT tokens (HS256) |
| **AI Integration** | Swappable LLM provider (OpenAI, Mock, etc.) |
| **Testing** | pytest, httpx |

## Project Structure

```
.
├── backend/          # FastAPI application
│   ├── app/          # Routes, services, models, WebSocket handlers
│   ├── alembic/      # Database migrations
│   ├── tests/        # Test suite
│   ├── requirements.txt
│   └── .env.example  # Environment variable template
├── frontend/         # React + TypeScript application
│   ├── src/          # Components, hooks, API client
│   ├── package.json
│   └── vite.config.ts
├── docs/             # Architecture & product documentation
├── docker-compose.yml
└── README.md
```

## Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+
- Docker & Docker Compose (for PostgreSQL and Redis)

### 1. Start Infrastructure
```bash
docker-compose up -d
```
This starts PostgreSQL on port `5432` and Redis on port `6379`.

### 2. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env to set your SECRET_KEY and LLM credentials

# Run migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload
```
The API will be available at `http://localhost:8000`.

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
The app will be available at `http://localhost:5173`.

## API Overview

### Authentication
| Endpoint | Description |
|----------|-------------|
| `POST /auth/register` | Register a new user |
| `POST /auth/login` | Authenticate and receive JWT |
| `POST /auth/logout` | Invalidate token |
| `GET /auth/me` | Get current user |

### Teams
| Endpoint | Description |
|----------|-------------|
| `POST /teams` | Create a team |
| `GET /teams` | List my teams |
| `GET /teams/{id}` | Get team details |
| `GET /teams/{id}/members` | List team members |

### Invitations
| Endpoint | Description |
|----------|-------------|
| `POST /teams/{id}/invitations` | Invite a user |
| `GET /invitations` | List pending invitations |
| `POST /invitations/{id}/accept` | Accept invitation |
| `POST /invitations/{id}/reject` | Reject invitation |

### Conversations
| Endpoint | Description |
|----------|-------------|
| `POST /teams/{id}/conversations` | Create a conversation |
| `GET /teams/{id}/conversations` | List team conversations |
| `GET /conversations/{id}` | Get conversation details |
| `DELETE /conversations/{id}` | Delete a conversation |

### Messages
| Endpoint | Description |
|----------|-------------|
| `GET /conversations/{id}/messages` | Fetch message history |
| `POST /conversations/{id}/messages` | Send a message |

### WebSocket
- **Endpoint:** `WS /ws/conversations/{conversation_id}?token={jwt}`
- **Purpose:** Real-time presence, typing indicators, message broadcasts, and AI streaming

## Real-time Protocol

Events are delivered in a standard envelope:

```json
{
  "event": "event.name",
  "event_id": "uuid",
  "conversation_id": "uuid",
  "actor_id": "uuid",
  "timestamp": "iso8601",
  "payload": {}
}
```

### Key Events
| Event | Description |
|-------|-------------|
| `conversation.member_joined` | User joined conversation |
| `conversation.member_left` | User left conversation |
| `presence.updated` | Online status changed |
| `typing.started` / `typing.stopped` | Typing indicators |
| `message.created` | New message broadcast |
| `assistant.response.started` | AI generation began |
| `assistant.response.delta` | AI token streaming |
| `assistant.response.completed` | AI generation finished |
| `assistant.response.failed` | AI generation error |

## Security

- **Authentication:** Secure password hashing with JWT tokens.
- **Authorization:** Server-side enforcement on every protected resource.
- **Secrets:** Stored in environment variables; `.env.example` provided as a template.
- **API Protection:** Safe CORS configuration, rate limiting, and no sensitive data in logs.
- **WebSocket Auth:** JWT passed via query parameter (standard for WebSocket handshake).

## Development Roadmap

### V1 Phases
1. Foundation – Project structure, configs, health-check
2. Authentication – Registration, login, JWT management
3. Teams & Invitations – Team CRUD, invitation workflow
4. Conversations & REST Messaging – Create conversations, REST message API
5. Realtime & AI – WebSockets, presence, typing, AI streaming

### V2 Phases
1. V2.1 – Domain + Database extensions (parent/snapshot columns, shares/requests)
2. V2.2 – Branch lifecycle + Authorization
3. V2.3 – AI Context / Branch Context assembly
4. V2.4 – Sharing + Access Request APIs
5. V2.5 – Tests + Security Hardening
6. V2.6 – Realtime Events for sharing
7. V2.7 – Frontend Integration
8. V2.8 – End-to-End Validation

## Documentation

Full architecture, domain model, API contracts, and design decisions are located in the `docs/` directory:

- [`PRODUCT.md`](docs/PRODUCT.md) – Product definition and feature boundaries
- [`ARCHITECTURE.md`](docs/ARCHITECTURE.md) – High-level system architecture
- [`AI_ARCHITECTURE.md`](docs/AI_ARCHITECTURE.md) – LLM integration design
- [`API_CONTRACT.md`](docs/API_CONTRACT.md) – V1 REST API specification
- [`REALTIME_PROTOCOL.md`](docs/REALTIME_PROTOCOL.md) – WebSocket event specification
- [`SECURITY.md`](docs/SECURITY.md) – Security model
- [`DOMAIN_MODEL.md`](docs/DOMAIN_MODEL.md) – Data entities and relationships
- [`DEVELOPMENT_PHASES.md`](docs/DEVELOPMENT_PHASES.md) – Roadmap
- V2 docs – Sharing, branching, and access request design

## License

[Add your license here]
