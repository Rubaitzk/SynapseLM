# SynapseLM V2.11 Release Acceptance & Stabilization Report

**Version**: 2.11.0  
**Date**: October 2026  
**Scope**: Bug Fix Stabilization for Request Lifecycle, Decision Notifications & Responsive Sidebar  
**Target Environment**: Pre-deployment verification (Local / Staging)

---

## 1. Executive Summary

During actual use of the V2.9/V2.10 collaboration and sharing features, three critical bugs were reported:
1. **Bug 1**: Admin/Owner encountered `HTTP 400 Bad Request` (`Only pending requests can be accepted`) when attempting to accept or reject access requests.
2. **Bug 2**: Requester received no real-time or persistent notification indicating whether their request had been accepted or rejected.
3. **Bug 3**: The right sidebar in `ConversationView.tsx` broke across viewport sizes (particularly when browser DevTools was docked, shrinking viewport width below 1024px).

All three bugs were traced to root cause with verifiable evidence from both the database and the codebase, resolved cleanly without altering core domain semantics, verified with 51 passing backend tests and a successful production build.

---

## 2. Root Cause Analysis & Evidence

### Bug 1: Request Lifecycle & HTTP 400 on Accept/Reject

- **Reported Error**:
  ```text
  ConversationView.tsx:623 POST http://localhost:5173/api/conversations/983796c5-3350-487a-98f9-0fac50d5954a/requests/4737e096-6f3d-4a88-8236-b6f7df141869/accept 400 (Bad Request)
  "Only pending requests can be accepted"
  ```
- **Database Investigation & Evidence**:
  Direct inspection of the development database for request `4737e096-6f3d-4a88-8236-b6f7df141869` revealed:
  ```python
  Request found: <ConversationAccessRequest id='4737e096-6f3d-4a88-8236-b6f7df141869'>
  Status: RequestStatus.rejected
  ```
  The record was **already in the `rejected` status**.
- **Why Was It Displayed with an "Accept" Button?**:
  1. `backend/app/crud/crud_request.py`: `get_conversation_requests(db, conversation_id)` did not filter by `status == RequestStatus.pending`. It returned **all** historical requests (pending, accepted, rejected, cancelled).
  2. `frontend/src/pages/ConversationView.tsx`: Rendered all returned requests under `"Pending Requests ({requests.length})"`. Even though the request had already been rejected (or accepted), it was rendered with active "Accept" and "Reject" buttons.
  3. No button loading state: `<Button onClick={() => handleRequestAction(req.id, 'accept')}>` had no disabled state while awaiting server response. A rapid click sent concurrent requests; the first transitioned the status, and the second was rejected with `HTTP 400`.
- **Solution**:
  - `crud_request.py`: Updated `get_conversation_requests` with an optional `status: Optional[RequestStatus] = None` query filter, defaulting to returning ordered by `created_at DESC`.
  - `backend/app/api/conversations.py`: Exposed `GET /api/conversations/{id}/requests?status=...` query parameter to allow server-side filtering.
  - `frontend/src/pages/ConversationView.tsx`: Filtered requests with `useMemo(() => requests.filter(r => r.status === 'pending'), [requests])` so only genuinely pending requests are displayed in the "Pending Requests" card list and notification badge.
  - Added `actionLoading[reqId]` state disabling Accept/Reject buttons during submission to eliminate double-submission races.
  - Added participant deduplication in `accept_request` to ensure duplicate participant rows are never created.

---

### Bug 2: Missing Requester Decision Notifications

- **Root Cause**:
  1. **Sparse WebSocket payloads**: In `conversations.py`, `reject_request` omitted `requester_id` and `conversation_title` from its broadcast payload. `accept_request` omitted `canonical_conversation_id` and `conversation_title`.
  2. **Passive Frontend Listener**: In `ConversationView.tsx`, the WebSocket `onmessage` listener for `request.accepted` and `request.rejected` merely re-fetched requests and participants without ever presenting a toast, banner, or notification to the user (`addToast` was never called).
  3. **No Branch Metadata State on Load**: When a requester navigated to or refreshed their branch, there was no endpoint or UI banner informing them whether their collaboration request was `pending`, `accepted`, or `rejected`.
