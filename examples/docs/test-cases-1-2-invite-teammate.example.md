# Test cases: Invite a teammate (Day 1, Task 2)

Author: QA UAT. Format — [roles/qa-uat.md](../../roles/qa-uat.md). Scenario source: [scenarios-1-2-invite-teammate.example.md](scenarios-1-2-invite-teammate.example.md).
Input for: QA E2E. Reference: Slack + common sense.

## TC-INVITE-001: Sending an invitation (happy path)

**Priority:** P0 Critical
**Source:** Scenario 1.1 from scenarios-1-2-invite-teammate.md
**Automation:** Yes

### Precondition
- The user is logged in, their team page is open.
- There is no invite for `newdev@example.com` in the team.

### Steps

| # | Given (state) | When (action) | Then (expectation) | UI selector |
|---|-------------------|-----------------|-----------------|-------------|
| 1 | Team page | Click "Invite teammate" | Modal is open, the email field is focused and empty, the Send button is gray/disabled | inviteButton, inviteModal, inviteEmailInput, inviteSubmit |
| 2 | Modal is open | Enter `newdev@example.com` | Send button is enabled | inviteEmailInput, inviteSubmit |
| 3 | Email entered | Click Send | Send shows a spinner and is disabled; then a toast "Invitation sent to newdev@example.com"; the modal closes | inviteSubmit, inviteToast |

### Test data
- Email: `newdev@example.com`

### Pass criteria
- [ ] The toast with the exact text is shown and auto-dismisses.
- [ ] The modal is closed, focus returns to the page.
- [ ] **Server-side check:** an `Invite{email:"newdev@example.com", status:"pending"}` appeared in the DB in the correct tenant.

## TC-INVITE-002: Email validation (Send button blocked)

**Priority:** P1 High
**Source:** Scenario 1.2 from scenarios-1-2-invite-teammate.md
**Automation:** Yes

### Precondition
- The invite modal is open.

### Steps

| # | Given (state) | When (action) | Then (expectation) | UI selector |
|---|-------------------|-----------------|-----------------|-------------|
| 1 | Email field is empty | — | Send button is disabled | inviteEmailInput, inviteSubmit |
| 2 | Email field is empty | Enter `not-an-email` | Send button remains disabled | inviteEmailInput, inviteSubmit |
| 3 | Invalid input | Fix to `ok@example.com` | Send button becomes enabled | inviteEmailInput, inviteSubmit |

### Test data
- Invalid: `not-an-email`; valid: `ok@example.com`

### Pass criteria
- [ ] With empty or invalid input, submission is impossible (no request goes to the API).

## TC-INVITE-003: Repeat invitation (409)

**Priority:** P1 High
**Source:** Scenario 1.3 from scenarios-1-2-invite-teammate.md
**Automation:** Yes

### Precondition
- `dup@example.com` already has a pending invite in this team (create via API in setup).

### Steps

| # | Given (state) | When (action) | Then (expectation) | UI selector |
|---|-------------------|-----------------|-----------------|-------------|
| 1 | Modal is open | Enter `dup@example.com`, click Send | Modal doesn't close; inline error under the field "This person already has a pending invite" | inviteEmailInput, inviteSubmit, inviteError |
| 2 | Error shown | Change email to `fresh@example.com` | Error disappears, Send is enabled | inviteEmailInput, inviteError, inviteSubmit |

### Test data
- Duplicate: `dup@example.com` (pending invite created in setup); new: `fresh@example.com`

### Pass criteria
- [ ] The duplicate does not create a second invite (server-side check: exactly one pending for `dup@example.com`).
- [ ] The error message is visible to the user and disappears when fixed.
