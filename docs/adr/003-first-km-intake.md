# ADR-003: The "first kilometer" — fix the dangling entry point with an edit, defer the intake pipeline

Date: 2026-06-27
Status: Accepted (implemented: the dangling entry point is closed by the edit; canonical intake
remains under gate O1 — the gate is open, this is not a status blocker)

> Decision reached by running the adversarial panel (red team → blue team → arbiter), see [core/adversarial-panel.md](../../core/adversarial-panel.md). It applies the norms of [ADR-001](001-scope-process-overlay.md) (process overlay, not a project-management framework; no owned debt) and [ADR-002](002-spec-driven-cplus.md) (don't build for unmeasured pain) to the "first kilometer."

## In short

"The first kilometer" is the entry into a project: which task to take on first. An audit exposed
a defect: the roles required the architect to "break down the **roadmap**," but a roadmap produces
nothing — it's a phantom, non-existent artifact. The root hole is closed by a **one-line edit**: the
architect breaks down not a roadmap, but the "next slice" from the already-existing
`docs/PROJECT-STATE.md`. We do **not** build a full intake pipeline (interview → product brief →
roadmap → backlog) — that would be scope creep toward project management, which the package's scope
forbids. Whether intake is needed at all will be decided by a retrospective on 2–3 real starts, not
by a debate between models.

## Context

An audit of the package's sufficiency for solo use revealed the "first kilometer" gap. The files
`roles/architect.md` and `core/task-protocol.md` required the architect to "break down the
**roadmap**" into `docs/day-<N>-guide.md`, but **the roadmap itself produces nothing**, and it isn't
even a line in the canonical artifact table. This is a phantom entry point: the solo operator
doesn't know which task 1 is the right one.

The first draft (v1) proposed an intake process: the architect interviews the user and generates
the chain `docs/product-brief.md → roadmap.md → backlog.md → day-1-guide.md`, plus a project
classification by **complexity** (lightweight "bot class" vs. full "SaaS class") chosen by the
user. New artifacts would be canonized in task-protocol and bootstrapped by the generator.

The operator's ground truth (solo): process weight scales with **project complexity**, not
headcount. A simple bot lives in a single window; a complex B2B product wouldn't have come into
being at all without the full pipeline.

## Decision

**A patch-only hybrid. We do not build the full intake pipeline (v1).** The arbiter's verdict:
the hole is real, but v1 fixes it along the wrong axis, at the wrong granularity, and with a
disproportionately heavy implementation.

**Built now** (unconditionally; a pure text edit of existing artifacts, 0 new ones):

- In `core/task-protocol.md` (the table) and `roles/architect.md` (lines 14, 42, 62, 64, 68), the
  wording "breaks down the **roadmap**" is replaced with "breaks down the **next slice** from
  `docs/PROJECT-STATE.md` (the "Next day" / Open questions section) or `docs/specs/`." The source
  of the slice actually exists: the PROJECT-STATE stub in `new-project.py` already carries "In
  progress" / "Next day" / "Open questions" sections. A long-term plan (roadmap) is optional and up
  to the user; the architect doesn't invent it, only lays out priorities the user has already set
  (see `architect.md` → business priorities; constitution PR-NN-02).
- In `examples/docs/PROJECT-STATE.example.md` and `examples/README.md`, references to "backlog" and
  "breaks down the roadmap" are removed.

**What we don't build** (killed by the panel):

- `roadmap.md` / `backlog.md` / `product-brief.md` as **canonical artifacts** of the package. This
  is scope creep toward project management and owned semantic debt that contradicts ADR-001; the
  package's roles deliberately do not define product priorities (`roles/sa.md`,
  `roles/architect.md`). The backlog is also dead weight — PROJECT-STATE already carries its
  function.
- **A hard-label project classification by complexity.** The package's cadence already works
  per-decision: the adversarial panel is triggered by the cost of error and irreversibility, C+ by
  a hard contract. A per-project "complexity" label duplicates and coarsens this existing
  mechanism.
- **A default of "not sure → full process."** This runs against the deliberate ADR-001 default
  (test-along + solo role map). The default remains lightweight; the heavy process only kicks in on
  an explicit signal.

**Decisive criterion (in one sentence):** the root hole is closed by a one-line edit + a patch
to one role; anything beyond that (an intake interview, a route hint) is a bet on value that
architecture cannot settle — only empirical evidence from real starts can.

## Consequences

**Pros:** the architect's dangling entry point is eliminated without a single new artifact and
without owned debt (the ADR-001 scope stays intact); scope hasn't leaked toward project management;
the per-decision cadence (panel / C+) is untouched and not duplicated; the ADR-001 default
(lightweight) is unchanged.

**Risks and open questions:**

- [ ] **Whether an intake protocol is needed at all** (empirical gate "O1"): settled by a
      retrospective on 2–3 real starts — if there was no loss at the entry point, never build the
      intake interview. A debate between models doesn't settle this. The question specifically: was
      there a real loss on "which task 1 is the right one," or does the operator already hold the
      slice in their head and only the entry point needed redirecting (this is the same
      retrospective as O2 in ADR-001).
- [ ] Is a route hint needed during decomposition (anchor "O2") — a recommendation like "many domain
      touchpoints → consider the SA/BA/QA-UAT pipeline; few → developer+reviewer in one window"?
      Here the predictor is the number of domain touchpoints, not the cost of a bug; the
      verification weight (panel/C+) is not to be touched; the operator decides. Or is the opt-in
      `--testing bdd` + the operator's intuition enough (it already exists: bot-class vs. SaaS-class)?
      Build only on confirmed benefit, not proactively.
- [ ] Solo verification of the entry point (anchor "O3"): if intake is ever built (O1), a single
      operator cannot distinguish "the gate was read" from "the gate was rubber-stamped" without a
      second pair of eyes — a residual risk of solo mode (like NP2 in ADR-001). Candidate mitigation
      (from the superpowers review): a separate design-review subagent with fresh context as a
      second pair of eyes on the slice itself **before** code. This is **not** an extension of the
      current `reviewer` (which reviews code after the developer, read-only) and not C+ (which is
      only for hard contracts, not a live domain) — it's a new pre-code entry-verification role.
      Under the same hard stop: build only on confirmed benefit (O1) + a separate panel/ADR on the
      role itself. We don't adopt the cosmetic form from upstream brainstorming (1 question at a
      time / multiple-choice / word limits): structured Socratic discovery already exists
      (`roles/sa.md`), and upstream also commits the spec itself, which contradicts
      `core/task-protocol.md` ("the agent doesn't commit").
- **Hard stop:** don't invest engineering days in the intake interview and route hint before gate
      O1 passes. If a retrospective shows the bottleneck is the absence of an **application**, not
      the entry point, that's a signal to reconsider ADR-001, not to build the intake pipeline.

## Alternatives considered

- **The full intake pipeline (v1).** Rejected: wrong axis (complexity instead of "cost of error
  × irreversibility"), wrong granularity (per-project instead of per-decision, which already
  works), 3 PM artifacts + an owned semantic API (contradicts ADR-001), a hallucinated roadmap,
  silently accepted solo (against the principles of "fact, not hypothesis" + PR-NN-02).
- **Splitting the cadence into two axes** (complexity → decomposition, cost of error →
  verification). Recognized as a real refinement, but it lives only as an optional route hint (O2),
  not as a primary mechanism: verification weight is already covered by the panel/C+ per-decision.
- **Do nothing.** Rejected: the dangling entry point is an actual defect (the roadmap as a
  non-existent artifact), and fixing it is unconditional and cheap.
