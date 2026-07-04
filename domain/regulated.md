# Regulated domain — compliance requirements

For projects working with regulated data: personal data (PD), medical data, financial data, government data, tender documentation.

The file contains general principles + Russia-specific specifics (152-FZ, 44-FZ, 223-FZ).

## Applicable laws and regulations

### Russian Federation

- **Russia's Federal Law No. 152-FZ "On Personal Data"** — processing of Russian citizens' personal data
- **Federal Law No. 149-FZ "On Information, Information Technologies and Information Protection"** — general requirements for information systems
- **44-FZ** — public procurement for state and municipal needs
- **223-FZ** — procurement by certain categories of legal entities (state-owned companies, natural monopolies)
- **275-FZ** — state defense order (if applicable)
- **FSTEC requirements** (Russia's Federal Service for Technical and Export Control) — if the system processes an information system for personal data (ISPDn) of a given protection level

### International

- **GDPR** — for EU clients or EU residents' data
- **CCPA/CPRA** — California Consumer Privacy Act for California residents
- **HIPAA** — US health data (not applicable without explicit scope)
- **SOC 2** — certification for B2B SaaS handling customer data

## Data residency

### Requirement

Russian citizens' personal data is stored and processed on servers located in Russia. This is a hard requirement of 152-FZ, not a recommendation.

Architectural consequences:

- A separate DB or a separate instance for Russian users
- Russian citizens' personal data cannot be stored in US/EU cloud regions
- CDN and static hosting can be global, but with a requirement of no personal data
- Backups also stay in Russia

### Implementation

Options in decreasing order of compliance:

1. **Fully Russia-based** — servers in a Russian data center, Russian cloud providers (Yandex Cloud, VK Cloud, Selectel). Simple story, but a limited choice of providers
2. **Hybrid** — main processing in Russia, auxiliary services (email delivery, file storage without personal data) global. More complex but more flexible
3. **Sovereignty-aware globally distributed** — global architecture with data locality. Complex, for large companies

For a tender product (and most Russian B2B SaaS) — option (1) is the most practical.

### Cross-border transfer

If cross-border transfer is needed, it requires:

- Notification of Roskomnadzor (Russia's data protection regulator) about the cross-border transfer
- An adequate level of protection in the receiving country (whitelist) or the data subject's consent
- Transfer mechanisms (SCC for the EU, explicit user consent)

Without these measures, cross-border transfer of personal data is a violation.

## Data classification

Every field in the DB is classified, and this classification affects storage, access, and logging.

### Classification levels

- **Public** — open data, requiring no protection (product catalog, public profiles)
- **Internal** — internal business data, not personal data, but of commercial value (metrics, configurations)
- **Personal (PD)** — the data subject's personal data (full name, email, phone, address)
- **Sensitive Personal (special categories of personal data)** — special categories of personal data (health, nationality, political views, biometrics)
- **Confidential Business** — trade secrets (contracts, tenant finances, proprietary algorithms)

### Marking in the DB schema

Via comments on columns or external configuration:

~~~sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) NOT NULL,  -- classification: personal
    full_name VARCHAR(255),        -- classification: personal
    tax_id VARCHAR(20),            -- classification: sensitive_personal
    created_at TIMESTAMPTZ
);
~~~

Or via a separate metadata table:

~~~sql
CREATE TABLE data_classification (
    table_name VARCHAR(64),
    column_name VARCHAR(64),
    classification VARCHAR(32),
    notes TEXT,
    PRIMARY KEY (table_name, column_name)
);
~~~

### Access rules by class

- Public — unrestricted access
- Internal — only authenticated users of tenant
- Personal — only users with permission, audit log on access
- Sensitive Personal — only specific permissions, mandatory audit log, possibly an approval workflow
- Confidential Business — compartmentalized access, strong audit

## Data minimization

Principle: collect only what's needed for the function. Not "just in case", not "might come in handy".

Rules:

- Every field in a registration/settings form is justified by a specific use case
- No "misc info", "comments" fields without a clear purpose
- Regular review of fields (every six months to a year) — remove obsolete fields
- Privacy Impact Assessment when adding new fields containing personal data

