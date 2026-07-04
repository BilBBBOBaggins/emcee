---
name: debugging
description: A method for debugging broken behavior — simultaneous log collection from every layer of the chain, finding the break, no guessing, the three-attempt rule. Use when something doesn't work, a test fails, there's a stack trace, or the root cause of a bug needs to be found.
---

This project's debugging discipline. **Full method in the `core/debugging.md` file** (from the project root): read it in full before debugging.

Briefly (so you don't go wrong even without opening the file):

- The user reporting a bug is a **fact**; the cause is a **hypothesis**, requiring verification against code/logs.
- Collect logs from **all** links of the chain **simultaneously** (not one layer at a time), correlate by time, find the break — where the data was lost/didn't arrive. Only then formulate the cause.
- Don't guess ("most likely", "probably" are forbidden). Not sure → you haven't finished reading.
- Localize the fix (protocol/platform/edge-specific), don't touch shared code without confirmation.
- Three-attempt rule: not fixed after 3 substantive attempts — stop, go to the user.
- **When NOT to:** this is root-cause search for something ALREADY broken. Not for a new feature/planning (→ spec-driven/architect). When the situation matches, invoke the method, don't debug by gut feel (see `core/skills.md`).
