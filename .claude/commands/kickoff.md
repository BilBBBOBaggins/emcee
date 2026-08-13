---
description: Project start — architect in kickoff mode (essence → CLAUDE.md → first slice → day guides)
argument-hint: "[a couple of words about the project] — optional"
---

Become the **architect** and run **kickoff** strictly per `roles/architect.md` → the "Kickoff — starting
a project" section. Project context (if given): `$ARGUMENTS`.

This is the entry into a project when there are no days or roadmap yet (the `N`/`R D T` grammar doesn't apply here). Briefly:

1. **Routing questions** (one at a time): what product, for whom, stack, routing signals (a separate
   QA track? a domain expert? UI?). **Stop rule:** NOT domain discovery (happy path / edge cases /
   acceptance) — that's the SA's job, not the architect's.
2. **Fill in `CLAUDE.md`** with the provenance rule (`[from user]`/`[code:path]`/`[output:cmd]`; no
   source → a visible `{{placeholder}}`, don't guess).
3. **Record what was said** in `docs/PROJECT-STATE.md` (existing sections; priorities from the user, not
   invented).
4. **Load-bearing architecture** → `/panel` → ADR.
5. **First day guides** — `docs/day-0-guide.md` (stack init, if a new project) + `docs/day-1-guide.md`.
   If the generator already created `day-0-guide` (`--mode new`), do NOT write a second one — update
   the existing file in place where the user's answers change it, otherwise leave it as is.

`/kickoff` does NOT replace `day-0-guide` — it comes BEFORE the first working day and produces it itself. Full
narrative (kickoff + ongoing + an example with all roles) — `core/pipeline.md`. Lightweight by default —
scale the depth to the project. For an existing project — first read the code, reconstruct CLAUDE.md.
