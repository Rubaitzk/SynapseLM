# SynapseLM - Product Definition

SynapseLM is a real-time collaborative AI workspace where humans collaboratively construct and interact with a shared AI context in real-time.

## Primary V1 Goal
Build a functional full-stack application where:
- Users can register and log in.
- Users can create teams and invite others.
- Team members can create conversations.
- Participants can see conversation history and send messages.
- Backend sends conversation context to an LLM, streaming response back.
- Real-time presence (online status, typing indicators).
- Authorization to prevent unauthorized access.
- Application can be run locally.

## V1 Architecture

```text
REST
 │
 ├── persistent commands (send message)
 └── persistent queries (fetch history)

WebSocket
 │
 ├── presence (joined/left)
 ├── typing (started/stopped)
 ├── message.created (realtime broadcast)
 └── AI streaming (assistant.response.*)

PostgreSQL
 │
 └── authoritative persistent state

Redis
 │
 └── realtime/ephemeral coordination across connections/workers
```

### Realtime Lifecycle
- **Authentication**: JWT token passed via `?token=` query parameter (WebSocket standard restriction).
- **Authorization**: Extracted user is verified as an active participant of the requested conversation before socket acceptance.
- **Event Envelope**: Standardized `{"event": "type", "conversation_id": "uuid", "user_id": "uuid", ...}`
- **Message Delivery**: Backend REST call saves message to Postgres, then publishes to Redis. All connected WebSockets for that conversation receive `message.created` and reconcile based on `message.id`.
- **AI Streaming**: Backend runs async AI generation, broadcasting `assistant.response.started`, `delta`, and `completed` events to sync all clients without polling.
- **Reconnect/Recovery**: Disconnected clients fetch Postgres state on reconnect via REST `fetchMessages`, bypassing missed ephemeral websocket payloads safely.

## V1 Boundary

V1 is complete and includes:
* realtime presence
* typing indicators
* realtime messages
* concurrent message delivery
* AI streaming
* reconnect/recovery
* authorization
* persistent history
* realtime frontend state

## V2 Boundary

V2 will introduce (NOT currently implemented):
* shared live prompt/draft
* member suggestions
* append requests
* accept/reject
* suggestion lifecycle
* limits/rate controls
* collaborative prompt composition
