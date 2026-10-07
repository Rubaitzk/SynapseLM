# Phase 1.5 Audit and Plan

## 1. Database and Permission Model
- **Current**: 
  - `User`, `Team`, `TeamMembership` (Roles: owner, admin, member), `Invitation`
  - `Conversation`, `ConversationParticipant`, `Message`
- **Gaps**: 
  - `delete_conversation` allows ANY participant to delete the conversation.
  - No `remove_team_member` endpoint.
  - WebSocket doesn't verify `TeamMembership`, only `ConversationParticipant`.
  - AI Configuration is currently global/env-based (`settings.LLM_PROVIDER`), not conversation-based.

## 2. LLM Provider Architecture
- **Current**: 
  - `orchestrator.py` checks `settings.LLM_PROVIDER` and returns `OpenAIProvider` or `MockProvider`.
  - Providers implement `generate_response(system, messages)`.
- **Gaps**:
  - Needs conversation-level configuration.
  - Needs `ExecutionTarget` concept.
  - Needs to persist AI config in the DB (new table or columns on `Conversation`).

## 3. Action Plan

### Step 1: LLM Architecture & Database Schema
1. Update `Conversation` model to add:
   - `ai_provider` (default "mock" or "gemini")
   - `ai_model` (string)
   - `ai_execution_target` (enum: hosted, local, etc)
   - `ai_system_instructions` (text)
   - `ai_temperature` (float)
2. Generate Alembic migration.
3. Update `ConversationCreate` and `ConversationResponse` schemas.
4. Refactor `orchestrator.py` to read from the conversation's AI config instead of global settings.
5. Create abstract `LLMProvider` interface and implement `GeminiProvider` (or rename `OpenAIProvider` to whatever is appropriate, though the project seems to use `openai_provider.py` as a generic OpenAI API compatible client for local/hosted). I'll rename or refactor it cleanly.

### Step 2: Permissions and Removals
1. Update `api/conversations.py`:
   - `delete_conversation`: Restrict to Team Owner/Admin.
   - `remove_participant`: Ensure it kicks the user via Redis broadcast.
   - `update_ai_config`: New endpoint restricted to Team Admin/Owner.
2. Update `api/teams.py`:
   - Add `DELETE /teams/{team_id}/members/{user_id}`.
   - Restrict to Team Owner/Admin.
   - Action: Remove `TeamMembership`, find all `ConversationParticipant` for this user in this team, delete them, and broadcast `participant.removed` to all those conversations.

### Step 3: Frontend
1. Add Conversation settings UI (dropdowns for AI config).
2. Add Delete Conversation button.
3. Add Team Member removal button in TeamDetails.
4. Add frontend WebSocket handlers for `conversation.deleted` and `participant.removed`.
5. Error state UI.
