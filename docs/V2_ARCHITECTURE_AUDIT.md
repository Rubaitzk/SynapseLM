# V2 Architecture Audit & Revision

## 1. Executive Summary
This document provides the definitive architectural blueprint for SynapseLM V2. It finalizes the design for conversation sharing, recipient branch isolation, and explicit collaboration access requests, rigorously maintaining the conceptual boundary between sharing, participation, and team membership.

## 2. Core V2 Product Principles (The Invariants)
1. **Sharing != Participation**: A share link grants preview/branch access, NOT actual participation.
2. **Sharing != Team Membership**: Sharing a conversation does not expose team data or grant team membership.
3. **Branches are Isolated**: Recipient messages remain in their isolated branch and never auto-merge into the canonical history.
4. **Single-Level Branching**: Branches cannot be branched further.

## 3. Revised Domain Model
- **Conversation**: Existing model. Added columns: `parent_conversation_id` (Nullable FK to self), `snapshot_at` (Nullable DateTime), `lifecycle_state` (Enum: ACTIVE, ARCHIVED).
- **ConversationShare**: `id`, `conversation_id` (FK), `share_token` (secure random string), `created_by` (FK), `is_active` (Bool), `expires_at` (DateTime).
- **ConversationAccessRequest**: `id`, `share_id` (FK), `requester_id` (FK), `branch_conversation_id` (FK), `status` (Enum: PENDING, ACCEPTED, REJECTED, CANCELLED).
- **ConversationParticipant**: Unchanged. Represents *actual* full participation.

## 4. Branching & AI Context Model
**The Branch Concept:** When a recipient accesses a share link, they instantiate a `Conversation` owned by them, linked via `parent_conversation_id` to the canonical conversation, with `snapshot_at` set to the exact creation time.

**Context Assembly Rules:**
- The Context Builder constructs the canonical history by fetching messages `WHERE conversation_id = parent.id AND created_at <= branch.snapshot_at`.
- It appends branch-local messages `WHERE conversation_id = branch.id`.
- Live syncing is strictly forbidden. Parent messages newer than `snapshot_at` are ignored in the branch. Branch messages are ignored in the parent.
- This deterministic approach prevents data duplication while safely enforcing token limits and pagination.

## 5. Share and Access Lifecycle
*(Detailed extensively in V2_STATE_MACHINE.md and V2_BRANCHING_MODEL.md)*
1. **Preview**: Recipient retrieves safe metadata via the token.
2. **Branch**: Recipient creates a continuation. They chat in `ACTIVE` isolation.
3. **Request**: Recipient submits an Access Request.
4. **Acceptance (Atomic)**: Owner approves. The request becomes `ACCEPTED`, the branch becomes `ARCHIVED` (immutable), and the recipient gets a `ConversationParticipant` record in the canonical conversation. Branch messages are **not** copied. Future interactions occur in the canonical conversation.

## 6. Authorization Invariants & Security Model
- **Token Entropy**: Share tokens must use cryptographic PRNG (e.g., 32-byte url-safe strings). No integer IDs.
- **IDOR Protection**: Share token validation must precede branch creation. Access requests must validate that the recipient actually owns the provided `branch_conversation_id` and that it descends from the requested share.
- **Preview Security**: Preview endpoints must strictly filter out message history and AI configurations, returning only `title`, `owner`, and expiration.
- **Team Isolation**: Share endpoints must enforce that the share boundary does not bypass `TeamMembership` checks for team-related features. Currently, V2 focuses on sharing individual conversations.

## 7. Concurrency and Race Conditions
- **Duplicate Acceptance**: Atomic transactions and strict `status == PENDING` checks ensure a request is processed only once.
- **Duplicate Requests**: Database unique constraints (or application-level locks) prevent a user from submitting multiple pending requests for the same share.
- **Message during Acceptance**: If a recipient sends a message to the branch at the exact moment it is archived, the message insertion must fail or safely be appended just before archival lock. The client receives the state update via WebSocket and switches context.
- **Revocation during Request**: If a share is revoked while a request is in flight, the request creation endpoint must reject if `share.is_active == False`.

## 8. V3 Extension Points
This architecture guarantees safe extension vectors:
- **Deep Branching**: Removing the single-level constraint and implementing recursive context building.
- **Proposals/PRs**: Using `ARCHIVED` branch messages as selectable diffs that an owner can explicitly merge into the canonical history.
- **Collaborative Live Drafts**: Can be built entirely within the canonical conversation bounds since participants are now cleanly authorized.

## 9. Revised V2 Implementation Order
The phases strictly build upon logical dependencies:
1. **V2.1 Domain + Database**: Alter `conversations` (add parent/snapshot/lifecycle), create `shares` and `requests` tables. *(Provides the persistence layer)*
2. **V2.2 Branch lifecycle + Authorization**: Implement core CRUD rules ensuring single-level branching and branch ownership constraints. *(Establishes security invariants)*
3. **V2.3 AI Context / Branch Context**: Update LLM Orchestrator to securely assemble deterministic snapshot context. *(Proves isolation works)*
4. **V2.4 Sharing + Access Request APIs**: Implement the REST endpoints outlined in `V2_API_PROPOSAL.md`. *(Exposes the feature)*
5. **V2.5 Tests + Security Hardening**: Execute the authorization matrix and concurrency tests. *(Prevents leakage)*
6. **V2.6 Realtime Events**: Broadcast request state changes over WebSockets. *(Syncs active clients)*
7. **V2.7 Frontend Integration**: Build the Preview UI, Branch Chat UI, and Request panels. *(Delivers user value)*
8. **V2.8 End-to-End Validation**: Final integration testing of the atomic acceptance flow.

---

## FINAL REPORT SUMMARY

**1. Documents Updated**
`docs/V2_ARCHITECTURE_AUDIT.md`, `docs/V2_STATE_MACHINE.md`, `docs/V2_API_PROPOSAL.md`. Created `docs/V2_BRANCHING_MODEL.md`.

**2. Major Architectural Changes from Previous Audit**
- Branches are explicitly restricted to single-level.
- Branch context inheritance is now bound by a deterministic `snapshot_at` timestamp.
- Acceptance behavior explicitly forbids auto-merging branch messages into canonical history. Branch becomes `ARCHIVED`.

**3. Final Branch Model**
A branch is a new `Conversation` owned by the recipient with `parent_conversation_id` and `snapshot_at`. It starts `ACTIVE` and becomes `ARCHIVED` upon acceptance.

**4. Final Share/Request Model**
Shares use high-entropy opaque tokens. Requests link the Share, the Requester, and the Branch.

**5. Final Acceptance Behavior**
Atomic transaction: Request -> `ACCEPTED`, Branch -> `ARCHIVED`, Canonical Conversation -> Creates `ConversationParticipant` for recipient. No message duplication occurs.

**6. Final AI Context Behavior**
Context Builder fetches canonical messages where `created_at <= snapshot_at`, then appends branch-local messages. Live sync is explicitly prevented.

**7. Final Authorization Invariants**
Sharing != Participation. Sharing != Team Membership. Tokens only grant preview/branch capabilities.

**8. Final V2 Implementation Order**
Revised to prioritize database, authorization, and AI context logic before exposing REST APIs and Realtime events. (Phases 2.1 -> 2.8).

**9. Any remaining architectural ambiguity**
None. The deterministic `snapshot_at` boundary and atomic `ARCHIVED` state transitions resolve previous ambiguities surrounding context synchronization and merging. The architecture is fully constrained, isolated, and implementation-ready.
