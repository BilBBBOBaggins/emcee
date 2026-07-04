# PROCESS-METRICS — does the process weight pay off (example)

> **Opt-in, not for every project.** Set up this file only when you're rolling out a **heavy**
> process (the full SA→BA→QA-UAT→QA-E2E pipeline, C+ spec-driven, adversarial panel) and want to
> VERIFY that it catches defects beyond a cheap `developer+reviewer`. For a simple project (bot-class,
> single-pane mode), metrics are a needless ritual — don't set them up.
>
> Why: [ADR-002](adr/) STOP-3 requires measuring whether C+ catches a new class of defects beyond
> qa-uat+reviewer; [ADR-003](adr/) O1/O3 require retros of real kickoffs. Without this log, "the
> process pays off" is intuition, not fact — and an unfalsifiable process easily becomes a religion.
> The goal here is **correctness of the bet on process**, not bureaucracy: one line per caught defect.

## Interception log (one line per finding)

Who caught the defect → what exactly → would a cheaper step (developer/reviewer) have caught it? If
"no" — the step paid off; if "yes, always" — the step is in question.

| Date | Step (role/method) | What it caught | Would reviewer/developer have caught it? | Class |
|------|------------------|-----------|-------------------------------|-------|
| 2026-06-14 | QA-E2E | invite went out, but the email wasn't delivered (bridge→provider break) | no (unit tests were green, the break only shows in the full stack) | paid off |
| 2026-06-15 | adversarial test-review (C+) | parser tests didn't cover empty and max-length input | no (the implementer would have written the same convenient tests) | paid off |
| 2026-06-18 | panel | architecture decision "one shared worker" = single point of failure under load | no (surfaced only in red↔blue) | paid off |
| 2026-06-20 | QA-UAT | scenario didn't describe the failure on a duplicate email — the feature silently failed | disputed | under watch |

## Escape defects (slipped through the ENTIRE process into production)

Defects found by users/in production — what should have caught them and why it didn't.

| Date | Defect | Which step SHOULD have caught it | Why it didn't |
|------|--------|------------------------------|------------------|
| — | (none yet) | | |

## Verdict on the stop gates (revisit every 2-3 features)

- **C+ (ADR-002 STOP-3):** over 2-3 features, did adversarial test-review catch ≥1 class of defects
  beyond qa-uat+reviewer? → YES = C+ is justified, keep it. NO = roll back to D (even the markdown
  layer didn't pay off).
  *Current status: [fill in after 2-3 features]*
- **Heavy pipeline (ADR-003 O1):** were there real interceptions at QA-UAT/QA-E2E/panel that
  developer+reviewer wouldn't have given? → YES = the pipeline is justified for this class of
  project. NO after 3 features = drop the cadence (this is the user's decision, not the agent's —
  PR-NN-02).
  *Current status: [fill in]*

Pruning: the log is episodic (see [core/memory.md](../../core/memory.md) → pruning). Old lines go
cold over time (git history); keep the last 2-3 features + verdict hot.
