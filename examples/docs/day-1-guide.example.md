# Day 1 — Invite a teammate by email

**Goal for the day:** an end-to-end "invite a teammate to the team by email" feature — from API to UI, with tests.

**Precondition:** the project is initialized (Go API + Next.js), migrations apply, `make test` is green.

Commands for entering roles (the digit key is in [CLAUDE.md](../CLAUDE.example.md)):

- `1 1 1` — developer takes Task 1 (backend).
- `1 1 2` — developer takes Task 2 (frontend).
- `0 1 1` — reviewer reviews Task 1.
- `3 1 2` — BA writes scenarios for the Task 2 feature → file `scenarios-1-2-…` (named after the feature it describes; see the `<DT>` convention in [core/task-protocol.md](../../core/task-protocol.md)).
- `4 1 2` — QA UAT turns the scenarios into test cases → `test-cases-1-2-…`.
- `2 1 2` — QA E2E writes E2E tests from the test cases.

---

## Task 1 — Backend: POST /api/v1/invites endpoint

Create an endpoint that opens an invite and queues it for the invitation email. The tenant is determined from the auth context (see [domain/b2b-saas.md](../../domain/b2b-saas.md), [architecture/multi-tenant.md](../../architecture/multi-tenant.md)).

**Affected files:**

- `internal/domain/invite.go` (new) — the `Invite` entity, statuses.
- `internal/service/invite_service.go` (new) — invite-creation business logic.
- `internal/transport/invite_handler.go` (new) — HTTP handler.
- `internal/repository/queries/invite.sql` (new) — sqlc queries.
- `internal/transport/router.go` (edit) — route registration.
- tests next to each file.

### Prompt for Claude Code

~~~
Implement POST /api/v1/invites in the Go project per the rules in stack/go.md and core/.

Contract:
- Input: JSON {"email": string}. The tenant comes from ctx (middleware already sets tenant_id), NOT from the request body.
- Validation: email per RFC; empty/invalid → 400 with {"error":"invalid email"}.
- If an active invite for this email in this tenant already exists → 409 {"error":"invite already pending"}.
- Success: create an Invite{id, tenant_id, email, status="pending", created_at} record, return 201 with the invite body.
- Side effect: enqueue an email-sending job via InviteService.enqueueEmail (an interface; the real send is a logger stub in this task).

Requirements:
- Layers: transport → service → repository, no reverse imports (core/code-quality.md).
- Errors wrapped via %w, typed (ValidationError, ConflictError).
- sqlc for queries, no inline SQL, prepared statements.
- Unit tests on the service (validation, duplicate, happy path) and the handler (response codes). Table-driven.
- No real network in tests, timeouts/queue via an interface with a mock.
- LOC limits and "no warnings" (golangci-lint) — core/quality-gates.md.
~~~

### After completion

~~~bash
make build && make test 2>&1 | tee /tmp/day1-task1.log
golangci-lint run ./internal/...
~~~

Expected: a clean build, all tests green, no linter complaints. New tests: `TestInviteService_*`, `TestInviteHandler_*`.

### Commit

~~~bash
git add internal/domain/invite.go internal/service/invite_service.go \
        internal/transport/invite_handler.go internal/transport/router.go \
        internal/repository/queries/invite.sql internal/repository/db/ \
        internal/service/invite_service_test.go internal/transport/invite_handler_test.go
git commit -m "feat(invites): POST /api/v1/invites — create pending invite, enqueue email"
~~~

---

## Task 2 — Frontend: "Invite teammate" modal

An invite form on the team page: a button opens the modal, email input, submitting calls the API from Task 1, feedback to the user.

**Affected files:**

- `components/features/InviteTeammateModal.tsx` (new)
- `components/features/InviteButton.tsx` (new)
- `lib/api/invites.ts` (new) — typed client.
- `app/teams/[teamId]/page.tsx` (edit) — wire in the button.
- tests alongside.

### Prompt for Claude Code

~~~
Implement the "Invite teammate" UI per the rules in stack/react-nextjs.md and core/.

Behavior:
- The "Invite teammate" button (objectName/testid: inviteButton) on the team page opens a modal (testid: inviteModal).
- In the modal: an email field (testid: inviteEmailInput), a Send button (testid: inviteSubmit), a Cancel button (testid: inviteCancel).
- The Send button is disabled while the email is empty or invalid (client-side Zod validation).
- Send → POST /api/v1/invites via lib/api/invites.ts (TanStack Query useMutation).
  - 201 → toast (testid: inviteToast) "Invitation sent to <email>", modal closes, the invite list is invalidated.
  - 409 → inline error under the field (testid: inviteError) "This person already has a pending invite".
  - 400/other → inline error "Could not send invite, try again".
- While the request is in flight, Send shows a spinner and is disabled (no double submit).

