# V2 API Proposal

This document outlines the proposed REST API endpoints for V2 sharing and collaboration features. It strictly distinguishes share management, preview access, branching, and access requests.

## A. Share Management by Owner

### 1. Create a Share Link
`POST /conversations/{conversation_id}/shares`
- **Actor**: Conversation Owner
- **Authentication**: Required (JWT)
- **Authorization**: Must be the explicit owner of the individual conversation. Must verify the conversation is not a branch.
- **Request Body**: `{"expires_in_seconds": 86400}` (Optional)
- **Response**: `ConversationShareResponse` containing `id`, `share_token` (secure random), `is_active`, `expires_at`.
- **Idempotency**: Generates a new share each time.

### 2. List Shares
`GET /conversations/{conversation_id}/shares`
- **Actor**: Conversation Owner
- **Authentication**: Required
- **Authorization**: Must be conversation owner.
- **Response**: `List[ConversationShareResponse]`

### 3. Revoke Share
`POST /conversations/{conversation_id}/shares/{share_id}/revoke`
- **Actor**: Conversation Owner
- **Authentication**: Required
- **Authorization**: Must be conversation owner.
- **Response**: `204 No Content`
- **State Transition**: Sets `is_active = False`.

## B. Share Preview / Access by Recipient

### 4. Preview Share Metadata
`GET /shares/{share_token}`
- **Actor**: Any Authenticated User (Recipient)
- **Authentication**: Required
- **Authorization**: Validates `share_token` is active and not expired.
- **Response**: `SharedConversationPreviewResponse` (`title`, `owner_username`, `expires_at`).
- **Security Check**: MUST NOT expose conversation messages, AI configuration, or participant details.

## C. Branch / Continuation Creation

### 5. Create Continuation Branch
`POST /shares/{share_token}/branches`
- **Actor**: Recipient
- **Authentication**: Required
- **Authorization**: Validates `share_token` is active and not expired. Validates recipient is not already a canonical participant.
- **Request Body**: None
- **Response**: `ConversationResponse` (The new branch).
- **Behavior**: Creates a new `Conversation` owned by the recipient. Sets `parent_conversation_id` to the canonical conversation's ID. Sets `snapshot_at = NOW()`. Sets `lifecycle_state = ACTIVE`.

## D. Access Request Creation

### 6. Request Collaboration Access
`POST /shares/{share_token}/requests`
- **Actor**: Recipient
- **Authentication**: Required
- **Authorization**: Validates `share_token` is active and not expired. Validates recipient owns a valid branch linked to this share.
- **Request Body**: `{"branch_conversation_id": "uuid"}`
- **Response**: `AccessRequestResponse` (status="PENDING")
- **Behavior**: Creates `ConversationAccessRequest`. Broadcasts `request.created` to canonical conversation.
- **Idempotency**: Reject if a `PENDING` request already exists for this user/share combination.

### 7. Cancel Access Request
`POST /requests/{request_id}/cancel`
- **Actor**: Recipient
- **Authentication**: Required
- **Authorization**: Must be the requester.
- **Response**: `204 No Content`
- **State Transition**: `PENDING -> CANCELLED`.

## E. Owner Request Management

### 8. List Pending Requests
`GET /conversations/{conversation_id}/requests`
- **Actor**: Conversation Owner
- **Authentication**: Required
- **Authorization**: Must be conversation owner.
- **Response**: `List[AccessRequestResponse]`

### 9. Accept Request
`POST /conversations/{conversation_id}/requests/{request_id}/accept`
- **Actor**: Conversation Owner
- **Authentication**: Required
- **Authorization**: Must be conversation owner.
- **Response**: `ConversationParticipantResponse`
- **State Transition**: Atomic transaction (Request `ACCEPTED`, Branch `ARCHIVED`, canonical `ConversationParticipant` created). Broadcasts `request.accepted`.
- **Idempotency**: Fails if request is not `PENDING`.

### 10. Reject Request
`POST /conversations/{conversation_id}/requests/{request_id}/reject`
- **Actor**: Conversation Owner
- **Authentication**: Required
- **Authorization**: Must be conversation owner.
- **Response**: `204 No Content`
- **State Transition**: Request `REJECTED`. Branch remains `ACTIVE`. Broadcasts `request.rejected`.

## F. Actual Participant Management

Leverages existing V1.5 APIs. Once accepted, the recipient uses:
- `GET /conversations/{canonical_id}/messages`
- `POST /conversations/{canonical_id}/messages`
These will succeed because the user now possesses a valid `ConversationParticipant` record for the canonical conversation.
