# Adversarial Panel — Reviewing Architectural Decisions Before Commit

A method for checking a non-trivial architectural/strategic decision **before** engineering months are
invested in it. Not "a review that improves," but an adversarial process of three roles that looks for
**where the decision breaks**, honestly defends it, and renders a binding verdict. The result is a
reworked architecture (v2) + an ADR.

This ships out of the box in every project (`core/` is always copied). **The method does not depend on
subagents.** On Claude Code the roles are implemented as subagents in `.claude/agents/` (`red-team`,
`blue-team`, `arbiter`), invoked via `/panel`; on other runtimes — a prose run through this file
(`origin: harness:claude-code` — only the wiring/invocation, not the method itself).

## When to Run It

Before a **non-trivial** decision where the cost of error is months of work or irreversibility:

- Load-bearing architecture (module/service boundaries, direction of authority, consistency model, storage choice).
- Build-vs-buy, choice of technology/platform that the entire project will then stand on.
- A strategic bet (where value flows, what the moat is) — technique without checking the frame is useless.
- Any decision that's expensive to roll back or that faces outward (an external contract, regulation, security).

**Do not** run it for: trivial implementation choices, things that are easy to revert, code style. For
those — the regular architect ([../roles/architect.md](../roles/architect.md)).

This is the concrete mechanism for decisions that [../roles/architect.md](../roles/architect.md) flags
as "option A vs B vs C" and for which an ADR is written.

## The Method's Load-Bearing Structure

Three roles + an independent second model (codex). Each role is a separate subagent with its own system
prompt; they **do not edit** each other, each writes its own document.

1. **Red team** ([red-team subagent](../.claude/agents/red-team.md)) — presumes the decision has fatal
   flaws. Attacks the **strongest** version of the intent through every lens (correctness, security/regime,
   legal, operations, economics, strategy, execution, effort↔value inversion). **Must engage codex** as an
   independent second model and folds its strongest hits into its own analysis. Produces a kill list.
