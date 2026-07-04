# p4form-arbiter — Verdict on whether to move `.claude/` → overlays/claude-code/

## 1. Verdict (outcome)

**C+mapping. Do NOT move now.** `.claude/` stays the canonical claude-code overlay in its native
position; `overlays/` is created ONLY for non-default runtimes (`overlays/codex/`); the docs record
the equivalence "`.claude/` ≡ overlays/claude-code/ in the position the runtime requires." Zero
churn, zero symlink risk, zero self-host breakage.

Decisive factor in one sentence: **the source↔target asymmetry (A6) cannot be removed by moving
anything, by construction of the generator (the target is always `target/.claude/`), so "moving"
doesn't buy SYSTEM consistency — only cosmetic package layout; while C+mapping delivers the same
mental-model value via a single doc paragraph at zero churn/symlink cost → C+mapping strictly
dominates move-now.** This isn't "don't move out of laziness" — it's strict dominance on
effort↔value.

Scope boundary: the C+mapping verdict applies **to the repository's current state** (no
`overlays/`, `overlays/codex/` not being built, G1 not green). At the moment P4 ACTUALLY builds
`overlays/codex/` and `sync-roles.py` becomes an N-runtime emitter, the question reopens as
move-later (see "Open"). move-now is rejected unconditionally; move-later is deferred, not
rejected.

Why not move-now: its entire motivation (T1 consistency) is defeated by A6 — fatally and with no
workaround (both sides agree). What's left is cosmetic layout, paid for with 16-file churn + a
symlink precondition + a window of self-host blindness. An inversion of effort↔value.

Why not move-later RIGHT NOW: its only benefit over C+mapping (the KL-5 parity social-enforcer
against a second overlay rotting) activates ONLY once a second overlay exists. There is no second
overlay. Tying P4's form to move-later before `overlays/codex/` materializes is a premature
commitment; but as a conditional plan for the moment it's built, it's valid and preferable to a
separate step.

---

## 2. Table of verdicts K1–K6

| # | Dispute | Who's right | Class | Residual after blue's mitigation | Confidence |
|---|------|----------|-------|------------------------------|-------------|
| K1 | A6/T1/T4: consistency is illusory — the target is always `target/.claude/` | **red** | **fatal** (for T1 as stated) | Blue's mitigation isn't a fix, it's abandoning T1 → reframing as T1' (layout symmetry). T1 in the form "system consistency" is dead beyond recovery. Residual: the entire stated motivation for the move is zeroed out; only cosmetic layout remains. | [fact] |
| K2 | Self-host breakage during `git mv` without an alias | **red** (the defect is real) | **serious** (operationally acute) | Blue's mitigation (atomic commit of move+symlink+sweep, ordering of operations) is cheap and valid — BUT it only cures the defect where K3 is green (the symlink materializes). On the Windows fallback, the blindness becomes permanent. Residual: conditional on K3. And the whole defect exists only if you move — under C+mapping it's zero. | [fact] |
| K3 | A1/T2: symlink fragility on Windows (core.symlinks=false → plain file) | **red on the fact, blue on the severity** | **serious, conditional** | Red's fact is correct (the git fallback is stable, years-old behavior; Claude Code's contract for reading through a symlink isn't published). But the severity hinges on the unverified premise "the package is cloned outside macOS." Blue's mitigation (documenting the precondition / a dev-setup script) is valid and cheap, but T2 "no surprises" is honestly downgraded — it's an honor-condition on every non-Mac machine. Residual: non-zero until the "macOS only" invariant is confirmed by the owner. | [fact]+[data needed] |
| K4 | A5/option B: a copy = a second SSOT (single source of truth) | **red** | **fatal for B / not a defect for the decision** | B institutionalizes drift (ADR-001/006) — dead, no workaround. But this is a hit on just one of the three self-host options, and blue discards it too. Mitigation = discard B, cost zero. Residual: zero (B explicitly excluded); the objection moves to K3 (symlink). | [fact] |
| K5 | A2/A4: YAGNI — `overlays/` doesn't exist, symmetry-of-one | **red** | **serious** (strategy/timing, not technical) | Blue honestly does NOT parry it with a trick, hands it off to strategy. A4 "(C) is not strictly better" is **false in the current state**: C is strictly cheaper for an equal outcome. This is the load-bearing verdict of the whole dispute. Residual: the move's benefit is real, but activates only once `overlays/codex/` exists → wrong timing, not "not needed." | [fact]+[assumption about value] |
| K6 | A3: churn is wider than claimed (16 files, source/target split) | **red** | **minor→serious** (the understatement is real) | "Limited" is an understatement: 16 files + a dangerous split between the source package (we change it) and the target project (we do NOT change it). Blue's mitigation (spike-classify the 16 sites + a green selftest, ~0.5–1 day) is valid, but honestly admits the risk of silently breaking target paths if the selftest doesn't cover both contexts. Residual: a one-time cost + unverified selftest coverage. All churn = zero under C+mapping. | [fact] |

