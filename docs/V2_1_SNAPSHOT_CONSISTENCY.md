# SynapseLM V2.1: Snapshot Consistency and Domain Invariant Audit

## 1. Executive Summary
This document outlines the database-enforced strategy used to guarantee that conversation branches receive an exact and consistent snapshot of canonical conversation history, and that single-level branching invariants are strictly maintained.

## 2. Snapshot Consistency Strategy

### The Race Condition Problem
A global PostgreSQL sequence (`messages_sequence_id_seq`) is used to assign `sequence_id` to messages. However, `sequence_id` allocation order does not necessarily match transaction commit order. If Transaction A and B insert messages into the same conversation concurrently, A might get sequence `5` and B might get sequence `6`. If B commits before A, and a branch is created taking snapshot `6`, it expects all messages up to `6`. When A finally commits, its message (`5`) will retroactively appear in the branch's snapshot, causing severe data consistency violations.

### The Solution: Conversation-Level Locking (`SELECT FOR UPDATE`)
To guarantee that `sequence_id` order exactly matches commit order within any single conversation, we use PostgreSQL row-level locks on the `conversations` table.

1. **Message Creation**: Before a message is inserted, `create_message` executes a `SELECT FOR UPDATE` on the conversation row. 
2. **Branch Creation**: Before a branch computes the `snapshot_sequence_id`, `create_branch` executes a `SELECT FOR UPDATE` on the canonical conversation row.

**Behavior under Concurrency:**
- **Concurrent Inserts**: If two transactions try to insert messages into the same conversation, the first transaction acquires the row lock. The second transaction blocks until the first commits. This completely serializes writes to a single conversation, eliminating the race condition.
- **Rollbacks / Retries**: If a transaction allocating `sequence_id = 5` rolls back, sequence `5` is lost globally. However, because writes to the conversation were locked, the next successful message in that conversation will receive `sequence_id = 6`. The snapshot logic (`sequence_id <= snapshot_sequence_id`) handles gaps natively, so rollbacks do not affect snapshot integrity.
- **Simultaneous Branch Creations**: Multiple branch creations only require a read of the `sequence_id` but we still acquire a `FOR UPDATE` lock to serialize them against incoming message writes. This guarantees that a snapshot boundary corresponds perfectly to a committed state.

## 3. Single-Level Branching Invariant

The product requirement dictates that branches must be single-level (a branch cannot have a child branch).

**Enforcement:**
- **Application Logic**: The `create_branch` method explicitly asserts that the parent conversation has `parent_conversation_id == None`. If it does not, it raises a `ValueError("single-level branching invariant violated")`. 
- **Deletion Cascade**: The schema uses `ON DELETE CASCADE` on `parent_conversation_id` (corrected via migration `6fb800001c1c`). This ensures that if a canonical conversation is deleted, all its branches are automatically deleted. This is critical because `ON DELETE SET NULL` would orphan the branch, turning it into a canonical conversation and silently breaking the invariant.

## 4. Lifecycle Semantics
The `deleted` state has been reconciled. It is now natively defined in the PostgreSQL ENUM `lifecyclestate`. This allows soft-deletion workflows to operate gracefully without schema errors.
