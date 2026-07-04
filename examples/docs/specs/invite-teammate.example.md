# Feature: Invite a teammate by email

Status: approved
Owner: SA
Related ADRs: [ADR-001](../adr/001-modular-monolith.example.md)
Last updated: 2026-04-17

Format — [roles/sa.md](../../../roles/sa.md). This is input for the architect (technical spec) and the developer (acceptance criteria).

## Context

For the team to start using the product, the owner must invite colleagues. Without invitations the
product is dead at the start of onboarding (see [domain/b2b-saas.md](../../../domain/b2b-saas.md) —
onboarding/activation). First step: sending the invitation; accepting the invite is a separate
feature (Day 2).

## Users and use cases

Primary users:
- **Team owner / admin**: invites colleagues by email, sees a send confirmation.

Secondary users (affected but not primary):
- **Invitee**: receives the email (accepting it is out of scope for this spec).

## User stories

### Story 1: Send an invitation

As a team admin,
I want to invite a teammate by email,
So that they can join my team without me sharing credentials.

**Priority**: P0
**Estimate**: M

Acceptance criteria:

1. **Scenario: Successful send**
   Given I'm a team admin and I've opened the invite form
   When I enter a valid email and click Send
   Then a pending invite is created in my tenant
   And I see the confirmation "Invitation sent to <email>".

2. **Scenario: Repeat invitation**
   Given this email already has a pending invite in my team
   When I try to invite them again
   Then the system doesn't create a second invite
   And I see "This person already has a pending invite".

3. **Scenario: Invalid email**
   Given the invite form is open
   When the email is empty or invalid
   Then submission is blocked (the Send button is disabled).

## Non-functional requirements

- **Security:** the email in the request body doesn't determine the tenant — the tenant comes
  strictly from the auth context (isolation, [architecture/multi-tenant.md](../../../architecture/multi-tenant.md)).
- **Performance:** API response < 300 ms; sending the email is asynchronous (queued), doesn't block
  the response.
- **Compliance:** email is PII, must not be written to logs in the clear
  ([core/code-quality.md](../../../core/code-quality.md), [domain/regulated.md](../../../domain/regulated.md) if applicable).

## Data model changes

New entity `invites`: `id`, `tenant_id`, `email`, `status` (pending|accepted|revoked|expired),
`created_at`. Uniqueness: one active (pending) invite per (`tenant_id`, `email`).

## Open questions

- [ ] Email provider (SES / Postmark / SMTP)? — blocks the real send, needs a user decision.
- [ ] Limit on pending invites per tenant and invite lifetime? — clarify with the domain expert.

## Assumptions

- We assume the auth middleware already puts `tenant_id` in the context. Verified: implemented in
  the scaffold (PROJECT-STATE).
- We assume accepting the invite is a separate feature. If wrong — expand the scope for Day 1.

## Out of scope

- Accepting the invitation via the token from the email (Day 2).
- Bulk invites, invite-by-link, roles at invite time.