### Key judgment (the question asked)

**Does A6 kill the consistency argument beyond aesthetics? — YES.** By construction
(`new-project.py:469`, hardcoded target `os.path.join(target, ".claude")`), the generator drops
into `target/.claude/` regardless of the source's position. This is a [fact], personally verified
by both sides. Hence the source↔target asymmetry cannot be removed by moving anything — it's
inherent to any generator. "System consistency" (T1) is not achieved after the move: only PACKAGE
LAYOUT symmetry is achieved. That is aesthetics + a weak social-enforcer, not a load-bearing
benefit. Blue admitted this honestly and discarded T1.

**Does C+mapping deliver the same mental-model value without the churn/symlink cost? — YES, and
it strictly dominates move-now.** A single mental model is achieved via one doc paragraph
("`.claude/` is the claude-code overlay in the native position the runtime requires;
`overlays/<h>/` are runtime overlays whose native position is not the repo root"). This closes the
one hole in bare C (visual asymmetry → cognitive load) at the cost of one paragraph. At the same
time: zero churn (K6), zero symlink fragility (K3 fully lifted), zero self-host breakage (K2 fully
lifted). The one thing C+mapping does NOT buy is the KL-5 parity social-enforcer (a visibly parallel
tree against `overlays/codex/` rotting) — but that benefit is zero anyway as long as there's no
second overlay. → In the current state, C+mapping strictly dominates both move-now and move-later.

---

## 3. Settled (not revisited)

- **In red's favor:** T1 "source↔target system consistency is worth more than the cost" — **false,
  fatal, no workaround**. A6 is a structural fact, probability 1.0. Blue agrees. [fact] Closed.
- **In red's favor:** option B (dev-script copy) — **a second SSOT, dead** (ADR-001/006). Both
  sides agree. Explicitly excluded. [fact] Closed.
- **In red's favor:** "move now as a separate cosmetic step" — **premature**: the benefit
  activates only once `overlays/codex/` exists, and it doesn't. A4 is false in the current state —
  C is strictly cheaper. Blue deferred to strategy and did not contest it on the merits. Closed as
  a verdict on form.
- **In red's favor (with blue's caveat on the count):** churn = 16 files with a dangerous
  source/target split; "limited" is an understatement. Closed as fact; relevant only if you move.
- **Panel consensus:** if the move happens at all — it's ONLY via symlink (option A), ONLY
  bundled with `overlays/codex/` in P4, ONLY as an atomic commit. move-now is dead. Neither side
  contests this.

---

## 4. Open (empirical unknowns → discovery)

| Question | What fact/experiment closes it | Who obtains it | Impact |
|--------|-----------------------------------|--------------|---------|
| Is the package ever cloned outside the operator's macOS (CI, a Windows contributor)? | Direct answer from the owner / a git-remote-clone inventory | **owner** (ground truth) | Decides whether the K3 Windows-fallback debt is real or near-zero. Does NOT block C+mapping (no symlink is needed there at all), but is mandatory BEFORE any future move-later. |
| When is `overlays/codex/` ACTUALLY built (G1 green, ADR-010 out of Proposed)? | G1-gate status (6-week log per MEMORY G1) + the moment `sync-roles.py` becomes an N-emitter | **owner** | This is the trigger for reopening move-later. Until it's met, the move is not on the table. |
| Does `selftest.py` cover BOTH contexts (.claude as source package AND as target project) at once? | Read the selftest, check whether it catches a silent target-path breakage during a source-side sweep | engineer (during the spike) | Relevant only for a future move-later (K6 residual). Not needed for C+mapping. |

None of the open items block the C+mapping decision — all three pertain to the hypothetical
future move-later. C+mapping is executable immediately and unconditionally.

---

## 5. Assessment of the sides

**Red — strong:** a rare case of a flawless attack. K1 (A6) is a static structural fact, not a
"risk"; it killed the load-bearing thesis cleanly. The steelman was built honestly and itself
bounds the verdict ("justified INSIDE overlays/codex/, not as a separate step"). codex's
contribution (the git core.symlinks fallback, the render-handbook churn site) is verifiable and
integrated, not dumped in as authority. The kill list is sorted correctly by decision-changing
weight.

**Red — weak:** (minor penalty) K1 "it was ONE place, became THREE" — a miscount: the
source↔target asymmetry ALREADY exists (source in the package + target in the project = two
places). Blue caught this precisely. Doesn't change the verdict (T1 is dead regardless), but it's
an inaccuracy in the accusation. (conceptual penalty) red at points conflates two different
verdicts — "C is strictly cheaper" (= don't move) and "justified in P4 as a bundled step" (=
move-later). These are DIFFERENT outcomes; red didn't separate them explicitly. Arbiter separates
them: in the current state — C+mapping; at the moment `overlays/codex/` is built — reopen
move-later.

