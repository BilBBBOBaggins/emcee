# ADR-011: The process layer (RFC) now + unblocking the multi-model build (ADR-010) by lifting gate G1 early

Date: 2026-06-28
Status: Accepted (the build was unblocked by lifting the empirical gate G1 from [ADR-010](010-multimodel-core-overlays.md) early — a deliberate project decision with the risk accepted explicitly)

> Decision reached via an adversarial panel run (red team → blue team → arbiter), see [core/adversarial-panel.md](../../core/adversarial-panel.md).

A direct continuation of [ADR-010](010-multimodel-core-overlays.md) (multi-model support under
gates) and [ADR-009](009-portability-boundary.md) (the portability boundary, the marker stop
condition).

## In short

The multi-model necessity gate (G1 from ADR-010) was lifted **early** by a deliberate project
decision — the empirical evidence hasn't been gathered yet, the blind-spot risk is accepted
explicitly and moved into monitoring — and the final target architecture was requested. The proposed
**v1** added an `owner: package|project` axis and made the `origin:`/`owner:` markers
machine-readable (the upgrader keys off `owner:`, the generator wires based on `origin:`). The panel
found: **v1 is a regression relative to the already-accepted ADR-010**, which went through a full
panel the same month and deliberately chose git-tree overlays + static copying with no marker
parsing.

Decision (v2):

