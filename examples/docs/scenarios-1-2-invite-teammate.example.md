# Scenarios: Invite a teammate (Day 1, Task 2)

Author: BA. Format — [roles/ba.md](../../roles/ba.md). Reference product: **Slack** (workspace invitation).
Input for: QA UAT → [test-cases-1-2-invite-teammate.example.md](test-cases-1-2-invite-teammate.example.md).

## 1 Inviting a teammate by email

**Status:** 🟢 Production
**Files:** `components/features/InviteTeammateModal.tsx`, `components/features/InviteButton.tsx`, `lib/api/invites.ts`, `internal/transport/invite_handler.go`, `internal/service/invite_service.go`

### Description

On the team page, the user clicks "Invite teammate", enters an email, and sends the invitation.
The system creates a pending invite and queues the email. The user sees a confirmation or a clear
error.

### Scenario 1.1: Happy path — sending an invitation

**Precondition:** the user is logged in, their team page is open, they have permission to invite.

| Step | User action | Expected result | Does Slack do the same? |
|-----|----------------------|---------------------|----------------------|
| 1 | Clicks "Invite teammate" (`inviteButton`) | The modal opens (`inviteModal`), the cursor is in the email field (`inviteEmailInput`), the Send button (`inviteSubmit`) is disabled | Yes |
| 2 | Enters `newdev@example.com` | The Send button becomes enabled | Yes |
| 3 | Clicks Send | The button shows a spinner and is disabled; after 1–2 sec — a toast (`inviteToast`) "Invitation sent to newdev@example.com", the modal closes | Yes (Slack shows "Invite sent") |

### Scenario 1.2: Edge case — invalid / empty email

**Precondition:** the modal is open.

| Step | User action | Expected result | Does Slack do the same? |
|-----|----------------------|---------------------|----------------------|
| 1 | Leaves the field empty | Send button is disabled, can't submit | Yes |
| 2 | Enters `not-an-email` | Send button remains disabled (client-side validation) | Yes |
| 3 | Fixes it to `ok@example.com` | Send button becomes enabled | Yes |

### Scenario 1.3: Error path — teammate already invited

**Precondition:** `dup@example.com` already has an active pending invite in this team.

| Step | User action | Expected result | Does Slack do the same? |
|-----|----------------------|---------------------|----------------------|
| 1 | Enters `dup@example.com`, clicks Send | The modal stays open; inline error under the field (`inviteError`) "This person already has a pending invite" | Yes (Slack: "already invited") |
| 2 | Changes to a new email | The error disappears, can submit | Yes |

### Test data

- New invite: `newdev@example.com`
- Duplicate: `dup@example.com` (requires a pre-created pending invite)
- Invalid: `not-an-email`