**Blue — strong:** exemplary honesty. Built no straw man, personally re-verified EVERY numeric and
structural fact from red (16 files, mode 120000, new-project.py:469) and confirmed them. Admitted 2
fatal hits (T1, B) without resistance. KEY move: did NOT parry K5 (YAGNI) with an engineering
trick, but honestly deferred it to strategy per the method's hard rule. And itself proposed
C+mapping as "possibly strictly better" — this isn't sycophancy, it's a quality arbitration
contribution from the defense side.

**Blue — weak:** (light penalty) the defense of T1' (layout symmetry as "a weak parity
social-enforcer") is a mitigation on the edge of unjustified: a social-enforcer against rot requires
(a) a second overlay to exist and (b) a contributor other than the solo operator who "sees" that
parity. On solo-macOS both conditions are absent → T1' buys zero RIGHT NOW. Blue admitted this
itself at the A6 fork ("activates only once `overlays/codex/` exists"), so the penalty is minimal —
but T1' cannot be counted as a live benefit in the current state. Arbiter: T1' = a deferred benefit,
not a current one.

Bottom line on policing: no fabrications, no unfalsifiable "threat" without a scenario, no
mitigation without a named cost. The panel operated cleanly. The one owner-dependent unresolved
quantity (Windows clone) was honestly flagged by both sides as [data needed].

---

## 6. Actions by priority (P4)

1. **Lock in the C+mapping layout (immediately, before any churn).** `.claude/` stays in its
   native position as the canonical claude-code overlay. `overlays/` is NOT created for
   claude-code. **Stop-condition:** if anyone proposes `git mv .claude` in the current state —
   reject it (K1+K5).

2. **Add a documented mapping (one paragraph).** In `core/portability.md` (or a new short ADR
   with an "In short" section): "`.claude/` is the claude-code overlay in the native position the
   Claude Code runtime requires (it scans `.claude/` at the root); `overlays/<harness>/` are
   runtime overlays whose native position is NOT the root (e.g. `overlays/codex/`). Equivalence:
   `.claude/` ≡ the conceptual `overlays/claude-code/`." This closes the one hole in bare C. Cost:
   one paragraph.

3. **The `--harness` generator: special-case claude, not a symmetric loop.** `new-project.py`
   for claude copies `PACK/.claude → target/.claude` (as now, line 469 untouched). For non-default
   runtimes — `PACK/overlays/<h> → target/<h's native position>`. No symlink is needed at all —
   the package's self-host works natively through the existing `.claude/`. **This zeroes out
   K2/K3/K4/K6.**

4. **Do NOT add a symlink.** Under the C+mapping layout it's not required for self-host or for
   the generator. The entire A1/T2/Windows-fallback branch becomes moot.

5. **Record the move-later reopening trigger (do NOT act on it now).** In that ADR — a line:
   "The physical move `.claude/ → overlays/claude-code/` reopens ONLY when (a) `overlays/codex/`
   is actually being built, (b) `sync-roles.py` becomes an N-runtime emitter, (c) the cloning
   invariant is confirmed (macOS only → symlink is fine; otherwise, a documented
   `core.symlinks` fallback). Until all three are met — do not move." **move-later stop-condition:**
   if the "cloned outside macOS" discovery comes back positive AND there's no ready dev-setup
   fallback — do not move even in P4, stay on C+mapping permanently.

6. **(conditional, only for a future move-later)** Run a spike: classify the 16 sites as source
   vs. target, confirm `selftest.py` (149 checks) covers both contexts. Not needed now.

---

## 7. Is a round 2 needed

**NO. The panel converged — this is a fixed point, not mutual exhaustion.** Blue admitted both
fatal hits (T1, B), did not parry K5 with a trick, and itself proposed C+mapping as the dominant
candidate — meaning the defense converged with the prosecution on a single outcome. Red, in its
steelman and codex verdict, already ruled "don't move now, option C." Blue's counter-questions to
red (section 6 in p4form-blue) are rhetorical clarifications, not live disagreements: the arbiter
answered all five above (the "one→three" count is red's inaccuracy, doesn't change the verdict;
the Windows clone is [data needed], not a C+mapping blocker; C+mapping > bare C — yes; "don't move
now" ≠ "don't move in P4" — explicitly separated; the source/target split is manageable, relevant
only for move-later).

The residual disagreements reduce to two explicitly-named empirical unknowns (the Windows
clone; the moment `overlays/codex/` is built), both handed off to the owner as discovery, both NOT
blocking the immediately executable C+mapping. This is the acceptable "log it as a TODO, don't
paper over it." A second round wouldn't resolve anything new — it would be arguing about the
hypothetical move-later, which isn't on the table until all three preconditions are met.
