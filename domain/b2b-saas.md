# B2B SaaS — domain patterns

Patterns and rules that apply to B2B SaaS products. A layer on top of [architecture/multi-tenant.md](../architecture/multi-tenant.md).

## Onboarding

B2B onboarding is a multi-level process, not just registration.

Typical sequence:

1. **The organization registers** — first user's email, company name, basic information
2. **The first admin creates a tenant** — email verification, choosing a tier or trial
3. **Admin invites the team** — email invites, roles assigned
4. **Initial setup** — tenant settings (branding, integrations, policies)
5. **First value** — first successful operation (first order, first analytics, first report)

Every step is measured by a metric. Drop-off at a step is a signal for UX improvement.

### Onboarding rules

- **Minimum steps to first value** — not 15 forms before showing the product, but a fast path to the "wow moment"
- **Skip-friendly** — optional steps can be skipped and returned to later
- **Progress visible** — the user sees where they are in the process
- **Empty states helpful** — when a tenant is empty, the UI shows what to do, not a blank screen
- **Setup wizard separate from the main UI** — don't mix the onboarding flow with everyday use

### Trial and activation

For SaaS with a trial period:

- Trial length — depends on product complexity (7 days for simple, 14-30 for complex)
- Clear expiration communication — 3 days before the end, on the day it ends
- Grace period — a few days after expiration to upgrade without losing data
- Data retention policy — if not upgraded, how long to keep the data

## Authentication and SSO

### By tier

- **Starter/SMB tier** — email/password + MFA (TOTP)
- **Professional** — add Google/Microsoft OAuth
- **Enterprise** — SAML 2.0 / OIDC for SSO with their identity provider + SCIM for user provisioning

### MFA mandatory for admins

An admin role cannot exist without MFA. On an attempt to elevate a role to admin without MFA — forced setup.

### SSO specifics

SAML/OIDC configuration per tenant:

- Metadata URL or upload
- Attribute mapping (name, email, roles)
- Domain whitelist — only emails from these domains are auto-provisioned via SSO
- Just-in-time provisioning — the user appears in the system on first SSO login

### SCIM for enterprise

Automatic user management from an external identity provider:

- Provisioning — creating users when added to an SSO group
- De-provisioning — deactivating users when removed from an SSO group
- Attribute sync — names, roles synchronized
- SCIM endpoints in the API under separate auth (bearer token from the SCIM client)

## Roles and permissions

### Minimal RBAC

Most B2B SaaS need a minimum of three roles:

