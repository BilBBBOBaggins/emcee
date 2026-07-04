# ADR-001: Package scope — process overlay, not app bootstrap

Date: 2026-06-27
Status: Accepted (implemented: README/stub reworded, test-along default, day-0-guide in the generator; item 3 refined by ADR-016)

> Update 2026-07-03: item 3 of the decision ("second model on the panel is recommended but not mandatory")
> is refined by [ADR-016](016-panel-second-model-mandatory-when-available.md) — mandatory **when available**,
> symmetrically for red/blue, with the same honest fallback. The body below is historical and was not rewritten.

> Decision reached by running the adversarial panel (red team → blue team → arbiter), see [core/adversarial-panel.md](../../core/adversarial-panel.md).

## In short

The package generator creates an **agent operating regimen**, not a working application — and that
is exactly how it should be. The decisive argument: owning an aging scaffold (go.mod, CI configs,
linters) across dozens of stacks is more than a single maintainer can sustain, and the package's
intended audience is a Claude Code operator who already initializes a stack with one command.
Accordingly, the README has been rewritten to make an honest promise, and the gap — "day one assumes
a green build" — is closed by the delegating `day-0-guide.md` guide.

## Context

The README promised a "quick start for a new project," but `new-project.py` only generates an
agent operating regimen (`core/`, `roles/`, `CLAUDE.md`, `docs/` skeletons) — **not a working
application.** There is no `go.mod` / `package.json`, no Makefile, no test runner, linter, CI, or
`.gitignore`. Meanwhile the day-one example already assumes that "the project is initialized and
`make test` is green" ([examples/docs/day-1-guide.example.md:5](../../examples/docs/day-1-guide.example.md)).

This gap between the promise and the actual output raised the question: should the generator be
extended into a full application bootstrap? Three scope options were considered:

- **A** — a full stack-specific app scaffold + onboarding wizard + solo mode by default.
- **B** — an honest process overlay on top of an already-existing project (rewrite the promises).
- **C** — a hybrid: scaffold behind a `--scaffold` flag, solo mode by default, second model (codex)
  with a fallback.

## Decision

**We build variant B+: process overlay + a delegating Day 0.** The generator does not own
toolchain artifacts — neither directly (as in A) nor behind a flag (as in C).

**Decisive criterion — who carries the version debt:**

- **Allowed:** an instruction to run an init command (`go mod init`, `uv init`,
  `create-next-app`). This is delegation — the package says *what to run*, but does not store the
  result.
- **Forbidden:** a stored result (`go.mod`, `pyproject.toml`, CI yaml, linter config) inside the
  package.

The main factor is the package's intended audience. It's a Claude Code operator who initializes
a stack with one command using the current version of the tool. Owning an aging scaffold would mean
taking on someone else's version debt across N stacks × N versions with no benefit. For a solo
maintainer this is more than can be sustained — the panel found this fatal for variant A.

**Concrete changes (constitute synthesis v2):**

1. **Wording.** README and stub: "quick start for a new project" → "an agent operating regimen
   on top of your project."
2. **Generator defaults:** `test-along` + a solo role map by default; BDD only behind an explicit
   `--testing bdd`. Update `day-1.example` and the self-test in sync.
3. **Adversarial panel:** the second model (codex) is recommended but **not mandatory.** If the
   second model is unavailable, a fallback protocol is mandatory (single model + strengthened
   self-critique + an honest note about the gap). Remove the reference to the private
   `~/.claude/CLAUDE.md`.
4. **New `docs/day-0-guide.md`** (in the generated project) on the delegation side: init commands,
   not stored results. This closes the gap "day 1 assumes a green `make test`."
5. **Fix the drift in the "Clean build" contract** in `stack/go.md` and `stack/python.md`, extend
   the self-test.

(These changes are separate from the point bugs A1–A7 from the preliminary review — those are
fixed independently.)

## Consequences

**Pros:** the false promise is removed; the entry barrier for solo use is lowered; the panel
works for an external user; the package focuses on its single moat — a mature agent operating
regimen.

**Risks and open questions** (decided by the user):

- [ ] **Key question (CRUX).** The package's audience is a Claude Code operator, not a novice
      without an agent. The entire ADR rests on this. If false — a full reconsideration (then A
      becomes possible as a different product for a different audience). Argument in favor: the
      package only functions through an agent at all (the `R D T` commands dispatch subagents), so
      "a novice without an agent" cannot use anything.
- [ ] Is the real cause of user churn a mismatched expectation (which B+ fixes) or the actual
      absence of an application (which would point toward A)? Settled by a retrospective on 3 real
      starts, not by a debate between models; data is needed.
- [ ] A panel without a second model is objectively weaker; the fallback reduces but does not
      remove this residue (NP2). This risk cannot be eliminated.
- **Hard stop — empirical gate "O1" (build only after a retrospective on 2–3 real starts):** do
  not build an owning scaffold or `--scaffold` until a user test (*after* the corrected promises)
  shows that stack initialization is a real bottleneck. If it does — that's grounds for a
  **separate** scope reconsideration, not an implicit green light for variant C. If initialization
  was not a bottleneck across 3 starts — never build it.

## Alternatives considered

- **A — an owning app scaffold.** Rejected: the non-aging core of A is already absorbed by B+,
  and owning version debt across N stacks is more than a solo maintainer can sustain; it also
  duplicates a task already solved by standard tools for an agent-audience that can run init itself.
  The panel found this fatal for A.
- **C — hybrid / `--scaffold`.** Rejected: the flag doesn't remove the maintenance debt, it only
  makes it conditionally invisible, plus it adds a second testing branch. The defensible core of C
  is terminologically identical to B+. If data about a bottleneck emerges — that's grounds for a
  separate reconsideration, not now.
