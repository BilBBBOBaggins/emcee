# ADR-017: Machine-checked plan invariants — harden the checker, then gate at the done boundary

Date: 2026-07-06
Status: Accepted

> Decision reached via a full adversarial panel run (red team → blue team → arbiter, codex gpt-5.5
> xhigh engaged symmetrically on both sides per [ADR-016](016-panel-second-model-mandatory-when-available.md),
> plus a final codex consistency pass on the synthesis). Working artifacts:
> `scratchpad/panel/plancheck-{v1,red-r1,blue-r1,arbiter-r1,v2}.md`. Idea source: an external AI IDE's
> "dynamic plan" (a backend state machine guarantees plan integrity — a plan cannot be lost,
> abandoned half-done, or transition invalidly).

## In short

The question was: should emcee get a **machine check of pipeline invariants** ("the machine, not
discipline, verifies the plan") — a lint or hook catching (1) a task declared done without its
quality-gate artifacts, (2) a day guide abandoned half-closed, (3) stale STATE/guide files?

The panel's answer: **build (1) only, in a revised composition; reject (2) and (3).** The initial
framing ("the checker already exists — QG-NN-05's `regimen-doctor.py --qg` — only its launch point
is missing") was **refuted by code and by a live run**: the checker had proven false-green paths
(vacuous pass when the `## Frozen scope` section is missing or format-drifted, evidence spoofable
by `@qg:` mentions in committed prose, no git awareness) and false-red paths (`build-qa/` — the
canonical QA directory — invisible to the scan). The claim "Balatro run 2 validated the checker"
was an epistemic substitution: run 2 was gated by the orchestrator's QA loop; `--qg` never ran in
that loop, and on that very tree the QG check passes **vacuously**.

The surviving formula: **the machine verifies the presence of evidence; a role holds the
completeness of the referent; the enforcement point is the done boundary at the orchestrator/CI.**
No state machine over markdown, no tooling that parses prose (the ADR-001/006/009 boundary holds).

## Decision

Three phases, order mandatory:

1. **Phase 1 — harden `regimen-doctor.py` (code; precondition for any launch point).**
   Under `--qg`: vacuous pass and format drift become 🔴 (a missing/unparseable `## Frozen scope`
   section may not be silent); per-bullet strictness inside the section (prose notes live outside
   it) and the `Shipping root(s):` line canonized as a machine element; **evidence scan by
   allowlist** (code/tests + a fixed manifest path) instead of the whole tree — closes prose
   spoofing entirely; "checked-in" means the **git index** (not the worktree), a non-git tree
   under `--qg` is 🔴; SKIP_DIRS matched by path segment against the relative path (fixes
   `build-qa/` and parent-`build/` false negatives); explicit `waiver: <reason>` syntax plus a
   printed list of waived items; 🔴 on duplicate scope-ids; the `--qg` help string drops
   "pre-commit" (it is code, so it belongs to this phase, not the docs-only phase 2).
   Acceptance: blue team's synthetic trees t1–t7 give the expected verdicts; `~/balatro-clone-2`
   goes 🔴-vacuous. Stop condition: if the allowlist false-reds legitimate non-code evidence
   carriers (`.feature`, SQL fixtures) with no cheap fix — stop and return the question rather
   than silently widening the scan back onto prose.

2. **Phase 2 — composite slice-close gate (docs-only; after phase 1 merges).**
   The recipe `doctor --qg && {{check-command}} && {{test-command}} && clean tree` at boundaries
   the machine actually knows: the orchestrator's `projectDone`/slice-done (a paragraph on the
   orchestrator's duty in `core/pipeline.md`) and CI/pre-push (a snippet in
   `core/quality-gates.md`). Composition lives **outside** the doctor (it stays read-only and
   stack-independent). *Amended 2026-07-06 (operator ruling, see Consequences → Strategic):* **no
   hosted-CI integration is shipped** — the canon records the provider-neutral command and the
   boundary semantics only; enforcement points are the orchestrator (autonomous mode, mandatory)
   and the architect/user at slice close, with a local `pre-push` hook as optional prose, no
   per-provider config owned by the package (the ADR-001/006/009 owned-debt class). This returns QG-NN-01/02 to the gate (live incident: run 2's QA files with
   strict errors on a clean product) and the clean-tree requirement closes the index≠HEAD gap.

3. **Phase 3 (optional, opt-in) — "readiness context" hook.** A PostToolUse hook on writes to
   `docs/PROJECT-STATE.md`, injecting **only 🔴 findings** via `additionalContext`; named
   readiness-context, not accountability; `origin: harness:claude-code`. Built only after
   phase 1 and after verifying the live hook docs (`additionalContext` semantics,
   resume/replay behavior). If unconfirmed — not built; phases 1–2 are the complete scope.

**Rejected (on the record):** a "half-closed day guide" lint — no incident behind it (the Balatro
failure was over-declared done, already covered by QG-NN-05), and it would require making day
guides machine-parseable, the owned-debt class killed by ADR-001/006/009; a staleness indicator
for STATE/guides — no incident, noisy heuristic, alarm fatigue (its real subclass is closed by the
composite gate); a soft SessionStart/Stop hook — no working configuration (expected-yellow
mid-slice normalizes ignoring; exit-0 Stop output is invisible; a blocking variant is per-turn and
not "soft"); pre-commit as the enforcement point — false reds mid-slice.

## Amends ADR-015 / QG-NN-05

Three points of the **Accepted** ADR-015 enforcement text change; this section makes the amendment
explicit rather than a silent re-litigation (the gate's substance and the
`` - `SCOPE-ID` — criterion `` format are preserved/strengthened):

1. **Waiver syntax:** "a `waiver` marker on the line" (substring) → explicit `waiver: <reason>`
   (this converges the canon with `examples/docs/PROJECT-STATE.example.md`, which already uses the
   colon form).
2. **"pre-commit" removed** from "for CI/pre-commit/exit" in `core/quality-gates.md` §QG-NN-05 and
   from the `--qg` help string.
3. **The `Shipping root(s):` line is canonized** as a machine element of the `## Frozen scope`
   section (previously an unstated prose exception — itself a nascent parse surface).
4. Design note: per-bullet strictness makes the section strictly machine-owned — the canon must
   say "prose notes go outside the section" (otherwise new false reds).
5. De-sync fix: `roles/developer.md` asks for `@qg` in the exit report — clarified that the report
   mention is informational; durable evidence is only the checked-in carrier.

## Consequences

**Named residuals (accepted):**

- **The genre's price (unremovable):** the machine never guarantees that the `## Frozen scope`
  section is a complete transcription of the product-level scope document — the architect holds
  transcription, the auditor holds the lens; the vacuous-red forces the section to *exist*, not to
  be *complete*.
- A prose criterion outside a bullet is invisible to the scanner.
- Waiver abuse is visible (listed) but not blocked.
- Index ≠ HEAD: evidence staged but not committed differs from history — mitigated by the clean-tree
  leg of the composite gate.
- Phase 3 is bypassed by "don't touch STATE" (caught by the composite gate) and the agent may
  ignore the injected context (accepted residual of an opt-in phase).
- Solo-collapse without CI remains launch discipline for the composite command (→ strategic
  question below).

**Verification TODOs:**

- [ ] Field-run the hardened `--qg` on the next autonomous run (false-red rate, alarm fatigue) —
      owner: developer of phase 1 + the next run.
- [ ] Verify live hook docs before phase 3 — owner: its implementer.
- [ ] **Allowlist design was the unanimous point of all four passes (red, blue, 2× codex) — flagged
      as a shared-blind-spot candidate**; check against t1–t7 + balatro-clone-2 at implementation
      time; when in doubt, a second model pass or the user.
- [ ] Is the prose rule "scope-ids are unique across slices" sufficient against stale annotations —
      auditor's lens on the first multi-slice project.

**Operational:** a CHANGELOG line + an "update `regimen-doctor.py`/`_pack_lib.py`" step in
`roles/upgrader.md` (version skew: generated projects carry a frozen copy of the doctor).

**Strategic (the operator's call, not engineering):** (i) whether CI becomes mandatory for the
autonomous mode — **answered 2026-07-06 by the operator: no CI integration.** Rationale: the
autonomous pilots are local trees where hosted CI cannot run, so for autonomous mode "CI" reduces
to the orchestrator's duty (phase 2's pipeline.md paragraph) anyway; the composite command is
provider-neutral, and owning per-provider config would be the ADR-001/006/009 debt class. The
solo-without-orchestrator residual (launch discipline) is thereby accepted **permanently**, not as
an open question. (ii) the ceremony budget of the autonomous mode (open item of ADR-015) — still
open.

## Alternatives considered

- **Build nothing** (run 2 showed an orchestrator QA loop suffices): rejected — run 2's gate was
  bespoke to that orchestrator; the regimen itself still ships a checker with proven false-green
  paths that any future orchestrator would trust.
- **The v1 composition** (soft SessionStart/Stop hook + pre-commit recipe + orchestrator duty on
  the *unhardened* checker): refuted — see "In short"; gating on a sieve is fictitious
  accountability.
- **A state machine over day guides / staleness heuristics** (the literal transfer of that external design):
  rejected — no incident, new synchronized parse surfaces over prose, the ADR-001/006/009 class.
