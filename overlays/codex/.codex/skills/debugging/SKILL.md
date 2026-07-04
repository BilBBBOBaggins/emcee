---
name: debugging
description: Method for debugging broken behavior — simultaneous log collection across every layer of the chain, finding the break, a ban on guessing, the three-attempt rule. Use when something isn't working, a test is failing, there's a stack trace, or you need to find the root cause of a bug.
---

This project's debugging discipline. **Full method in `core/debugging.md`** (from the project root): read it in full before debugging. (Discovery on Codex — this SKILL.md in `.codex/skills/debugging/`.)

In short (so you don't get it wrong even if you haven't opened the file):

- The user reported a bug = a **fact**; the cause = a **hypothesis**, requiring verification against code/logs.
- Collect logs from **all** links of the chain **simultaneously** (not one layer at a time), correlate them by time, find the break — where the data was lost/didn't arrive. Only then formulate the cause.
- Don't guess ("most likely", "probably" — forbidden). Not sure → you haven't finished reading.
- Scope the fix (protocol/platform/edge-specific), don't touch general code without confirmation.
- Three-attempt rule: not fixed after 3 substantive attempts — stop, escalate to the user.
- **When NOT to:** this is for finding the cause of something ALREADY broken. Not for a new feature/planning (→ spec-driven/architect). If the situation matches — invoke the method, don't debug by instinct (see `core/skills.md`).