2. **Blue team** ([blue-team subagent](../.claude/agents/blue-team.md)) — maximizes the decision's
   survival **honestly**. Classifies every red claim (hit / miss / straw man / fabrication), gives a
   mitigation **with a cost and residual risk** for every real hit — or concedes it's fatal. **Must engage
   codex** with the same second model: looks for mitigations that red+codex missed, and **rechecks red's
   codex findings** (catches the accuser's hallucinations). Assembles the reworked version.
3. **Arbiter** ([arbiter subagent](../.claude/agents/arbiter.md)) — **judges, doesn't smooth things
   over**. For every disputed point: rules whose position is stronger, the defect class
   (fatal/serious/minor/not-a-defect), and the remainder after blue's mitigation. "Both are right" is a
   forbidden outcome (except for an honest "not resolvable on this evidence," naming the deciding fact).
   Engages codex **only as a fact-checker of disputed empirical claims** (a number / "shipped product or
   preprint" / a currently-in-force regulation), **not as a co-judge** — the verdict on "whose argument is
   stronger" is not delegated. Calibrates against rhetorical bias **symmetrically**: a confident attack ≠
   a hit without evidence, an unproven claim doesn't count from **either** side, and before the verdict it
   reconstructs the strongest version of **both** positions. Synthesizes the overall verdict and
   actionable next steps.

## Second Model (codex): Symmetric on Red and Blue, Fact-Check at the Verdict

One model (Claude) is prone to blind spots and plausible hallucinations. A second independent frontier
model (codex) attacks from a different error distribution. Its value is **decorrelation**, and it only
works when codex stands **opposite** Claude, not on the same side.

**codex is mandatory when available, symmetrically for red and blue** (the panel's default mode;
physically unavailable → the honest fallback below, not a skip — ratified by
[ADR-016](../docs/adr/016-panel-second-model-mandatory-when-available.md)):

- **red + codex** — an independent attack (red integrates codex's strongest hits);
- **blue + codex** — an independent defense: mitigations that red+codex didn't find, **and rechecking
  red's codex findings** (red might have smuggled in a hallucination from its own second model — blue
  catches it with its own).

Symmetry removes the skew where "the accuser has a frontier ally and the defense doesn't," which is why
red used to win systematically.

**The arbiter's codex does NOT hand down the verdict.** If red relied on codex, and the arbiter's own
codex judges the dispute, the judge is anchored to the same model that shaped the attack: decorrelation
collapses, and the skew toward red **intensifies**. That's why the arbiter calls codex **only for an
independent fact-check of a disputed empirical point** (a number, "shipped product or arXiv preprint,"
the currently-in-force edition of a regulation) — not for a verdict on "whose argument is stronger." Once
codex has worked for both red and blue, its fact-check is honestly neutral for the arbiter.

**Calibrating the arbiter against rhetorical bias** (the second reason for red's advantage, besides
firepower): an LLM reads confident criticism as rigor and honest defense as sycophancy, and the judge
overweights the accuser's force. This is corrected **not by a counter-bias favoring blue, but by a single
standard for both sides**: an unproven/unsourced claim doesn't count, no matter who makes it; before the
verdict, the strongest version of **both** positions is reconstructed; the burden of proof is on whoever
is asserting [a fact]. The standard is symmetric; that red more often ends up under it is a consequence
of red more often introducing new claims, not a rule against red.

**If codex (or any second frontier model) is unavailable** — don't skip the panel, switch to the honest
fallback mode: (1) red and blue attack/defend as usual; (2) in a **separate pass**, each side tries to
refute its own conclusions (a reinforced self-critique from a different angle); (3) the output explicitly
flags "no second model was used — this is a gap in the review, the residual risk of blind spots is
higher." The fallback is weaker than the two-model mode — but better than a silently skipped check. (If
you have your own second-model protocol configured globally — follow it.)

The invocation command (max effort, full project read, web-enabled) — **canonically in
[second-model.md](second-model.md) §How to call it**: the single source for the command block and the live
`<codex-model-id>` footnote, not duplicated here (single-source — ADR-001, ADR-014 #4). Panel-specific
detail: `tools.web_search=true` is **mandatory** for red/blue (regulation/norms/numbers).

codex is used in the panel:
- **inside red-team** — an independent attack (red must request it and integrate the strongest finding);
- **inside blue-team** — an independent defense + rechecking red's codex findings;
- **with the arbiter** — a narrow fact-check of disputed empirical claims (not a verdict);
- **at the finale** — a review pass of the synthesized v2 for **internal contradictions** (where one
  statement in the spec conflicts with another).

Cost, honestly: codex is the slow part of the run. Symmetry adds passes (red + blue are heavy, the
arbiter is a narrow targeted fact-check, can skip xhigh). Under the north star "quality over token
economy" this is justified; keep the arbiter's fact-check narrow, not a full xhigh run.

## Run Process

The panel works in `scratchpad/panel/` — round artifacts don't clutter the repository before the final
ADR. All `panel/...`-style paths below are relative to this directory (i.e. `scratchpad/panel/...`); the
orchestrator passes the subagents the full path so that red/blue/arbiter write to the same directory.

0. **Fix v1.** Write the decision under review into `panel/architecture-v1.md`: load-bearing theses (each
   a separate checkable claim), context, constraints. If the decision isn't yet written down — write it
   out first; you can't attack what hasn't been formulated. Extract a **numbered list of load-bearing
   assumptions** — these are the attack targets.
1. **Red team r1.** Run the `red-team` subagent on `architecture-v1.md` + the assumption list. It
   engages codex internally and delivers `panel/red-r1.md` (verdict + kill list + assumptions↔cheap
   check + survival preconditions + steel man + pre-commit questions).
2. **Blue team r1.** Run the `blue-team` subagent on `architecture-v1.md` + `red-r1.md`. It **does not
   wait** for red and doesn't edit it — it reads what's presented, engages codex internally (an
   independent defense + rechecking red's codex findings), and delivers `panel/blue-r1.md` (claim
   classification + mitigations with cost + a reworked version + acknowledged fatal flaws).
3. **Arbiter r1.** Run the `arbiter` subagent on all three documents. On a disputed **empirical** point,
   it calls codex for a narrow fact-check (not a verdict). Delivers `panel/arbiter-r1.md`: the verdict
   (build / build with conditions / rework / don't build), a table of rulings, resolved/open items,
   prioritized actions, and — if needed — which points to send back for a second round.
4. **Second round (if the arbiter calls for it).** For the disputed points that remain open, repeat
   red↔blue in a targeted way (not the whole scope — only the named points), then arbiter r2.
5. **Synthesize v2.** Assemble `panel/architecture-v2.md` from the arbiter's verdict: what changes, what
   new preconditions apply, what's been carved out of scope, what remains an open question with a
   discovery owner.
6. **Final codex review pass.** Run v2 through codex for **internal contradictions** (one statement in
   the spec against another). Fix whatever is found.
7. **ADR.** Record the decision as an ADR in `docs/adr/` (format —
   [../roles/architect.md](../roles/architect.md) → "ADR process"): Context, Decision (= v2),
   Consequences, Alternatives considered. In Consequences — the open questions and survival preconditions
   from the arbiter's verdict, as explicit risks/TODOs with an owner.

Show the user every round (red's verdict, blue's defense, the arbiter's ruling) — they're the ground
truth and can kill a bad premise before the panel goes deep into it ([principles.md](principles.md):
visibility of work).

## Consensus Is a Fixed Point, Not Mutual Exhaustion

The panel is finished when either: (a) another round produces no new **decision-changing** objection
(the position survived the attack — as-is or revised), or (b) the remaining disagreement reduces to
explicitly named **empirical unknowns** ("true IF fact X holds; X is unverified") — these are logged as
discovery TODOs, not swept aside.

**Not consensus:** a side capitulating without addressing its strongest argument (sycophancy — LLMs cave
under pressure, the arbiter penalizes this); both sides running out of steam; agreement resting on an
unflagged assumption.

**Unanimity is not automatically confirmation.** If red, blue, and codex all converge on a non-obvious
load-bearing point, that can be a **shared blind spot** of a single model distribution, not the truth
(the same reason the panel needs a second model). The arbiter flags such unanimity as a candidate for
verification (by a second model / the user), rather than closing it as a settled question. Disagreement
is caught by the CRUX; here it's the reverse trap — false agreement.

**Termination guard:** a cap of ~4-5 rounds. If still diverging — stop, present the user with the live
disagreement + the **CRUX** (the one fact/value that resolves it). Honest non-agreement beats fake
agreement.

## Anti-patterns

- Running the panel on a trivial decision — a waste of time; this is a tool for expensive/irreversible forks.
- Feeding red-team a straw man — the attack must target the strongest version of the intent, otherwise the review is useless (the arbiter penalizes this).
- Accepting a blue mitigation with no cost and no residual risk — that's a slogan, not a defense.
- Silently skipping the second model — loses the protection against a single model's blind spots. No codex → the honest fallback mode (self-critique + a flag noting the gap), not a silent skip.
- Not writing out v1 before the attack — you can't attack what isn't formalized; you'll end up arguing about different understandings.
- Papering over a strategic defect with an engineering trick — if the frame is weak, flawless implementation won't save it.