1. **Discard v1's machinery** — the `owner:` axis, tooling parsing of markers, a physical content
   split. This is fatally broken regardless of sequencing (it violates ADR-009's stop condition and
   ADR-006's by-file boundary).
2. **Build now, harness-agnostic** — the process layer from the RFC (skill routers, phase
   contracts, depth tiers, the verify format) + the AGENTS.md clarification + gates on two planes. A
   clear quality win, no second runtime needed.
3. **Unblock the build of the multi-model overlay** in the form of ADR-010 (git trees, static
   `--wiring`, markers as prose) — G1 and the arbiter's YAGNI sequencing are lifted early, the cost is
   accepted explicitly.

## Context

After [ADR-010](010-multimodel-core-overlays.md) (multi-model support adopted as a design, but the
build blocked by field gates G1/G2), gate G1 was **lifted early** by a deliberate project decision
(the necessity evidence hasn't been gathered yet — the risk is accepted explicitly), and the final
architecture was requested. In parallel, two external RFCs (Factorial: a guidance layer + routing
skills; an advanced AI workflow) contributed process patterns, some of which the package didn't yet
have.

The proposed architecture-v1 folded this into a single layout, but introduced:
- an `owner: package|project` axis as **a machine key** for the upgrader;
- an `origin:` layer that **the generator wires** namespaces by;
- a physical package/project content split.

The panel (red team → blue team → arbiter, drawing on codex as a second model), with high
convergence between two independent models, established that this overrides verdicts already handed
down:
- **ADR-006**: the package/project boundary "isn't split by rule, it's computed **by file**,
  by-content" (`{{` placeholders vs. clean). The `owner:` axis either duplicates this signal or splits
  something indivisible (a filled-in stack file = mixed).
- **ADR-009** (the marker stop condition, [portability.md:39-43](../../core/portability.md)):
  `origin:` stays outside owned debt **only as long as** it doesn't drive composition and isn't
  parsed by tooling. v1 violates both points **by design**.
- **ADR-010**: already chose static copying of git trees via `safe_copy_tree`/`--wiring` **with no
  parsed manifest** — precisely to avoid a relapse of ADR-001/006 owned debt.

The facts were checked directly: ADR-009/010 exist; `new-project.py` already has
`safe_copy_tree` + `--wiring` and doesn't parse `origin`/`owner`; the stop condition is confirmed in
portability.md.

## Decision

### A. Discarded (fatal, not salvageable by mitigation)

- **The `owner: package|project` axis** — cancelled. The package/project boundary = the existing
  by-content signal from ADR-006 (`{{` vs. clean).
- **Tooling parsing of markers** — cancelled. Generation = `safe_copy_tree`/`--wiring` (the code
  already exists).
- **A physical content split** — not done. Content stays shared and harness-neutral; overlays are
  plumbing only.

**Stop condition (load-bearing):** reintroducing machine reading of `origin:` markers/any new axis
requires a deliberate re-examination of ADR-009 by a new panel, with owned debt accepted openly, not
quietly.

### B. Being built now — the process layer, harness-agnostic (RFC additions ADR-010 didn't cover)

- **skills = routers**: the template `Purpose / When to use / When NOT to use / decision-tree /
  key constraints / standard procedure / validation` + **a quality bar** (add one only if a frequent ∨
  costly failure ∨ recurring review comments ∨ the agent consistently picks the wrong path; NOT for
  one-off / vague / policy-prose). Content/template/quality bar are built now; per-harness discovery
  wiring — later.
- **pipeline = phase contracts**: a phase requires the input artifact of the previous one → STOP,
  no simulating progress.
- **depth tiers Inline / Atomic / Full** instead of the binary micro/full in
  [constitution.md](../../core/constitution.md).
- **the verify format** `COMPLETENESS / CORRECTNESS / EVIDENCE / ⚠ warnings` — the form of the
  exit report and reviewer/QA output.
- **coworker-not-executor** — as a load-bearing principle.
- **AGENTS.md = a substrate for content/conventions**, NOT hardware guarantees (those come from the
  per-runtime permission profile). The format's maturity is confirmed (AAIF/Linux Foundation).
- **Gates on two planes**: definition — in the constitution's registry (11 non-negotiables);
  enforcement = per-runtime profile/hook. A mechanical gate with no enforcer on the runtime
  **degrades to accountability** (on record), the obligation doesn't disappear.
- **`origin:` markers stay prose** (4 axes: `universal` / `process-convention` /
  `harness:<name>` / `model:<name>`), lazily labeled on touch, not parsed.

### C. Being built now — the multi-model overlay in the form of ADR-010 (build unblocked)

G1 (necessity) and the arbiter's YAGNI sequencing are lifted early — a deliberate project
decision, the cost accepted explicitly. The form is strictly ADR-010, with no marker machinery:

- the core (`core/` + `roles/*` content + `stack/architecture/domain`), scrubbed of harness-isms;
- independent overlay git trees; the generator copies the chosen one statically;
  - **Form (clarification):** the claude-code overlay **stays `.claude/` in its native
    position**, it does NOT move to `overlays/claude-code/`. `overlays/` is created **only for
    non-default runtimes** (`overlays/codex/`: `.codex/*.toml` permission profiles, hooks, AGENTS.md
    wiring, skills). The equivalence `.claude/ ≡ overlays/claude-code/` is recorded as a documented
    mapping in a doc paragraph. **The move was rejected:** the consistency would be illusory — the
    generator still drops it into `target/.claude/` (the source↔target asymmetry is inherent);
    the move would add symlink fragility (Windows `core.symlinks=false`), a self-host break, and churn
    across 16 files for zero benefit beyond aesthetics. Leaving `.claude/` in place + a documented
    mapping strictly dominates on effort↔value;
- `roles.json` as the single source of truth → `sync-roles.py` extended to N runtime emitters;
- a per-runtime guarantee matrix (role × runtime × hardware-enforced/prose/absent);
- `regimen-doctor` reports state, not presence.

**Order:** (1) revert v1's machinery → (2) the process layer (section B) → (3) neutralize the core
(~1.5 days) → (4) overlays + N emitters + a file-count backstop in `selftest.py` → (5) verify Codex's
permission profile and hooks → the guarantee matrix + doctor.

## Consequences

**Upsides:** the process layer is a clean quality win immediately, with no dependency on a second
runtime; the panel caught v1's regression before weeks of engineering went into it; multi-model
support is built in a form that has already passed a panel (it doesn't relapse into manifest owned
debt).

**Accepted costs/risks (explicit):**

- **Lifting gate G1 early** removes the only risk-detection instrument: two weeks of enthusiasm →
  one default runtime → the second overlay rots, constraining every core change. The risk is accepted
  explicitly and monitored (a necessity log, in the open questions below).
- **The debt of N overlays is material** (`.claude/` is already 25 files; the codex overlay = a
  second product). The backstop is the file count in `selftest.py` (the threshold for unmanageable
  debt when a role is added).
- **Slash dispatch on Codex** degrades to prose (`R D T`) — the guarantee matrix records it, it
  doesn't hide it.
- **The "neutral core" is permanently partly-false**: process convention (`R D T`, days) on Codex
  stays a typed idiom even after the core is neutralized — the matrix shows this honestly.

**Open questions (learned from the field/testing):**

- [x] Neutralizing the core — a grep sweep for harness-isms across the whole core (~1.5 days). A
      precondition for extracting the core. → **Outcome: done** in the build (the core is neutral,
      the entry point is per-harness — ADR-012).
- [x] Verifying the permission profile on Codex — `docs-only.toml` + 3 write attacks against
      `src/` (≤0.5 day). If a write gets through, docs-only on Codex downgrades to prose (amends the
      guarantee matrix, doesn't bury it). → **Outcome: RED, downgraded** — G2,
      [g2-findings](../evidence/g2-findings.md).
- [x] Codex hook-activation test — `Stop`/`PreCompact` actually fire. → **Outcome: RED (KL-7)** —
      headless hooks don't fire, hook gates = accountability
      ([g2-findings](../evidence/g2-findings.md)).
- [ ] A multi-model necessity log is kept during the build (a 6-week window). Not a blocker (the
      gate is lifted), but it provides data for a future decision on "whether to fold the codex
      overlay back in": if the necessity turns out to be only cross-checking, the overlay wasn't
      needed (codex already provides a second model).

## Alternatives considered

- **v1 as proposed (the `owner:` axis + marker parsing + split).** Rejected: a regression relative
  to ADR-010, violates ADR-009's stop condition and ADR-006's by-file boundary (the panel's verdict —
  fatal).
- **Defer the overlay until G1 is green (the arbiter's recommendation, YAGNI sequencing).**
  Rejected: the cost of building now is accepted explicitly (a deliberate project decision). The
  process layer (B) doesn't depend on this and would proceed now regardless.
- **A new panel to revisit ADR-009's stop condition** (legalizing machine reading of markers). Not
  needed: the goals of the split are achieved by ADR-006's by-content signal + static `--wiring`, with
  no marker machinery.
- **Provider (vendor) as a regimen axis.** Rejected: doesn't affect the regimen; harness and model
  are sufficient axes.
