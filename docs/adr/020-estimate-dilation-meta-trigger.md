# ADR-020: Estimate-dilation meta-trigger

**Status:** accepted (2026-07-16)

## In short

An auditor's post-mortem on a long autonomous run found a stage whose estimate had **dilated ~9×** — the
work took roughly nine times its estimate — with **no rule in the regimen that reacts to that fact**. The
loop simply kept drifting: each day absorbed the overrun silently and moved on, and the blow-out was only
visible in retrospect, to an auditor reading the whole history at once.

This ADR adds the missing **meta-trigger**: when an estimate is exceeded by a set multiple, the architect
must **re-estimate and review the decomposition granularity, and record why** the blow-out happened. It is
a **self-correction and budgeting signal for a human over the loop**, not a stop and not a
corner-cut — this package's north star is **quality over tokens**, so the trigger is emphatically *not*
"go faster" or "cut scope." It is "notice that reality diverged from the plan by a multiple, and
re-examine whether the work was decomposed at the right granularity — under record — instead of drifting."

## Context

Estimates in the pipeline are cheap and approximate: the architect sizes a slice or a stage when breaking
it into day guides. That is fine — estimates are a planning aid, not a contract. The defect the audit
surfaced is not that an estimate was wrong; it is that **being wrong by a large multiple produced no
signal**. A 9× dilation is not noise. It almost always means one of a few things: the stage was
decomposed too coarsely (one "day" was really a week of hidden sub-tasks), a premise was wrong and the
work forked into unplanned recovery (cf. the premise-defect cascades in
[ADR-019](019-definition-of-ready-premise-executability.md)), or the problem was genuinely
under-understood at planning time. Each of those is a **useful thing to know** — and each is invisible if
the overrun is absorbed day by day with no threshold that forces a look.

Two framings were explicitly rejected as the *purpose* of the trigger:

- **A stop / budget cap.** "Estimate exceeded N× → halt" would trade quality for schedule, which
  contradicts the package's north star. A human over the loop may *choose* to stop, but the trigger does
  not stop anything.
- **A corner-cut / go-faster nudge.** "You're over budget, trim the work" is the opposite of what the
  package optimizes for. The trigger does not ask for less work; it asks for an honest re-look at how the
  work was sliced, on the record.

## Decision

Add an **estimate-dilation meta-trigger** to the architect's duties. When the actual effort/duration of a
stage or slice **exceeds its estimate by a set multiple** (default threshold **3×**; the project may tune
it, and records the chosen value), the architect performs a **mandatory re-estimation and
granularity/decomposition review, recorded** in the natural place (PROJECT-STATE's snapshot, the day
guide, or a short note — one short paragraph, not a report):

- **Re-estimate** the remaining work with what is now known, so the rest of the plan reflects reality
  rather than the stale original figure.
- **Review granularity/decomposition** — was the stage sliced at the right size? Should it have been
  several days, or split by a seam that only became visible during the work?
- **Record why** the dilation happened — coarse decomposition, a wrong premise, genuine
  under-understanding, external blockage. This "why" is the actual deliverable: it is a budgeting datum
  for a human over the loop and an input to better future estimates.

The trigger fires on the **fact of the multiple**, measured against the recorded estimate — not on a gut
feeling that something is slow, and not only when an auditor reads the history later. It is explicitly
**not** a stop, a budget cap, or a signal to cut corners; a human may act on the recorded finding, but the
regimen's obligation is the re-estimation-and-review-under-record, so the drift stops being silent.

## Consequences

- **Silent drift becomes a recorded event.** The class of failure the audit caught — an estimate dilating
  by a large multiple with nothing reacting — now has a defined reaction. The blow-out surfaces *while the
  loop runs*, in the artifact stream, instead of only in a retrospective audit.
- **Better inputs to future estimates.** The recorded "why" turns each dilation into a lesson about
  decomposition, feeding back into how the architect sizes the next slice — and often into DoR
  (ADR-019): a wrong premise is a common root of both a cascade and a dilation.
- **A budgeting tool for the human over the loop.** The record gives a human a concrete, thresholded
  signal to intervene on — or to consciously accept — rather than discovering the overrun after the fact.
- **North-star-aligned.** Because the trigger never asks for less work or faster work, it adds a
  self-correction loop **without** creating pressure to trade quality for schedule. The only cost is a
  short recorded review when a threshold is crossed.
- **Threshold is tunable, default 3×.** A multiple, not an absolute time, so it scales with the size of
  the stage; the project records its chosen value so "dilation" is a defined fact, not a judgment call.
