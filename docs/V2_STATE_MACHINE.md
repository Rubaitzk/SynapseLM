# V2 Sharing and Collaboration State Machine

This document defines the strict lifecycle transitions for Shares, Access Requests, and Branches in SynapseLM V2.

## 1. Conversation Share State Machine

The share token dictates the validity of new access attempts.

```mermaid
stateDiagram-v2
    [*] --> ACTIVE : Owner creates share link
    ACTIVE --> REVOKED : Owner explicitly revokes
    ACTIVE --> EXPIRED : Expiration time reached
    REVOKED --> [*]
    EXPIRED --> [*]
```

## 2. Recipient Branch State Machine

The branch governs the recipient's isolated workspace.

```mermaid
stateDiagram-v2
    [*] --> ACTIVE : Recipient initiates continuation
    
    state ACTIVE {
        [*] --> Chatting
        Chatting --> Chatting : Isolated messages
    }
    
    ACTIVE --> ARCHIVED : Access Request is ACCEPTED
    ARCHIVED --> [*] : Read-only history
```

## 3. Access Request State Machine

The access request governs the explicit collaboration agreement.

```mermaid
stateDiagram-v2
    [*] --> PENDING : Recipient requests access
    
    PENDING --> ACCEPTED : Owner approves
    PENDING --> REJECTED : Owner declines
    PENDING --> CANCELLED : Recipient withdraws
    
    ACCEPTED --> [*]
    REJECTED --> [*]
    CANCELLED --> [*]
```

## 4. Atomic Cross-Entity Acceptance Transition

When an owner accepts a pending access request, a critical cross-entity transition occurs. This **MUST** be executed as an atomic database transaction to prevent corrupted state.

```mermaid
sequenceDiagram
    participant Owner
    participant DB as Database Transaction
    participant Req as AccessRequest
    participant Branch as Recipient Branch
    participant Canonical as Canonical Conversation

    Owner->>DB: Accept Request
    activate DB
    DB->>Req: Update status = ACCEPTED
    DB->>Branch: Update lifecycle_state = ARCHIVED
    DB->>Canonical: Create ConversationParticipant(recipient)
    DB-->>Owner: Transaction Commit
    deactivate DB
```

### Transition Table (Acceptance)

| Entity | Pre-State | Post-State | Effect |
| :--- | :--- | :--- | :--- |
| **AccessRequest** | `PENDING` | `ACCEPTED` | Request is finalized. |
| **Branch** | `ACTIVE` | `ARCHIVED` | Recipient can no longer send messages to the branch. |
| **Canonical Conv** | Recipient is unauthorized | Recipient is `Participant` | Recipient can now read live canonical messages and write directly to the canonical conversation. |

### Edge Case Constraints
- A request can only transition to `PENDING` if the associated `ConversationShare` is `ACTIVE`.
- If a `ConversationShare` becomes `REVOKED`, existing `PENDING` requests may remain pending or be auto-rejected depending on product policy, but new requests are blocked.
- A `Branch` remains `ACTIVE` if a request is `REJECTED` or `CANCELLED`, allowing the user to continue isolated interaction.
