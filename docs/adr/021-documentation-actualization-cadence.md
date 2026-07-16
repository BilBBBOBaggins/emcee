# ADR-021: Documentation actualization cadence — docs stay current as a duty of the loop

**Status:** accepted (2026-07-16)

**Panel:** skipped because — direct owner directive with a working field precedent (the same rule ran
as a project-level ADR inside an autonomous production run); a process rule, trivially reversible,
touching no class trigger (no frozen semantics, money, boundaries, or migration contracts).

## In short

Documentation drifts unless the loop itself owns keeping it current. A long autonomous field run
showed the exact failure shape: human-facing functional docs were delivered once at a stage gate,
accepted, and then frozen — nothing obliged later stages to grow them, so every feature delivered
after the gate existed only in code and agent-facing artifacts. The fix that worked in the field
(a project-level housekeeping ADR) is promoted into the package as a standing duty with two tiers:

1. **Every day exit (cheap, local).** The architect's day exit runs "statuses = fact" over the docs
   the day's substance touched: any claim the day made stale — a status line, a feature list, a
   "not implemented yet", a README promise — is updated in the same exit, or explicitly queued with
   an owner. If the project keeps **human-facing docs** (README, a functional set, guides), the exit
   asks one question: "did today change user-visible behavior?" — if yes, the human-facing delta
   becomes a named task, and the **stage/slice close gates on it** (the docs gate is part of "done",
   same rank as tests).
2. **Every ~3 days (tunable; default 3).** The slice carries a mandatory housekeeping task:
   a statuses=fact sweep across live docs, a dead-link check (machine gate where the project has
   one), archive candidates (superseded docs moved out with a ledger of what replaced them), and
   forward-notes. The day-close of such a day confirms the check ran — or records an explicitly
   sanctioned deferral (named in an ADR/day entry, never silent).

## Context

Two forces make doc drift the default. First, day guides reward substance: code, tests, gates — a
doc update has no failing test, so it silently loses every priority contest. Second, human-facing
documentation is typically produced as a one-time gate artifact (a stage-close deliverable), which
makes it correct exactly once. The field run's owner had to intervene twice: once to gate a stage
close on full human-readable documentation, once to institute a recurring housekeeping check after
a single dead link cost a day of work. Both interventions worked; neither should require an owner.

## Decision

- The day-exit "statuses = fact" duty and the human-facing-delta question live in the architect's
  day cycle ([roles/architect.md](../../roles/architect.md) → "Duties on entering a day").
- The recurring housekeeping task (default every ~3 days; the project may tune and record the
  cadence) is the architect's slicing responsibility; the day-close verifies presence or a
  sanctioned deferral.
- The project entry file's documentation section states the principle: documentation follows
  delivered functionality — a stage whose substance changed user-visible behavior does not close
  with the human-facing docs describing the previous stage.
- Machine layers stay machine: where the project has a link/consistency gate (doctor-style), it
  runs on every check — cadence applies to what machines can't judge (statuses, coverage, archive).

## Consequences

- Doc currency stops depending on owner interventions; the loop self-reports drift (a skipped
  check is a recorded deferral, visible in the artifact stream).
- Cost is bounded: the daily tier only touches docs the day actually made stale; the sweep tier is
  one task per ~3 days. The known failure mode — housekeeping tasks losing priority contests
  against substance — is countered by making the day-close verify the check, not by trusting the
  slice to include it.
- Human-facing docs become a rolling deliverable, not a gate-day artifact; acceptance of a stage
  includes their delta.