Direct consequence — when in doubt whether to add a field or not, don't add it. Better to add it later once the use case appears than to collect data that goes unused.

## Encryption

### At-rest

- Database storage encrypted at the disk/storage level (LUKS, cloud provider encryption)
- For sensitive fields — application-level encryption on top of database encryption
- Application-level encryption is mandatory for:
  - Passwords (bcrypt/argon2, not reversible encryption)
  - API keys and tokens (AES-256-GCM with a key from KMS)
  - Financial data (card numbers — PCI-DSS tokenization)
  - Biometric data

### In-transit

- TLS 1.2+ for all network connections
- TLS 1.3 preferred
- Internal services also on TLS (mTLS for production environments)
- Certificate validation is mandatory, never disable it

### Key management

- Keys never in code, never in config files, never in committed environment variables
- Use a KMS (AWS KMS, Vault, Yandex KMS)
- Automated rotation on a schedule (90 days for short-lived, yearly for long-lived)
- A revocation process for compromised keys

## Compliance audit log

Separate from the general audit (see [b2b-saas.md](b2b-saas.md)). For regulated data — stricter requirements.

### What gets logged

For every access to personal data or Sensitive data:

- Who (authenticated user ID, service account, system)
- When (timestamp with millisecond precision)
- What (which record, which field)
- Why (purpose — part of the request context)
- Result (success/denied, what data was returned)

### Immutability

The audit log is not edited or deleted. Implementation:

- Append-only storage (write-once, read-many)
- Cryptographic hash chain (each record contains the hash of the previous one) — tampering detection
- Or a blockchain-like approach if critical
- Or a separate DB with IAM policies forbidding update/delete

### Retention

Depends on the regulation. Typically:

- 152-FZ: 3 years after processing ceases
- GDPR: a separate DPIA for each processing activity
- SOC 2: usually 7 years
- Financial regulators: 5-10 years

Retention is automatic — old entries are not deleted manually, the policy lives in storage.

## User rights (rights of the personal data subject)

### Access

The user has the right to obtain a copy of their data:

- A full export of all data in a machine-readable format (JSON, CSV)
- Including metadata (when created, by whom, from where)
- Request processing within 30 days (152-FZ) or 30 days (GDPR)
- Free — no charge for the first request in the period

### Rectification

The right to correct inaccurate data:

- UI for self-service editing where possible
- For fields the user cannot edit (e.g. verified name) — a process via support with ID verification

### Erasure / Right to be forgotten

The right to deletion (with restrictions):

- User initiates the request
- The system deletes personal data from the production DB
- Cascading delete — all related data (logs, analytics)
- **Restrictions**:
  - Data required for legal compliance (billing records, audit logs) is retained with justification
  - Anonymization instead of deletion — acceptable in some cases
  - Contractual obligations may require retention

Processing time — 30 days maximum.

### Portability

The right to receive data in a format that allows transfer to another provider:

- Structured machine-readable format
- Industry standards where possible (iCalendar for calendars, vCard for contacts)

### Withdrawal of consent

The right to withdraw consent to processing:

- UI for withdrawal — by category (marketing, analytics, etc.)
- Withdrawal → prompt halt of processing
- Withdrawal does not affect processing on other legal bases (contract performance, legal obligation)

## Consent to personal data processing

### Recording consent

- An event "consent given" is recorded with:
  - User ID
  - Timestamp
  - Version of the consent text (important!)
  - IP address
  - Which purposes (cannot be bundled — separate consent for each purpose)
- Stored for at least as long as the personal data itself

### Text versioning

- Each version of the consent text is a separate record
- When the text changes — a new version, users must re-consent
- Grandfather clause — old users remain on the old version if there was no material change

### Granularity

Separate consents for different purposes:

- Product functionality (mandatory, contract basis)
- Marketing emails (separate, optional)
- Product analytics (separate, optional or legitimate interest)
- Third-party sharing (separate, explicit, per third party)

No bundling "I agree to everything".

### Withdrawal

