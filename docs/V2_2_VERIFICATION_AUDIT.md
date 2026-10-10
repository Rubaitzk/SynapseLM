# V2.2 Verification Audit Report

This report provides an evidence-based audit of the LLM provider architecture corrections, randomized test identifiers, and the V2.2 API implementation as requested.

## A. Provider Architecture Review

1. **`ConversationCreate` Changes**: 
   - Replaced hardcoded provider strings (`"gemini"`) with `Optional[str] = None`.
   - In `app/crud/crud_conversation.py`, the system resolves the default at database insertion: `ai_provider=conv_in.ai_provider or settings.LLM_PROVIDER`. This preserves backward compatibility for clients that don't send `ai_provider`.
2. **Provider Resolution & Trace**: 
   - Creation path: Client -> `POST /api/conversations/` -> `ConversationCreate` -> `crud_conversation.create_conversation` -> writes to DB. No LLM client is initialized at this step.
   - Message path: Client -> `POST /api/conversations/{id}/messages` -> `orchestrator.generate_assistant_response`.
   - `get_provider(conversation)` selects the implementation based on `conversation.ai_provider`.
3. **Mock Mode Behavior**: 
   - When `LLM_PROVIDER="mock"` is used, `get_provider()` drops into `else: return MockProvider()`. 
   - `MockProvider` contains no external network calls, does not check credentials, and operates deterministically.
4. **Credential Isolation & Error Handling**:
   - Initializing `GeminiProvider` explicitly checks `settings.LLM_API_KEY` and raises a clear `ValueError` if missing. It does not touch the OpenAI SDK.
   - Initializing `OpenAIProvider` explicitly checks `settings.LLM_API_KEY` and raises `ValueError`.
   - There is no silent fallback from a configured real provider to another real provider. (Note: unrecognized provider names silently fallback to `MockProvider()`, which prevents crashes but isn't explicitly strict).
5. **Future Support**: The architecture binds the provider resolution to the `Conversation` database record. A future frontend can easily pass `ai_provider` in the payload, fully bypassing system defaults and integrating cleanly with per-user credential management.

## B. Audit of Randomized Test Identifiers

1. **Why the Database Persists**: 
   - `tests/conftest.py` uses Alembic migrations and binds a `TestingSessionLocal` to `synapselm_test`. The `setup_db` fixture explicitly avoids `drop_all` / `create_all`. 
   - While the `db_session` fixture yields and then calls `session.rollback()`, the API endpoints are tested via `TestClient` utilizing `app.dependency_overrides[get_db] = override_get_db`. The `override_get_db` session commits records directly to the database and *does not roll back* at the end of the test.
2. **UUID Evaluation**:
   - Because of the missing test cleanup/teardown logic, records are permanently written to `synapselm_test`.
   - Generating `uuid4()` for emails and usernames in `test_ai.py`, `test_auth.py`, `test_conversations.py`, `test_invitations.py`, `test_teams.py`, and `test_websockets.py` prevents `IntegrityError` collisions across runs.
   - **Verdict**: UUIDs are a valid band-aid for idempotency, but they cause infinite data accumulation in the test database.
   - **Recommendation**: In the future, the test suite should ideally truncate tables before execution or employ savepoint rollbacks for the API test client.

## C. V2.2 API and Domain Constraints Audit

1. **Snapshot Consistency**: `snapshot_sequence_id` is successfully established using a table lock during branch creation (`get_conversation(db, parent_id, for_update=True)`). Message retrieval dynamically merges canonical messages (`sequence_id <= snapshot_sequence_id`) with branch-local messages, ensuring deterministic ordering without duplicating rows.
2. **Share Token Security**: `ConversationShare` generates a token, stores its hash, and returns the plaintext token only once via `POST /api/conversations/{id}/shares`. Previews limit data exposure successfully.
3. **Branch Invariants**: `create_branch()` enforces single-level branching explicitly (`if parent.parent_conversation_id is not None: raise ValueError`). The Alembic migration (`1070bc8fa328`) provides foreign key cascading. 
4. **Access Request Lifecycle**: Enforced through API endpoints and DB constraints (`uq_share_requester_pending` partial index). `ConversationAccessRequest` uses `SELECT FOR UPDATE` to prevent concurrency races during accept/reject.
5. **Archive Constraint**: V2.2 tests (`test_archived_branch_writes_fail`) prove that sending a message to a branch after it is archived returns a 400 Bad Request.

## D. Test Reproduction

- **Command Used**: `.\venv\Scripts\pytest tests\` (executed twice consecutively to prove idempotency).
- **Environment**: `TEST_DATABASE_URL` pointing to PostgreSQL (`synapselm_test`). 
- **LLM Context**: `LLM_PROVIDER=mock`, entirely offline, no Gemini credentials used.
- **Results**: Both runs passed completely (26 passed, 0 failed). No live Gemini network requests were executed (live tests skipped/untested with real credentials during this offline verification).

## Verdict
**Verified with limitations.** 
The architecture corrections and API logic strictly satisfy the V2.2 requirements, operate concurrently using database locks, and gracefully resolve providers.
**Remaining Blockers / Limitations:**
1. Live Gemini behavior has not been explicitly run against the network during this offline test cycle.
2. The test suite is now idempotent but continuously accumulates records in `synapselm_test` due to the lack of teardown truncation. 
3. Realtime WebSocket broadcast events for requests (`request.created`, `request.accepted`) are unhooked, pending the frontend integration phase.
