# V2.4 WebSocket Event Contract

This document outlines the real-time event broadcasting architecture for SynapseLM, detailing the event envelopes, payload schemas, authorization rules, and delivery semantics.

## 1. Connection and Authorization
WebSocket connections are established at `/ws/{conversation_id}?token={jwt_token}`.
- **Authentication**: The JWT token is validated to identify the user.
- **Authorization**: The user must be a participant of the target conversation. Unauthorized attempts will be closed with `1008 Policy Violation`.
- **Delivery Scope**: Events are strictly bound to the `conversation_id` channel. Users only receive events for conversations they have explicitly connected to and are authorized to access.

## 2. Event Envelope
All events sent to clients follow this standard JSON envelope:
```json
{
  "event": "<event_name>",
  "conversation_id": "<uuid>",
  ... // event-specific payload
}
```

## 3. Core Chat Events
Already supported events:
- `presence.joined`: User connected to the WebSocket. `{"user_id": "...", "user_name": "..."}`
- `presence.left`: User disconnected all sessions from the WebSocket. `{"user_id": "...", "user_name": "..."}`
- `typing.started` / `typing.stopped`: User typing indicator. `{"user_id": "...", "user_name": "..."}`
- `message.created`: New message persisted. `{"message": {<MessageResponse>}}`
- `assistant.response.started` / `delta` / `completed` / `failed`: AI generation stream.

## 4. Lifecycle & Membership Events (New)
These events correspond to committed database transactions. They must NEVER be broadcast before the transaction commits successfully.

- `participant.added`: Broadcast to the conversation when a new user is added.
  - Payload: `{"user_id": "<uuid>"}`
- `participant.removed`: Broadcast to the conversation when a user is removed (also forces the removed user's active WebSocket to close).
  - Payload: `{"user_id": "<uuid>"}`
- `conversation.deleted`: Broadcast when the conversation is deleted (forces all clients to disconnect).

## 5. Access Request Events
Access requests involve interactions between a parent conversation (the shared one) and a branch conversation (created by the requester). 

- `request.created`: Emitted when a user requests to merge their branch access back to the parent conversation.
  - **Target**: Parent conversation (notifies owner/participants of the request).
  - **Payload**: `{"request_id": "<uuid>", "requester_id": "<uuid>", "branch_id": "<uuid>"}`
  
- `request.accepted`: Emitted when the owner approves the access request.
  - **Target 1**: Parent conversation (notifies existing participants).
  - **Target 2**: Branch conversation (notifies the requester who is currently subscribed to their branch).
  - **Payload**: `{"request_id": "<uuid>", "requester_id": "<uuid>"}`
  *(Note: This state change also implicitly triggers `participant.added` in the parent conversation).*

- `request.rejected` / `request.cancelled`: Emitted when the request is rejected or cancelled.
  - **Target 1**: Parent conversation.
  - **Target 2**: Branch conversation.
  - **Payload**: `{"request_id": "<uuid>", "status": "rejected|cancelled"}`

## 6. Delivery Semantics and Limitations
- **At-Most-Once Delivery**: The current architecture uses Redis Pub/Sub for multi-worker delivery. If a client is disconnected when an event is fired, the event is lost.
- **Reconnection**: Clients must fetch the canonical state via REST API upon reconnection to recover any missed events or messages.
- **Transaction Binding**: Backend routes must issue broadcasts *after* `db.commit()`. If an operation fails and rolls back, the event must not be sent.
