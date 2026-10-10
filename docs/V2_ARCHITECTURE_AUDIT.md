# V2 Architecture Audit & Final Revision

## 1. Executive Summary
This document provides the definitive architectural blueprint for SynapseLM V2. It finalizes the design for conversation sharing, recipient branch isolation, explicit collaboration access requests, and transactional guarantees, rigorously maintaining the conceptual boundaries between sharing, participation, and team membership.

## 2. Core V2 Product Principles (The Invariants)
1. **Sharing != Participation**: A share link grants preview/branch access, NOT actual participation.
2. **Sharing != Team Membership**: Sharing a conversation does not expose team data or grant team membership.
3. **Branches are Isolated**: Recipient messages remain in their isolated branch and never auto-merge into the canonical history.
4. **Single-Level Branching**: Branches cannot be branched further.

## 3. Revised Domain Model
- **Message**: Existing model. Added column: `sequence_id` (Integer, global auto-increment) to ensure strict monotonic ordering.
- **Conversation**: Existing model. Added columns: `parent_conversation_id` (Nullable FK to self), `snapshot_sequence_id` (Nullable Integer), `lifecycle_state` (Enum: ACTIVE, ARCHIVED).
- **ConversationShare**: `id`, `conversation_id` (FK), `token_hash` (String, SHA-256), `created_by` (FK), `is_active` (Bool), `expires_at` (DateTime).
- **ConversationAccessRequest**: `id`, `share_id` (FK), `requester_id` (FK), `branch_conversation_id` (FK), `status` (Enum: PENDING, ACCEPTED, REJECTED, CANCELLED).
- **ConversationParticipant**: Unchanged. Represents *actual* full participation.

## 4. Branching & AI Context Model
**The Branch Concept:** When a recipient accesses a share link, they instantiate a `Conversation` owned by them, linked via `parent_conversation_id` to the canonical conversation, with `snapshot_sequence_id` set to the highest `sequence_id` present in the canonical conversation at that exact moment.

**Context Assembly Rules:**
- The Context Builder constructs the canonical history by fetching messages `WHERE conversation_id = parent.id AND sequence_id <= branch.snapshot_sequence_id`.
- It appends branch-local messages `WHERE conversation_id = branch.id`.
- Live syncing is strictly forbidden. Parent messages newer than the snapshot are ignored in the branch. Branch messages are ignored in the parent.
- This deterministic sequence approach prevents data duplication and completely avoids race conditions caused by clock skew or concurrent uncommitted message inserts.

## 5. Share and Access Lifecycle
*(Detailed extensively in V2_STATE_MACHINE.md and V2_BRANCHING_MODEL.md)*
1. **Preview**: Recipient retrieves safe metadata via the token.
2. **Branch**: Recipient creates a continuation. They chat in `ACTIVE` isolation.
3. **Request**: Recipient submits an Access Request.
4. **Acceptance (Atomic)**: Owner approves. The request becomes `ACCEPTED`, the branch becomes `ARCHIVED` (immutable), and the recipient gets a `ConversationParticipant` record in the canonical conversation. Branch messages are **not** copied. Future interactions occur in the canonical conversation.

## 6. Authorization Invariants & Security Model
- **Token Entropy & Storage**: Share tokens are generated using a CSPRNG (e.g., 32-byte url-safe strings). The backend stores only the cryptographic hash (`token_hash`) of the token. The plaintext is returned only once upon creation and is never exposed in listing APIs.
- **Revocation Semantics**: Revoking a share (`is_active = False`) blocks new branch creation and new access requests. Existing active branches are not deleted; recipients can continue chatting locally but cannot request canonical access.
- **IDOR Protection**: Share token validation must precede branch creation. Access requests must validate that the recipient actually owns the provided `branch_conversation_id` and that it descends from the requested share.
- **Preview Security**: Preview endpoints must strictly filter out message history and AI configurations, returning only `title`, `owner`, and expiration.
- **Team Isolation**: Share endpoints enforce that the share boundary does not bypass `TeamMembership` checks.

