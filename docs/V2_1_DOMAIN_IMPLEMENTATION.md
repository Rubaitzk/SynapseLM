# SynapseLM V2.1: Domain & Database Implementation

This document details the implementation of the V2.1 persistence layer for the SynapseLM collaborative AI workspace, establishing the foundation for conversation sharing, access requests, and conversation branching.

## 1. Context and Goals

This phase successfully implements the persistent data models required by the V2 architecture (`docs/V2_ARCHITECTURE_AUDIT.md`) without breaking existing V1.5 functionality. 

- **Sharing:** Users can generate unique share links for a conversation.
- **Participation:** Non-owners can request access to a shared conversation, which creates an isolated branch conversation until the owner approves.
- **Team Semantics Maintained:** Existing `owner_id` and `team_id` paradigms were rigorously preserved.
- **Safe Snapshot Boundaries:** A robust `sequence_id` has been introduced on messages to determine deterministic snapshots, rather than relying on race-condition-prone timestamps.

## 2. Schema Additions

### Conversations
Added branching and lifecycle metadata to the `conversations` table:
- `parent_conversation_id`: Points to the canonical conversation if this is a branch.
- `snapshot_sequence_id`: Captures the sequence boundary of the parent conversation at the moment the branch was created.
- `lifecycle_state`: Tracks whether the conversation is `active`, `archived`, or `deleted`.

### Messages
Added monotonic snapshotting to the `messages` table:
- `sequence_id`: A monotonically increasing integer unique within the database (via a sequence `messages_sequence_id_seq`).
  - *Why?* Timestamps are prone to race conditions under high concurrency. Using a DB-backed sequence ensures a rigid, totally ordered timeline, guaranteeing exact snapshots for branches.

### Conversation Shares
Created `conversation_shares` to manage generated links.
- `token_hash`: Secure SHA-256 hash of the generated share token (plaintext tokens are never stored, only provided once to the creator).
- `is_active`: Allows revoking shares without deleting historical data.
- `expires_at`: Optional temporal limit on the share.

### Conversation Access Requests
Created `conversation_access_requests` to handle the transition from "shared access" to "approved collaboration".
- `share_id`: The share through which the request was made.
- `requester_id`: The user asking for access.
- `branch_conversation_id`: The isolated child conversation where the requester interacts pending approval.
- `status`: Lifecycle of the request (`pending`, `accepted`, `rejected`, `cancelled`).
- *Constraint*: A partial unique index guarantees a user can only have one `pending` request per share.

## 3. Token Security Strategy

Tokens will be generated securely in application logic using high-entropy randomness (`secrets.token_urlsafe(32)`). They will be hashed (e.g., `hashlib.sha256`) before being persisted to `conversation_shares.token_hash`. This ensures that even if the database is compromised, valid share tokens cannot be stolen. The plaintext token will only be returned by the REST API at the exact moment of creation.

## 4. Known Environment Limitations (Important)

Due to infrastructure limitations in the current environment (lack of a running Docker daemon and PostgreSQL instance), the following constraints applied to this implementation phase:

1. **Manual Alembic Migration:** Because the existing migration history leverages PostgreSQL-specific operations (e.g., `ALTER TABLE ... DROP NOT NULL`), SQLite could not be used as a fallback to autogenerate migrations. The migration file (`1070bc8fa328_add_v2_1_domain_models.py`) was written manually.
2. **Migration Testing:** The upgrade and downgrade paths for the Alembic migration could not be executed or tested against a live database. 
3. **Constraint Validation:** Advanced constraints, such as the `postgresql_where` partial unique index on access requests, could not be tested locally via `pytest` because SQLite does not parse this syntax. Model-level unit tests were added to verify Python object instantiation and defaults, but DB-level constraints require a live Postgres environment.

These factors must be considered before deploying these changes to a live staging environment, where a dry-run migration test should be performed first.

## 5. Next Phases

Phase V2.2 will leverage these entities to build:
- REST endpoints for creating/revoking shares.
- REST endpoints for requesting and approving access.
- Domain logic for copying the context of the canonical conversation up to the `snapshot_sequence_id` into the child branch context.
