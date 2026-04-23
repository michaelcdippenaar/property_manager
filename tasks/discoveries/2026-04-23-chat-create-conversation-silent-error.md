---
discovered_by: rentals-reviewer
discovered_during: UX-014
discovered_at: 2026-04-23
priority_hint: P2
suggested_prefix: UX
---

## What I found
`createConversation()` in `tenant/src/views/chat/ChatListView.vue` silently swallows all API errors with an empty `catch { /* ignore */ }` block. If the POST to `/tenant-portal/conversations/` fails (network error, 403, 500), the tenant taps a prompt chip or the FAB and nothing happens — no toast, no retry, no feedback.

## Why it matters
Tenants on flaky connections (common on mobile) will see zero feedback and assume the app is broken. If the error is a 403 (session expired), they will be silently stuck on the chat list with no prompt to re-authenticate.

## Where I saw it
- `tenant/src/views/chat/ChatListView.vue:84` — `catch { /* ignore */ }`

## Suggested acceptance criteria (rough)
- [ ] On API error, show a toast ("Couldn't start a chat — please try again") matching the pattern used in `ChatDetailView.vue` (`toast.error(...)`)
- [ ] If the error status is 401/403, redirect to login (or let the global axios interceptor handle it)

## Why I didn't fix it in the current task
Pre-existing pattern before UX-014; expanding the diff would mix concerns. Requires a decision on whether a global axios error interceptor should handle 401/403 uniformly across the tenant app.
