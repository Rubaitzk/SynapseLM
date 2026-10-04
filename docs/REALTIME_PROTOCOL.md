# Realtime Protocol

WebSocket endpoint: `WS /ws/conversations/{conversation_id}`

## Event Envelope
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

## Initial Event Types
- `conversation.member_joined`
- `conversation.member_left`
- `presence.updated`
- `typing.started`
- `typing.stopped`
- `message.created`
- `assistant.response.started`
- `assistant.response.delta`
- `assistant.response.completed`
- `assistant.response.failed`