## 7. Concurrency and Transaction Boundaries
- **Accept/Reject Races**: Explicit `SELECT ... FOR UPDATE` row-level locks on `ConversationAccessRequest` guarantee requests are processed precisely once.
- **Duplicate Requests**: Database partial unique index (`share_id`, `requester_id`) `WHERE status = 'PENDING'` entirely blocks spamming active requests.
- **Archival vs Message Write**: Message writes lock the `Conversation` row and verify `lifecycle_state == ACTIVE`. Concurrent acceptance safely aborts the message write.
- **Duplicate Participant Creation**: The existing `ConversationParticipant` unique constraint provides a fallback guarantee against double-insertion.
- **Realtime Events**: All Redis publish events occur *after* `db.commit()` to prevent clients from fetching uncommitted DB state.

## 8. V3 Extension Points
This architecture guarantees safe extension vectors:
- **Deep Branching**: Removing the single-level constraint and implementing recursive context building.
- **Proposals/PRs**: Using `ARCHIVED` branch messages as selectable diffs that an owner can explicitly merge into the canonical history.
- **Collaborative Live Drafts**: Can be built entirely within the canonical conversation bounds since participants are now cleanly authorized.

## 9. Revised V2 Implementation Order
The phases strictly build upon logical dependencies:
1. **V2.1 Domain + Database**: Alter `messages` (add `sequence_id`), alter `conversations` (add parent/snapshot/lifecycle), create `shares` and `requests` tables. *(Provides the persistence layer and deterministic snapshotting)*
2. **V2.2 Branch lifecycle + Authorization**: Implement core CRUD rules ensuring single-level branching and branch ownership constraints. *(Establishes security invariants)*
3. **V2.3 AI Context / Branch Context**: Update LLM Orchestrator to securely assemble deterministic sequence-based context. *(Proves isolation works)*
4. **V2.4 Sharing + Access Request APIs**: Implement the REST endpoints outlined in `V2_API_PROPOSAL.md`. *(Exposes the feature)*
5. **V2.5 Tests + Security Hardening**: Execute the authorization matrix and concurrency tests. *(Prevents leakage)*
6. **V2.6 Realtime Events**: Broadcast request state changes over WebSockets. *(Syncs active clients)*
7. **V2.7 Frontend Integration**: Build the Preview UI, Branch Chat UI, and Request panels. *(Delivers user value)*
8. **V2.8 End-to-End Validation**: Final integration testing of the atomic acceptance flow.

---

## FINAL REPORT SUMMARY

**1. Documents Updated**
`docs/V2_ARCHITECTURE_AUDIT.md`, `docs/V2_STATE_MACHINE.md`, `docs/V2_API_PROPOSAL.md`, `docs/V2_BRANCHING_MODEL.md`. All documents fully synchronize across schema, endpoints, lifecycles, and security rules.

**2. Snapshot Consistency Resolved**
Instead of relying on unstable `created_at` timestamps, the architecture introduces a globally auto-incrementing `sequence_id` to the `Message` table. Branches record a `snapshot_sequence_id`. Context building is now perfectly deterministic and transactionally safe without duplicating historical message contents.

**3. Share Revocation Defined**
Revocation (`is_active = False`) blocks new branches and requests. Existing branches remain active for local use but cannot submit requests. Existing canonical participants are completely unaffected by share revocation.

**4. Token Storage Secured**
Tokens utilize 32-byte CSPRNG generation. The backend only stores `token_hash` (e.g., SHA-256). Plaintext is strictly returned once upon creation and omitted from all subsequent fetches.

**5. Concurrency Guaranteed**
Explicit `SELECT ... FOR UPDATE` row-level locks govern Accept/Reject state changes and Branch message writes vs Archival. Partial unique indexes prevent duplicate pending requests. Redis events strictly fire post-commit.

**6. Safe to Proceed**
There are no remaining architectural ambiguities. The model successfully meets all constraints provided. Phase **V2.1 Domain + Database** can safely commence.