- Must be just as easy as giving consent
- One click where possible
- Does not require contacting support

## Incidents and breach notification

### Incident response plan

Documented procedure:

1. **Detection** — monitoring triggers an alert
2. **Assessment** — what happened, what was compromised, who is affected
3. **Containment** — stop further damage
4. **Investigation** — root cause, scope
5. **Notification** — regulator + affected users
6. **Remediation** — fix vulnerability, prevent recurrence
7. **Post-mortem** — lessons learned, process improvements

### Notification timelines

Regulator notification deadlines:

- **GDPR**: 72 hours from the moment of awareness
- **152-FZ**: 152-FZ does not set an exact deadline, but "without undue delay" — usually 72 hours as best practice
- **SOC 2**: per contract with clients, usually 24-72 hours

User notification deadlines:

- **GDPR**: without undue delay, if high risk
- **152-FZ**: similarly
- **Form**: email + in-app + possibly SMS for critical cases

### Documentation

A breach log for every incident:

- Dates (detection, containment, notification)
- Scope (records affected, data types, users)
- Root cause
- Remediation steps
- Communication log

For regulator audits.

## Third parties

### Data Processing Agreements (DPA)

Any third party gaining access to data — a DPA:

- Processing purposes
- Types of data
- Duration
- Security measures
- Sub-processors (if they use others)
- Return/deletion of data after the contract ends

### List of sub-processors

A public list (on the website or in the DPA) of all third parties:

- Name, jurisdiction
- Purpose (what they do with the data)
- Data types
- Location of processing

When the list changes — notification to clients, often with an opportunity to object.

### Due diligence

Before using a third party:

- Security assessment
- Compliance certifications (SOC 2, ISO 27001)
- References
- Legal team contract review

## Tender specifics (44-FZ / 223-FZ)

If the product is tied to a tender system:

### Public data

- Tender documentation on the Unified Information System (EIS) is **public**, not personal data
- Participant profiles (legal entities) are **public** via the Unified State Register of Legal Entities / Individual Entrepreneurs (EGRYuL/EGRIP)
- Contact persons of legal entities — a **hybrid** case, usually public but with nuances

### Clients' trade secrets

Internal data of the product's clients:

- Their own tender analytics (win rate, pricing strategies) — trade secret
- Their custom setup and preferences — trade secret
- Their won contracts may be public, but the analytics is theirs

Separating these categories is critical in the data architecture.

### Integration with the Unified Information System (EIS)

EIS API for fetching tenders:

- The API is public, rate-limited
- Some data requires registration as a user
- Certain operations require an electronic signature (ES)
- A sandbox environment for development

### Audit trail for contracts

If the product helps prepare bids and contracts:

- Full change history for every document
- Electronic signature integration where required
- Retention requirements per 44-FZ

## Secrets and keys

### Storage policy

- Clients' API keys — **application-level encrypted**, never plaintext
- Environment secrets — in a secrets manager (Vault, AWS Secrets Manager, Yandex Lockbox)
- No secrets in:
  - Git history
  - Docker images
  - Config files that get committed
  - Environment files on shared filesystems

### Scheduled rotation

- Database passwords — rotate monthly or on incident
- API keys — expirable with automatic rotation
- Signing keys (JWT) — rotation + overlap period for graceful transition
- TLS certificates — automated renewal (Let's Encrypt, ACM)

### Auditing secret access

- Every access to a secret is logged
- Usage patterns monitored — unusual access triggers an alert
- Service accounts — minimal permissions, short-lived credentials where possible

### Revocation process

On compromise:

- Immediate revocation of the compromised secret
- Generation of a new one
- Rolling deployment with the new secret (without downtime where possible)
- Rotate related secrets if lateral movement is possible
- Post-mortem — how it happened, how to prevent it

### Git history compromise

If a secret ends up in git history:

- Rotate immediately
- Rewrite history (git filter-branch or BFG Repo-Cleaner)
- Force push (coordinated with the team)
- Notify everyone with the repo to re-clone
- Add a pre-commit hook (detect-secrets or equivalent) to prevent recurrence
