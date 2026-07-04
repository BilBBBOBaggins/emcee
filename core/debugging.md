# Debugging broken behavior

A separate file because debugging is the most frequent cause of bad agent behavior. Getting the
process right matters fundamentally.

## The user reported a bug — that's a fact

If the user says "X doesn't work" — X doesn't work. This isn't up for debate, it's a given.

But the bug's **cause** is a hypothesis that requires verification. The user sees the symptom, not
the cause.

The right opening: "Got it, X doesn't work. Checking the cause." — and the process below begins.

The wrong opening: "X doesn't work? Strange, it should work, maybe..." — that's arguing with the
user about their own experience.

## Simultaneous information gathering across every layer

The core principle of effective debugging. The antipattern is a vertical search, one layer at a
time.

Bad process (a typical agent failure):

1. Check the UI logs — see nothing
2. Check the Bridge logs — see nothing
3. Check the Core logs — see nothing
4. Check the external service's logs — there's the error

That's 3-5 wasted iterations, plus a context loaded with scraps from different places, plus
frustration.

The right process:

1. **Identify the whole chain** the operation passes through. For the current bug — which layers
   are involved, which modules, which external dependencies.
2. **For every link in the chain, work out where its logs/telemetry/metrics live**. If logs are
   missing somewhere — add logging at that level.
3. **Collect the logs of every link at once**, for the same time interval the bug occurred in. If
   the bug doesn't reproduce — reproduce it and collect.
4. **Correlate by time.** Look at what was happening on every layer at the moment of the bug, in
   parallel, not sequentially.
5. **Find the break** — where in the chain the data got lost, got transformed wrong, or the call
   never arrived at all.
6. Only after this, formulate a hypothesis about the cause.

## Related modules and services

A bug often crosses the boundary of a single module. If the bug is in module X, but X depends on Y
and Z — the logs of Y and Z are needed too.

Especially critical for:

- **Event-driven systems** (pub/sub, queues, signals/slots) — source and consumer in different
  modules
- **Asynchronous operations** — the initiator and the handler in different threads/processes
- **Distributed systems** — different services
- **Layered architectures** — the action passes through several layers in sequence

Rule: isolating to "just X" produces blind spots. Always widen the scope to the modules X interacts
with within the current operation.

## Prohibition on guessing

A repeat from principles.md, but it matters especially in the debugging context.

Forbidden phrasings during debugging:

- "Most likely the problem is in X"
- "Possibly this is related to Y"
- "Probably the bug is somewhere here"
- "I'll try changing Z and see"

If the agent catches itself in phrasings like these — it hasn't read enough. Go back to the
"collect the logs of every layer" step.

Allowed phrasing: "Read X.cpp:120-150 and the Y log for the moment of the bug. I see the call from A
never reaches B. The cause: at line 135, the condition isEnabled() returns false when true is
expected. Checking why."

## Localizing changes when fixing

A fix for a specific protocol / feature / provider must not touch shared code.

Example: a bug in EWS calendar sync. Wrong — change the shared `CalendarController` "because it's
cleaner that way." Right — fix it in the EWS-specific branch (`if (providerType == "ews")`, or
inside `EwsCalendarProvider`).

Only if the fix confirms the change is needed by every protocol — fold it into shared code. Until
confirmed — keep it protocol-specific.

The same rule applies to:

- Bugs on a specific platform — fix in a platform-specific branch
- Bugs with specific data — fix in that format's handler
- Bugs in an edge case — fix in the edge-case branch, not in the main path

Shared code changes only once it's explicitly confirmed everyone needs it.

## The "three attempts" rule

If the same bug still isn't fixed after three substantive attempts — stop.

Signs the attempts are substantive: each is based on a new understanding of the problem drawn from
logs and code, not on a random change.

Signs the attempts aren't substantive: you change random spots hoping it'll work, roll back, and
try another random spot. That's no longer debugging — it's guessing.

Action at three attempts: stop, state what's known and what isn't, describe it to the user, wait
for help.

## Bug-report format during debugging

Once the problem is found, the report includes:

~~~
PROBLEM: brief description
FILE:LINE: exactly where
CHAIN BREAK: [layer A] → [layer B] (where the data is lost)
EVIDENCE:
  - Log/code checked → what was found
  - ...
CAUSE: a concrete explanation in terms of the code
FIX: what changes and why it resolves the problem
~~~

The format is the same for internal debugging and for QA-to-developer handoff.

## Related rules

Test hygiene during debugging — in [quality-gates.md](quality-gates.md): "don't lose the logs"
(don't rerun a failed test without analyzing its log) and "don't bisect tests" (the first failing
run is a fact — analyze it, don't run it 10 times). The prohibition on guessing above is a repeat
from [principles.md](principles.md).