- **Solution**:
  - `backend/app/api/conversations.py`:
    - Enriched both `request.accepted` and `request.rejected` broadcasts to include `status`, `request_id`, `requester_id`, `branch_id`, `canonical_conversation_id`, and `conversation_title`.
    - Added `GET /api/conversations/{id}/branch-request` endpoint allowing branch owners to inspect their collaboration request status on load or refresh.
  - `frontend/src/pages/ConversationView.tsx`:
    - In WebSocket listener: when `data.requester_id === user?.id`, triggers instant toasts:
      - Accepted: `"Your collaboration request was approved! You are now a participant in \"{title}\"."` (with auto-refresh of conversation and participants).
      - Rejected: `"Your collaboration request for \"{title}\" was declined. You can continue chatting privately in this branch."`
    - Added reactive Branch Status Banners at the top of the chat:
      - **Approved**: Emerald banner with a direct `"Open Main Conversation →"` button.
      - **Pending**: Amber banner stating messages remain private until approved.
      - **Declined**: Subtle banner informing that branch can continue privately.

---

### Bug 3: Responsive Right Sidebar Across Viewport Sizes

- **Root Cause**:
  - In `ConversationView.tsx`, the sidebar container was declared as:
    ```tsx
    <div className="hidden lg:flex w-72 flex-col bg-white border-l border-gray-200 shrink-0">
    ```
  - When viewport width was `< 1024px` (such as on tablets, mobile screens, or desktop windows with browser DevTools docked), `hidden` suppressed the sidebar entirely, making the toggle button non-functional.
  - Conversely, without an overlay abstraction, an inline sidebar on narrow screens would crush the message layout horizontally.
- **Solution**:
  - Transformed the sidebar into a dual-mode responsive layout:
    - **Wide viewports (`>= lg`, >= 1024px)**: Inline static panel (`lg:static lg:w-72 lg:z-auto lg:shadow-none`).
    - **Narrow viewports / DevTools open (`< lg`, < 1024px)**: Rendered as a slide-out drawer (`fixed inset-y-0 right-0 z-50 w-80 max-w-[85vw] shadow-2xl`) paired with a semi-transparent backdrop (`fixed inset-0 bg-black/30 backdrop-blur-xs z-40 lg:hidden`).
    - Added a clear `Close` (`<X size={18} />`) button in the header visible on mobile/narrow viewports, plus click-outside backdrop dismissal.

---

## 3. Test & Build Verification

### Backend Automated Test Suite
- Test file added: `backend/tests/test_v2_11_lifecycle.py`
  - `test_v2_11_request_lifecycle_and_state_machine`:
    - Verifies multi-user branch requests.
    - Verifies `?status=pending`, `?status=accepted`, `?status=rejected` query filtering.
    - Verifies non-owner authorization rejection (403).
    - Verifies idempotency guards on already-accepted (400) and already-rejected (400) requests.
    - Verifies `GET /api/conversations/{id}/branch-request` endpoint.
  - `test_v2_11_websocket_decision_notifications`:
    - Verifies WebSocket emission of enriched decision payload to branch channel.
- Complete pytest run: **51 passed, 0 failed**.

### Frontend Production Build
- Command: `npm run build` (`tsc -b && vite build`)
- Result: **Clean build in 2.78s** (`dist/assets/index-D8R6xbgP.js`, `dist/assets/index-OreMUpni.css`).

---

## 4. Verification Checklist

| Requirement | Status | Verification Details |
|---|---|---|
| Request Lifecycle State Machine | ✅ Verified | Only pending requests can be accepted/rejected; subsequent attempts rejected with explicit detail |
| DB Request Status Filtering | ✅ Verified | `get_conversation_requests` supports optional `status` filter; defaults to descending order |
| Pending Requests UI Filtering | ✅ Verified | Frontend filters `requests.filter(r => r.status === 'pending')` |
| Button Debouncing & Loading | ✅ Verified | Buttons disabled with `Processing...` state during API submission |
| Realtime Requester Notifications | ✅ Verified | WebSocket broadcasts enriched payload; frontend shows success/info toasts |
| Branch Status Banners | ✅ Verified | Top banner displays Approved / Pending / Rejected states with link to main conversation |
| Responsive Sidebar Layout | ✅ Verified | Inline on wide screens, slide-out drawer with backdrop on `< lg` / DevTools viewports |
| Regression Test Suite | ✅ Verified | All 51 backend tests pass; frontend TypeScript build succeeds |
