# ADR-008: PROJECT-STATE — a snapshot, not a journal (anti-sprawl)

Date: 2026-06-27
Status: Accepted (implemented: snapshot canon in core/memory.md + roles/architect.md §Updating PROJECT-STATE, generator stub)

The decision was reached not via an adversarial panel but through a brainstorm with the operator: the question is doc-only, easily reversible, and not load-bearing (it changes no code architecture). It builds on the memory model from [core/memory.md](../../core/memory.md).

## In short

`docs/PROJECT-STATE.md` is the status file the architect reads on entering each day. In the stub it
had a **"Done"** section that got appended to as work was completed. It was always appended to and
never pruned, so the file slowly turned into an unreadable cumulative log.

Decision: PROJECT-STATE is a **hot snapshot of "where the project stands now", not a journal of
"what was done"**. The "Done" section was removed. On entering a day the architect **rewrites the
file in place and discards what has served its purpose**, rather than accumulating. The "what and
when" history lives in git, the "why" decisions live in ADRs. Project memory has three layers: a hot
snapshot (PROJECT-STATE) + curated decisions (ADRs) + searchable git. A thousand commits don't
overflow the context, because history is never loaded wholesale — it's queried point by point.
`regimen-doctor` softly warns (🟡) if the snapshot has grown anyway.

## Context

Operator (solo, ground truth): "What should be done so PROJECT-STATE doesn't sprawl into an
unreadable mess?" During the brainstorm he asked two clarifying questions, and both hit the root:

1. **"Commits will eventually number in the thousands — won't they overflow the context anyway? Is
   that inevitable?"**
2. **"Does the agent itself prune it, or does the user?"**

The source of the pain is the PROJECT-STATE stub with its "Done" section. It's a **sprawl magnet**:
always "hot" (read on entering every day), grows without a ceiling, and duplicates what's already in
git. A solo developer will keep appending to it but will not prune it by hand.

## Decision

**PROJECT-STATE is a snapshot, not a journal. The agent prunes it. History and the "why" live in
git and ADRs.**

Specifically:

1. **Removed the "Done" section** from the stub ([new-project.py](../../new-project.py)) and from
   the reference example
   ([examples/docs/PROJECT-STATE.example.md](../../examples/docs/PROJECT-STATE.example.md)). The
   file's header now states the rule "a snapshot, not a journal." The stack and commands were removed
   from the snapshot — they're durable and live in `CLAUDE.md`; no reason to duplicate them.
2. **The architect prunes it on entering a day**
   ([roles/architect.md](../../roles/architect.md) → "Updating PROJECT-STATE"): it updates the file
   **by rewriting it in place**, discarding resolved open questions, closed risks, and stale "In
   progress" items. No fact is lost in the process — it stays in git.
3. **The project's three memory layers are made explicit** (in
   [core/task-protocol.md](../../core/task-protocol.md) and
   [core/memory.md](../../core/memory.md)):
   - **hot snapshot** — PROJECT-STATE, rewritten in place, target ≤ ~1 screen;
   - **curated "why"** — `docs/adr/`, a limited set of load-bearing decisions;
   - **searchable git** — the entire "what and when" history, queried point by point, never loaded
     wholesale.
4. **A commit message convention** (Conventional Commits: `type(scope): what`) is fixed in
   `task-protocol.md`. Without meaningful messages, git doesn't work as "cold memory" —
   `git log --grep` over "fix stuff" is useless.
5. **`regimen-doctor` softly warns** (🟡, doesn't block) if PROJECT-STATE has passed ~200 lines —
   this is a backstop reminder to prune.

**Answers to the operator's two questions** (recorded because they are themselves the rationale):

- **Thousands of commits are not inevitable sprawl.** The worry assumes that history must be
  "held onto" in order to be known. It doesn't: it's **never read wholesale**, it's queried point by
  point — `git log --since=…`, `--grep`, `git log <path>`, `git shortlog`. "What mattered" doesn't
  live in a thousand commits but in a dozen **curated ADRs** (you read 10 files, not 1000 commits).
  That's why a cumulative section in a file is strictly the worse option: always hot, grows forever,
  duplicates git.
- **The agent prunes it, not the user.** This is the natural point — the architect already updates
  PROJECT-STATE on entering a day. The file is under git, so pruning is **safe and reversible** (git
  is the undo). Manual pruning by the user is exactly the thing that doesn't happen and therefore
  accumulates sprawl. The doctor's soft warning is insurance in case the agent still doesn't prune.

## Consequences

**Upsides:** PROJECT-STATE stays a short snapshot (≤ ~1 screen) instead of a growing log; the model
mirrors the package's own memory discipline (`core/memory.md`: hot core + thin index + cold store);
pruning is reversible because everything is under git; the human gets an explicit answer to "what to
do so it doesn't bloat."

**Risks and open questions:**

- [ ] Pruning discipline rests on the agent. If the architect doesn't prune on entering a day, the
      file will still creep up. The only backstop is the doctor's soft 🟡. We deliberately don't put in
      a hard gate: a snapshot's size legitimately fluctuates, a block on line count would be too
      blunt.
- [ ] The 200-line threshold is an estimate, not a measurement. Adjust if 🟡 fires too early or too
      late on real projects.
- [ ] Extreme scale. Over years and tens of thousands of commits, even point queries against git get
      noisy. The curated layer (ADRs plus, if needed, the occasional phase summary) addresses this,
      not git. We're not building this now — the need isn't there yet.

## Alternatives considered

- **Keep the cumulative "Done" section.** Rejected: always hot, grows without a ceiling, duplicates
  git — this is sprawl itself.
- **The user prunes manually.** Rejected: manual pruning is exactly the thing that doesn't happen;
  it's precisely what accumulates the "unreadable mess."
- **A hard doctor gate (🔴) on size.** Rejected: a snapshot legitimately varies in size; a hard block
  on line count is too blunt — the soft 🟡 was chosen instead.
- **Rename the "Next day" section → "Next slice".** Rejected: touches 8 files, including immutable
  ADR-003 and ADR-005 (violating their read-only status), and has nothing to do with anti-sprawl —
  it's a sprawl of edits for cosmetics.
