# V2 Branching Model

This document outlines the core architecture for conversation branching in SynapseLM V2, a critical mechanism for safely isolating a recipient's continuation from an owner's canonical conversation.

## 1. Core Concepts

### Canonical Conversation
The original conversation owned by the creator. It contains the authoritative history.

### Branch
An isolated continuation of the canonical conversation. It is created when a recipient opens a share link and begins interacting. It is represented as a new `Conversation` entity owned by the recipient.

## 2. Invariants

### 1. Single-Level Branching
V2 strictly enforces a single level of branching.
- **Valid:** `Canonical -> Branch A`
- **Invalid:** `Canonical -> Branch A -> Branch B`
The backend enforces this by rejecting any attempt to create a share or a branch from a conversation that already has a `parent_conversation_id` set.

### 2. Snapshot Boundary
A branch inherits the canonical conversation's history exactly as it existed at the moment the branch was created.
- The snapshot boundary is deterministic, represented by a `snapshot_at` timestamp on the branch.
- **No Live Sync:** Messages added to the canonical conversation *after* `snapshot_at` do not appear in the branch.
- **No Reverse Sync:** Messages added to the branch never silently appear in the canonical conversation.
- The AI Context Builder constructs the branch's context by querying canonical messages where `created_at <= branch.snapshot_at`, and appending branch-local messages.

### 3. No Auto-Merging
Branch messages are completely isolated. They are never copied or interleaved into the canonical conversation's history. 

## 3. Branch Lifecycle

A branch operates as a state machine with the following states:

- **ACTIVE**: The default state upon creation. The recipient can send messages, interact with the AI, and request collaboration access to the canonical conversation.
- **ARCHIVED**: The branch becomes immutable. This occurs when an access request is ACCEPTED by the owner.

### Edge Cases
- **Share Revoked/Expired**: If the original share link becomes invalid, existing `ACTIVE` branches remain `ACTIVE` for isolated chatting, but the recipient can no longer submit an access request to the canonical conversation.
- **Request Rejected**: The branch remains `ACTIVE`. The recipient is isolated but can still chat with the AI using the branched context.
- **Recipient Abandons**: The branch remains `ACTIVE` indefinitely until manual cleanup or archival policies are introduced in V3.

## 4. Acceptance Transition
When an access request is **ACCEPTED**:
1. The branch transitions from `ACTIVE` to `ARCHIVED` (read-only).
2. The recipient is granted a `ConversationParticipant` record in the canonical conversation.
3. Future messages sent by the recipient go directly into the canonical conversation.
4. Past branch messages remain securely archived in the branch and are *not* copied over.

## 5. V3 Extension Points
This isolated branching model provides a robust foundation for V3 features:
- **Suggestions / Pull Requests**: An archived branch could be submitted as a "proposal," where the owner explicitly reviews and merges specific branch messages into the canonical history.
- **Branch Comparison**: UI tools to diff a branch against the canonical conversation's current state.
- **Deep Branching**: The single-level restriction can be lifted in V3 once recursive context assembly and UI depth indicators are implemented.
