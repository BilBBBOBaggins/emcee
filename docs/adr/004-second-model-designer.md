# ADR-004: Second model for all roles (narrow, opt-in) + a dormant Designer role

Date: 2026-06-27
Status: Accepted (implemented: core/second-model.md + dormant roles/designer.md under gate O1-D)

> Decision reached by running the adversarial panel (red team → blue team → arbiter), see [core/adversarial-panel.md](../../core/adversarial-panel.md). Applies the norms of [ADR-001](001-scope-process-overlay.md) (the package doesn't own debt) and [ADR-003](003-first-km-intake.md) (activating a new capability happens under a gate tied to the operator's retrospective).

## In short

The operator requested two features. First — give a second model (codex) to all roles, not just
the panel and C+: done as a single core doc, `second-model.md`, with narrow opt-in triggers (not a
line added to eight role files). Second — a Designer role that draws a mockup: built **dormant** and
**text-only** — Designer produces a wireframe as code straight from the spec, while a raster mockup
remains an ephemeral "for the eyes" scratch artifact and never enters git. The raster path as a code
source (image-gen → vision → code) and PNG as a versioned artifact were thrown out: unreliable and
contrary to the package's scope.

## Context

The operator (solo, ground truth) requested two features:

- **(A)** give a **second model (codex) to all roles**, not just the panel and C+.
- **(B)** a **Designer** role that draws a mockup via codex and translates the image into a
  wireframe, with versioning of both the PNG mockup and the wireframe code.

The premise was verified (web, 2026): the codex CLI does generate images (gpt-image-2) and
accepts them as input (vision), so the pipeline is technically possible. But v1 in its original form
ran into the package's norms.

## Decision

**We build narrow and text-only; we discard the raster path; Designer's activation goes under a
gate.**

**A. Second model — `core/second-model.md`** (built now):

- A single core doc with **narrow opt-in triggers** — "when any role calls codex for a second
  opinion" — on high-stakes output (reviewer on findings, architect before an ADR, SA/BA on
  requirements, debugger on a hypothesis). This is **not** a line added to eight `roles/*.md`
  files — such a touchpoint would be dead debt.
- **Opt-in, not mandatory.** "Second model (codex) at every step" was rejected: that's ritual plus
  a squeeze on the second model's quota limits.
- **Honest caveat:** codex is a code/reasoning model; as a reviewer of design or requirements it's
  weaker, so on non-code its use should be flagged and its benefit measured (in PROCESS-METRICS).
- **Doesn't weaken local protocols:** if the panel or C+ is running, their own rule about codex
  applies; the general second-model is a separate opt-in for ordinary roles.

**B. `roles/designer.md` — a dormant regimen** (built now, zero runtime):

- The method is written in markdown, but the role **isn't in `roles.json`** → no number, the
  numeric pipeline doesn't invoke it. An ad-hoc direct prompt is manually reading the method, not
  activation.
- The output is a **wireframe as CODE** straight from the spec (HTML / SVG / a skeleton):
  versionable, dev-ready, diffable.
- **The mockup image is an ephemeral "for the eyes" option** in a path that's ignored by design
  (`scratchpad/design/`). It is not committed and is not a code source. There is deliberately no
  `.gitignore` rule for it — so Designer first offers to add one for the operator. There's no
  reverse reading of "PNG → code."
- Designer-as-a-role-instruction in the user's repository is delegation (the same way day-0
  delegates init); the package doesn't own design artifacts → ADR-001 stays intact.

## What was discarded (found fatal by the panel)

- image-gen → PNG → vision → code **as a code source** (a raster dev contract is unreliable:
  Design2Code / DCGen hallucinate layout).
- A PNG mockup as a **canonical versioned artifact** + UI regression in the repository (a binary
  contradicts ADR-001: it's not diffable, it goes stale).
- A "call codex" line in eight roles; a mandatory codex pass.

## Consequences

**Pros:** a second pair of eyes is generalized across the whole pipeline without touchpoint
debt; Designer is available as a method with no owned debt and no binary in git; the ADR-001/002/003
norms stay intact; role numbers 0–7 are untouched.

**Risks and open questions:**

- [ ] **O1-D — Designer's activation stop-gate.** Activate Designer (a number in `roles.json`, a
      spot in `task-protocol.md`, generator bootstrap, a self-test invariant) only after a
      retrospective on 2–3 real UI starts shows a loss from "no wireframe." No loss → don't
      activate.
- [ ] Log the benefit of the second model (codex) on non-code work (SA/BA/design) in
      `docs/PROCESS-METRICS.md`. If across 2–3 features it doesn't catch a class of defects, narrow
      the triggers back to reviewer/architect/C+.
- [ ] The second model (codex) runs on a limited quota; as call frequency grows, watch the rate
      limit (narrow triggers are the primary defense).

## Alternatives considered

- **v1 (codex mandatory for everyone + Designer with a PNG canon + raster vision → code).**
  Rejected: mandatory = ritual + rate limit; the PNG canon contradicts ADR-001; raster → code is
  unreliable; activation without a gate contradicts ADR-003.
- **codex applied narrowly only in reviewer/architect.** Absorbed by `second-model.md`'s narrow
  triggers (the same spots + SA/BA/debugger under measurement) — not a separate entity.
- **A Designer that only produces wireframe code without an image.** Essentially adopted; the image
  is kept as an ephemeral "for the eyes" option, not as a versioned artifact.
