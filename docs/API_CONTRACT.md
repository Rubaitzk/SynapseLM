# API Contract

RESTful APIs with consistent naming and error handling.

## Authentication
- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/logout`
- `GET /auth/me`

## Teams
- `POST /teams`
- `GET /teams`
- `GET /teams/{team_id}`
- `GET /teams/{team_id}/members`

## Invitations
- `POST /teams/{team_id}/invitations`
- `GET /invitations`
- `POST /invitations/{id}/accept`
- `POST /invitations/{id}/reject`

## Conversations
- `POST /teams/{team_id}/conversations`
- `GET /teams/{team_id}/conversations`
- `GET /conversations/{conversation_id}`
- `DELETE /conversations/{conversation_id}`

## Participants
- `GET /conversations/{id}/participants`
- `POST /conversations/{id}/participants`
- `DELETE /conversations/{id}/participants/{user_id}`

## Messages
- `GET /conversations/{id}/messages`
- `POST /conversations/{id}/messages`
