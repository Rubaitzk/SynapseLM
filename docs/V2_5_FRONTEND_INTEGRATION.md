# V2.5 Frontend Integration

## Overview
This document describes the frontend integration of the established V2.2 sharing APIs, V2.3 provider/model contract, and V2.4 realtime WebSocket events into the React application.

## 1. Sharing and Access Requests
- **ShareAccept Page (`/shares/:token`)**: A new dedicated route allows users visiting a share link to view the conversation preview. From here, they can either branch the conversation into their own workspace or request access to the original conversation.
- **Pending Requests UI**: `ConversationView.tsx` now fetches and displays pending access requests in the right sidebar. Authorized users can accept or reject requests directly from this UI.

## 2. Realtime WebSocket Events
The existing `RealtimeManager` WebSocket subscription in `ConversationView.tsx` was extended to handle the new V2.4 lifecycle events:
- `participant.added`: Triggers a refetch of authoritative participants list via HTTP.
- `request.created`, `request.accepted`, `request.rejected`, `request.cancelled`: Triggers a refetch of the authoritative access requests list via HTTP.
- **Reconnection Logic**: Updated the WebSocket `onclose` timer to also refetch `participants` and `requests` alongside presence and messages, ensuring resynchronization if events were missed during a connection drop (due to Redis Pub/Sub's at-most-once delivery).

## 3. Provider/Model Selection
- **AI Configuration Modal**: The configuration modal in `ConversationView.tsx` was updated to enforce the `SUPPORTED_MODELS` defined in the backend contract. The Model input is now a strict `<select>` dropdown that dynamically updates its options based on the chosen Provider.
- **Error Handling**: The `handleSend` function in `ConversationView.tsx` and the conversation creation flow in `NewConversation.tsx` now catch the specific backend error codes (`provider_configuration_missing`, `unsupported_provider`, `invalid_provider_model_combo`). If these are encountered, the user is presented with a clear Toast message explaining the configuration issue, and in `ConversationView`, the AI Configuration modal is automatically opened.

## Known Limitations & Gaps
- **Per-User Credentials**: Currently, credentials (like `LLM_API_KEY`) remain in the backend `.env`. The frontend provides a configuration UI for provider/model selection, but does not yet have a credential management screen.
- **Request Cancellation**: The UI currently focuses on accepting/rejecting requests from the conversation owner's side. A dedicated view for users to see and cancel their own outgoing requests (`/api/requests/me`) is not fully implemented in the frontend.
- **Reconnection Syncing**: While reconnection resyncs the active conversation's state, it relies entirely on HTTP endpoints rather than receiving a backlog of missed events.

## Next Steps
- Implement **V2.6 Release Hardening** and **Per-User Credential Management**, allowing individual users to securely store and use their own API keys instead of relying on the system `.env` defaults.
