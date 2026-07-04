# Agent memory — how a project remembers context between sessions

How to save project knowledge so the agent picks it up without bloating the startup context. This
is about **memory architecture**, not about work rules (see [principles.md](principles.md)) and not
about automated gates (see [quality-gates.md](quality-gates.md)).

**Neutrality boundary (P3, ADR-010/011).** The memory **discipline** itself is `universal`: a thin
index + lazy topic files, load only what's relevant, don't duplicate, prune, a recovery checkpoint
before context loss. The **mechanisms** below (Claude Code's two native systems, the `PreCompact`
hook, `/rewind`, `/schedule` and `/loop` routines) are `origin: harness:claude-code`. On another
runtime — its own memory mechanism + entry-file hierarchy (see the map in
[portability.md](portability.md)); the discipline ports over as is. Below is the Claude Code
implementation (verified against the Claude Code docs → memory; current as of 2026).

## Two native memory systems

Claude Code loads both at the start of **every** session and treats them as context (not as
enforced config — a hard prohibition is a `PreToolUse` hook, not a line in memory):

1. **CLAUDE.md — what you write** (rules, architecture, commands). Loaded **hierarchically**: Claude
   walks up the directory tree and **concatenates** every file it finds (from root to cwd; the one
   closest to the run is read last); nested `CLAUDE.md` files load lazily when files in their
   directory are read.
2. **Auto-memory — what Claude writes for itself** (observations, patterns). Lives **outside the
   repository**, per git repo: `~/.claude/projects/<project>/memory/` with a `MEMORY.md` index +
   topic files. At startup only the first ~200 lines / 25KB of `MEMORY.md` load; topic files load on
   demand.

Division of responsibility: **rules and architecture → CLAUDE.md** (in the repo, versioned,
reviewed); **the agent's accumulated observations/habits → auto-memory** (machine-local, not in
git).

## Discipline (the main part)

The goal of the discipline below is **output quality, not token savings**. Clean, relevant context
raises adherence and reasoning quality; a bloated context and wall-of-text files degrade them. That
it's also cheaper along the way is a nice side effect, not the motive (see the package's north star:
quality over token economy).

- **<200 lines per memory file.** Longer, and the model follows it worse. **Break up** a large
  regimen into nested per-directory `CLAUDE.md` files (each <200 lines), not one wall-of-text file.
- **Thin index + lazy topic files.** `MEMORY.md` (and the root `CLAUDE.md`) is a map with links, and
  the details live in separate files pulled in as needed. The startup context is only what's
  relevant, so the model reasons on a clean slate instead of digging through noise.
- **Tiered / on-demand loading.** Don't load "just in case" (= [principles.md](principles.md):
  minimal context — for quality's sake, not cheapness). Keep large logs/reference material behind a
  link, read on trigger.
- **Don't duplicate.** One fact, one place. A project rule goes in CLAUDE.md; an agent observation
  goes in auto-memory. A duplicate between the two drifts.

The flip side of the north star: where quality demands **more** work — a second model in the panel
always, verification passes, multi-agent checks, maximum effort — that's the default, not "budget
permitting." Context discipline frees up room for reasoning; it doesn't cut analysis depth.

This package is already built on this discipline: `CLAUDE.md` is the entry point with links, heavy
rules are moved out into `core/`, `roles/`, `stack/` and pulled in situationally, not all at once.

## Pruning — archive, don't erase; update in place

Long-lived memory degrades if you only ever append to it: hot context balloons, and
stale/contradictory notes **actively harm** (the agent acts on a wrong fact — worse than having no
memory at all). Pruning here is about **correctness**, not size. It's done so there's practically no
loss:

- **Durable facts/rules** (how the project is built) — **update in place**, don't archive. This
  layer is bounded and stable; CLAUDE.md holds *current* facts, overwriting stale ones, rather than
  growing as a history.
- **Hot state snapshot** (`docs/PROJECT-STATE.md`) — overwritten in place on every update (architect
  on entering/exiting a day): resolved/stale material is **pruned**, not appended to. This is a
  snapshot of "where we are now" (target ≤ ~1 screen), not an accumulating log — "what was done and
  when" comes from git, "why" comes from `docs/adr/` (curated decisions). PROJECT-STATE pruning
  discipline — [../roles/architect.md](../roles/architect.md).
- **Episodic material** (logs, decisions, progress) — goes **cold** over time: git history + a
  separate archival topic file if needed. Retrieved by **searching on demand** (`git log`/`git
  grep`/Read), not via a standing pointer.
- **The index stays lean.** Leave a pointer in `MEMORY.md`/the index ONLY for "cold, but the agent
  should know it exists" — curated entries, not one line per archive item. Otherwise the index
  itself becomes a wall of links = the same bloat, one level removed.
- **Don't hard-delete anything non-versioned.** Git-backed material (CLAUDE.md, `docs/`) is safe to
  delete — history keeps everything; auto-memory outside git — **archive, don't erase**.

Antipattern: "append + archive everything with a pointer" → memory turns into a growing wall of
links. The right end state is **a small, stable hot core (current facts) + a thin index of what's
live + a searchable cold store**.

## Checkpoint before compaction (optional)

A long session hits the context limit and gets **compacted** — some detail is lost. To keep state
from getting lost, the package ships a ready-made `PreCompact` hook
[.claude/hooks/checkpoint-precompact.sh](../.claude/hooks/checkpoint-precompact.sh): before
compaction it writes a recovery checkpoint (time, trigger, path to the transcript) to
`docs/checkpoints.md`. It's enabled in `.claude/settings.json` (the `PreCompact` section is already
present in `settings.json.example`).

This fixes a **recovery point** (you read the transcript + `git log` → continue). For a
**meaningful** summary in the checkpoint — extend the script with a model call over the transcript.
Checkpoints are episodic: clean/archive them per the pruning rule above. Known edge case:
`PreCompact` may not fire on a manual `/compact`.

Meaningful capture is manual, done while context is still alive: at the end of a significant
session, ask the agent to "summarize the session: what had to be figured out along the way, and
what of that should go into the regimen/entry file" (the capture-what-to-remember pattern from
Anthropic's prompt library). The agent already knows what it had to figure out — getting
suggestions is cheaper before context is lost than reconstructing them afterward. This complements,
not replaces: the PreCompact hook writes only the recovery point, and "Evolution of this document"
reacts to already-repeated mistakes — this technique is proactive. Filter what's proposed as usual
(don't duplicate what's already in the repo/guides).

This is about losing state on **context compaction**. For "I just broke it with an edit" — the
native **`/rewind`** (Esc-Esc): rolls code/dialogue back to a snapshot before the change (see
[principles.md](principles.md) → recovery from breakage). Two different tools: the checkpoint is
recovery after compaction, rewind is rolling back a fresh breakage.

## When memory is a process, not a place

For background/recurring work between sessions, memory is complemented by automation, not files:

- **Routines** — configurable Claude Code cloud agents (prompt + repo + connectors), triggered by
  cron / API / a GitHub event, run on Anthropic's infrastructure (work with the laptop closed).
  Suited to overnight upkeep (pick up a bug → fix it → draft a PR). Launch/configure via
  `/schedule`.
- **Iterative loops** (`/loop`, the Ralph Wiggum approach) — for self-pacing tasks with a stop
  condition.

This isn't part of the startup context — it's a way to launch work that writes its own result into
memory/a PR. Keep a **human gate on high-stakes output** (Anthropic's own engineers' practice:
autonomy is growing, but what matters is still validated by a human).
