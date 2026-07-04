# PROJECT-STATE — Acme Teams

**A snapshot of the current state, not a journal.** The architect reads this on entering a day
(`N`) and overwrites it in place at the end of the day: removes what's resolved, wipes what's
stale. History ("what was done and when") lives in git (`git log`); "why" decisions live in
`docs/adr/`. This holds only what's needed to continue right now. Target ≤ ~1 screen.

Last updated: 2026-04-18 (Day 1)

## Snapshot

- **Phase:** MVP, week 1. Scaffold is ready: auth (session cookie, middleware puts `tenant_id` in
  ctx), multi-tenancy (Row-Level Security by `tenant_id` in Postgres), the "invite a teammate"
  feature (API + UI + tests).
- **Stack/commands** — in `CLAUDE.md` (not duplicated here).
- **Metrics** (recomputed on entering a day, not accumulated): 14 commits · 86/86 tests ·
  ~2,400 LOC — commands in [roles/architect.md](../../roles/architect.md) (status report section).

## Frozen scope (QG-NN-05)

Shipping root(s): `cmd/acme/main.go` (API) · `app/layout.tsx` (web) — fixed by the architect; a
task that changes the shipping entry point must update this line
([core/quality-gates.md](../../core/quality-gates.md) §Reachability).

- `INV-01` — the owner invites a teammate by email with a role; after accepting, the invitee sees
  the team. Evidence: `tests/assembled/invite_flow_test.go` (annotation `@qg:INV-01`).
- `INV-02` — a repeat invite to a pending email is rejected with a user-visible error.
  Evidence: same file (`@qg:INV-02`).
- `INV-03` — the toast auto-hides after 5 seconds — waiver: ergonomics with no outcome
  differential, E2E circuit, not a gate.

## In progress

- Accepting the invitation (accept invite) — planned for Day 2.
- Real email sending (currently a logger stub) — waiting on the provider choice, see open
  questions.

## Risks / blockers

- The email provider isn't chosen — affects Day 2. Needs a user decision.
- No rate limit on invites yet — potential abuse vector, carry over to Open questions / "Next day".

## Open questions

- [ ] Email provider: SES vs Postmark vs SMTP? — needs a user decision.
- [ ] Limit on pending invites per tenant? — clarify with the domain expert (see [roles/sa.md](../../roles/sa.md)).

## Next day

Day 2: accepting the invitation via the token from the email + wiring invite → member.