Requirements:
- Server/Client Components per the rules; the modal is a Client Component.
- Form: React Hook Form + Zod, the schema is the source of truth for types.
- No internal properties in UI text; the user sees only the texts above.
- Tests (Vitest + Testing Library): disabled button on empty/invalid email, a successful submit triggers the mutation, 409 shows an inline error. getByRole/getByLabelText, not testid where a role exists.
~~~

### After completion

~~~bash
npm run build && npm run test -- --run 2>&1 | tee /tmp/day1-task2.log
npm run lint && npx tsc --noEmit
~~~

Expected: typecheck without errors, linter clean, tests green.

### Commit

~~~bash
git add components/features/InviteTeammateModal.tsx components/features/InviteButton.tsx \
        lib/api/invites.ts app/teams/\[teamId\]/page.tsx \
        components/features/InviteTeammateModal.test.tsx
git commit -m "feat(invites): invite teammate modal wired to POST /api/v1/invites"
~~~

---

## Task 3 — BA: scenarios for the "invite" feature

`3 1 2`. The BA reads the code from Tasks 1–2 and writes user scenarios per the format in [roles/ba.md](../../roles/ba.md).

- **Input:** the invite-feature code (handler, service, modal).
- **Output:** `docs/scenarios-1-2-invite-teammate.md` (example: [scenarios-1-2-invite-teammate.example.md](scenarios-1-2-invite-teammate.example.md)).
- **Reference for comparison:** Slack / Notion (workspace invitations).

### Prompt for Claude Code

~~~
Read the invite-feature code from Tasks 1–2: internal/transport/invite_handler.go,
internal/service/invite_service.go, components/features/InviteTeammateModal.tsx. Write user
scenarios for the "invite a teammate" feature per the format in roles/ba.md: the main scenario +
alternatives (duplicate email, invalid email, cancel), each ending in the user-VISIBLE expected
result. Compare with Slack/Notion's workspace invitation; list what we're missing as a separate
gaps list.
Result: docs/scenarios-1-2-invite-teammate.md.
~~~

### After completion

Eyeball review: every scenario ends in a user-visible result, not internal state.

### Commit

~~~bash
git add docs/scenarios-1-2-invite-teammate.md
git commit -m "docs(invites): user scenarios for invite teammate feature"
~~~

---

## Task 4 — QA UAT: test cases

`4 1 2`. QA UAT reads `scenarios-1-2-…` and the code (behind the UI selectors), writes formal test cases per [roles/qa-uat.md](../../roles/qa-uat.md).

- **Input:** `docs/scenarios-1-2-invite-teammate.md` + code.
- **Output:** `docs/test-cases-1-2-invite-teammate.md` (example: [test-cases-1-2-invite-teammate.example.md](test-cases-1-2-invite-teammate.example.md)).

### Prompt for Claude Code

~~~
Read docs/scenarios-1-2-invite-teammate.md and the feature code (behind the UI selectors:
components/features/InviteTeammateModal.tsx). Turn the scenarios into formal Given/When/Then test
cases per roles/qa-uat.md: the expected result is only what the user sees; add negative, stress,
and concurrency cases (double submit, a race on the same email).
Result: docs/test-cases-1-2-invite-teammate.md.
~~~

### After completion

Eyeball review: no Then references internal state (DB, store) — only what's visible in the UI.

### Commit

~~~bash
git add docs/test-cases-1-2-invite-teammate.md
git commit -m "docs(invites): UAT test cases for invite teammate feature"
~~~

---

## Task 5 — QA E2E: automated tests

`2 1 2`. QA E2E turns the test cases from `test-cases-1-2-…` into E2E tests per [roles/qa-e2e.md](../../roles/qa-e2e.md): action through the UI → visible result → server-side verification (the invite really was created) → UI after the server responds.

- **Input:** `docs/test-cases-1-2-invite-teammate.md`.
- **Output:** E2E tests in the `build-qa/` track (see [core/quality-gates.md](../../core/quality-gates.md) — separation of testing tracks).

### Prompt for Claude Code

~~~
Read docs/test-cases-1-2-invite-teammate.md. Implement the cases as E2E (Playwright) in the
build-qa/ track: every action goes through the UI of the built app, verification is a visible
result + server-side verification (the invite really was created) + UI after the server responds.
Gate QG-NN-05 (core/quality-gates.md): the run goes through the app's declared shipping root — no
bespoke injection of wiring (dependencies, outcome hooks, triggers) that shipping already provides
on its own; assert the OBSERVABLE EFFECT of the "invite" feature (the invite really was created and
is visible), not mere presence.
Annotate each assembled test with @qg:<scope-id> — the checked-in annotation IS the durable
evidence (regimen-doctor --qg reconciles it). In the report: for every atomic acceptance
criterion of the frozen scope — the assembled path + the @qg reference (informational).
~~~

### After completion

~~~bash
cd build-qa && npx playwright test 2>&1 | tee /tmp/day1-task5.log
~~~

Expected: all E2E tests green on the assembled app.

### Commit

~~~bash
git add build-qa/
git commit -m "test(invites): e2e invite teammate flow through assembled app"
~~~
