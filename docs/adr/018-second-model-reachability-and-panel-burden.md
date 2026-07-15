# ADR-018: Second-model reachability on every role + inverted burden of proof for the panel

**Status:** accepted (2026-07-15)

## In short

Two defects surfaced by a long autonomous field run, fixed together because they share one root —
the second model existed on paper but not in practice:

1. **Reachability.** Six roles (architect, auditor, ba, qa-uat, reviewer, sa) shipped without a
   shell, so they physically could not call codex. ADR-016's "mandatory when available" degraded to
   "never available": across ~40 autonomous day-increments there was not a single real codex call —
   every panel and audit fell back to honest single-model prose with flags. Fix: every role's
   subagent definition now carries Bash with a scoped-use block — it exists to call codex per
   `core/second-model.md`; read-only roles must not write or commit through it.
2. **Panel threshold self-classification.** The panel fired once per ~34 ADRs, because the same
   architect who makes a decision also classifies it as "load-bearing vs trivial" — and drifts
   toward skipping. A retro second-model pass then contested 2 of 4 sampled solo rulings. Fix: the
   burden of proof is inverted. Every ADR carries a `Panel: run (link) / skipped because <reason>`
   field whose skip reason is a first-class review object, and a class trigger (frozen semantics,
   money/CAS/crypto/PII, module perimeters/boundaries, migration contracts) mandates a **compact
   panel** — scoped to the single question, red → blue → arbiter, **each of the three roles calls
   codex** — with no skip allowed.

## Context

The autonomous run drove a mature production project for ~40 day-increments with zero fabrications:
honest STOPs, red day-closes recorded red, every second-model skip flagged. The accountability layer
worked. What it revealed is that flags do not substitute for capability: single-model review caught
real criticals (including rejecting the architect's own crypto canon), but a retroactive codex sweep
still contested semantic rulings the review had accepted. The marginal value of the second model
concentrated exactly where decisions ratify semantics that are expensive to unfreeze later.

## Decision

- Bash on all role surfaces, scoped to second-model calls (`.claude/agents/*.md`, scoped-use block).
- `Panel:` field required in every ADR; review validates skip reasons on the merits and may block.
- Class-trigger list above ⇒ compact panel with codex on all three roles; the second-model fallback
  ladder of `core/second-model.md` applies, a real call failure is flagged with the literal error.
- Process ADRs (day entries, tranche slicing, record errata) stay solo + review, with the `Panel:` field.

## Consequences

- "Mandatory when available" (ADR-016) becomes enforceable: availability is now a property of every
  role, not of the harness owner's session.
- Panel volume rises only on the class-trigger subset (field estimate: +5–10% of day time), not on
  process ADRs — the compact scope keeps a panel at hours, not a day.
- Review gains a new first-class object (the skip reason), which makes threshold drift visible in
  the artifact stream instead of in retrospect.