- **Admin** — manages the tenant (users, billing, settings, all data access)
- **Manager** — works with content (create/edit/delete business entities), but does not manage tenant-level settings
- **User** — basic use (view, create within what's permitted)

### Permissions are checked at the API level

The UI hides buttons by role, but that is not protection — only UX. The real check is in the API handlers:

~~~go
func (h *Handler) DeleteOrder(w http.ResponseWriter, r *http.Request) {
    user := UserFromContext(r.Context())
    if !user.HasPermission("orders:delete") {
        http.Error(w, "forbidden", http.StatusForbidden)
        return
    }
    // ...
}
~~~

Never trust the frontend. Never check permissions only in the UI.

### Attribute-Based Access Control (ABAC)

For cases more complex than RBAC:

- Permissions depend on attributes: owner, team, region, tag
- "A user can only edit their own orders" — that's ABAC, not RBAC
- Implemented via a policy engine (Casbin, OPA) or inline checks

### Custom roles

Enterprise tier often requires custom roles. Structure:

- Permissions — atomic (`orders:create`, `orders:delete`, `users:invite`)
- Roles — sets of permissions
- System roles — immutable (Admin, User)
- Custom roles — a tenant can create its own

## Billing

### Subscription tiers

Typical structure:

- **Free/Trial** — limited usage, time-bounded
- **Starter** — small team, basic features, monthly subscription
- **Professional** — bigger team, advanced features, annual discount
- **Enterprise** — custom pricing, SSO, dedicated support, custom contract

### Usage-based billing

Where applicable (API calls, storage, compute):

- Metered usage tracked per tenant
- Monthly aggregation in the invoice
- Overage charges — if usage exceeded plan limits
- A transparent dashboard showing current usage vs. limits

### Proration on upgrades

A user upgrades mid-cycle:

- Old plan pro-rated refund
- New plan pro-rated charge
- A single invoice with both line items

Downgrade is usually applied from the start of the next cycle (no refund).

### Payment methods

- **Credit card** — for Starter and Professional, automatic charge
- **Invoice (NET 30/60/90)** — for Enterprise, sent by email, paid by wire transfer
- **Bank transfer / ACH** — for Enterprise
- **Custom** — some enterprise clients have non-standard billing terms

### Dunning — handling failed payments

- Automatic retries on a schedule (3 days, 7 days, 14 days)
- Email notifications about failed payment
- Grace period before deactivation
- Downgrade to free (if available) or suspend service
- Win-back flows for churned accounts

## Admin panel

Two levels of admin:

### Tenant admin panel

For client admins. Scope — their tenant only.

Views:

- **Users** — list, invite, roles, deactivate
- **Usage** — current period, history, trends
- **Billing** — current plan, invoice history, payment methods, upgrade
- **Settings** — branding, integrations, security policies
- **Audit log** — actions within their tenant

Not visible: other tenants, system-level data.

### Platform admin (internal)

For platform operators. Scope — all tenants.

Views:

- **Tenants overview** — all tenants, their plans, usage, health
- **Impersonation** — log into a tenant as admin for support (with audit log)
- **Feature flags** — enabling features for specific tenants
- **System metrics** — infrastructure health, error rates
- **Support queue** — tickets, escalations

Separate auth from tenant auth. A strong audit log — every impersonation is logged, the tenant is notified.

## Audit log

All significant actions are logged.

### What gets logged

- User lifecycle: create, invite, role change, deactivate, delete
- Authentication: login, logout, failed attempts, MFA events
- Authorization: permission grants, revocations
- Data access: read sensitive data, export, bulk download
- Data modification: create, update, delete business entities
- Settings changes: tenant configuration, billing info
- Admin actions: impersonation, feature flag changes

### Audit event structure

~~~go
type AuditEvent struct {
    ID         uuid.UUID
    Timestamp  time.Time
    TenantID   uuid.UUID
    ActorID    uuid.UUID        // who did it
    ActorType  string           // user / system / api_key
    Action     string           // "order.deleted"
    Resource   string           // "order:abc-123"
    Changes    map[string]any   // before/after for updates
    IP         string
    UserAgent  string
    Metadata   map[string]any
}
~~~

### Read-only, append-only

The audit log is not edited or deleted. Storage:

- A separate table/DB with write-only permissions for the app, read-only for the audit viewer
- Or an append-only log (S3 with versioning, cloud-native audit service)
- Export for compliance — the ability to export a given period

### Retention

Depends on compliance requirements. Typically 1-7 years. For regulated industries — per the applicable regulations.

## Notifications

### Channels

- **Email** — for important events (billing, security, invites)
- **In-app** — for workflow events (task assigned, mention)
- **SMS** — optional, for critical security events (MFA, suspicious login)
- **Webhooks** — for integration with client systems
- **Slack/Teams** — for B2B, often more important than email

### User preferences

Every user manages their own notification preferences:

- Per category (security, billing, workflow, marketing)
- Per channel (email, in-app, SMS)
- Digest vs. immediate — some prefer batched, some real-time
- Quiet hours — don't send outside working hours (respecting timezone)

### Unsubscribe mandatory

For marketing/promotional emails — an unsubscribe link is legally required (CAN-SPAM, GDPR).
For transactional emails (billing, security) — unsubscribe is not required, but preferences must allow turning something off.

## Customer success

### Product analytics

Tracking:

- **Feature usage** — which features are used, by whom, how often
- **User engagement** — DAU/MAU, session duration, return rate
- **Adoption metrics** — % of users who activated key features
- **Cohort analysis** — retention by cohort (by signup month)

Tools: Mixpanel, Amplitude, PostHog, or self-hosted equivalents.

### Health scores

A per-account "churn likelihood" indicator:

- Usage trends (growing/declining)
- Feature adoption (using mission-critical features or only basic ones)
- Support tickets (frequency and severity)
- User engagement (all users active or only one)
- Renewal proximity (how close to contract end)

A low health score triggers outreach from the customer success team.

### Automated alerts

Customer success receives alerts:

- Account not logged in for X days
- Usage drop > 30% month over month
- Multiple failed payments
- A support ticket with "high" severity
- User count increased (upsell opportunity)

## Support

### Ticket system

- Email-to-ticket integration
- In-app widget for creating tickets
- Priority levels with response time SLA per tier
- Escalation paths (L1 → L2 → Engineering)

### Response time SLA

By tier:

- Free: best effort
- Starter: 24h business hours
- Professional: 8h business hours
- Enterprise: 1h 24/7 for critical, with an explicit SLA in the contract

### Knowledge base

- Public help center with articles
- Search across all content
- Video tutorials for complex workflows
- Release notes with screenshots and examples

### In-app chat

For paid tiers — live chat:

- Business hours coverage
- After hours — async, response whenever the team is available
- Integration with user context (who, on which page, which tier)

## Data export

Users have the right to export their data. Mandatory under GDPR, good practice everywhere.

Formats:

- **CSV** — for tabular data
- **JSON** — for structured data
- **PDF** — for reports
- **Full export** — a zip with everything in machine-readable format

Export UI:

- In settings → "Export data"
- Choice of scope (specific data types or everything)
- Email notification when the export is ready (for large exports, an async job)
- Download link valid for a limited time

## Terms and contracts

### Click-through for self-serve

- Starter/Professional tier — the user accepts the ToS at signup
- The text should be read-friendly, not a legal wall of text
- Updates — email notification + re-acceptance on significant changes

### MSA for enterprise

- Custom contracts with legal review
- Signed through DocuSign or equivalent
- Effective dates, renewal terms, termination clauses
- MSA separate from specific services (SOW)

### DPA for GDPR compliance

Data Processing Addendum — a separate document:

- Data controller / processor relationship
- Processing purposes
- Sub-processors (third parties the data flows to)
- Data transfer mechanisms (SCC for EU→US)
- Security measures
- Breach notification procedures

Mandatory for EU clients, useful everywhere.

### Change notifications

When ToS/Privacy Policy/Pricing terms change:

- Email to all affected users
- In the email — a summary of changes + a link to the full document
- Advance notice — usually 30 days for material changes
- An opt-out option (for pricing changes — cancellation without penalty)
