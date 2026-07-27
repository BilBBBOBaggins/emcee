# ADR-022: Obligations governance for autonomous runs — provisional ledger + churn cap (build under conditions)

**Status:** amended (2026-07-27, same day) — **G1 ran and its self-destruct clause fired**: the
ledger is deferred, the lightweight fallback ships as general package rules, and the autonomous
profile is repositioned as a supervised night shift. See "Amendment: G1 verdict" at the end.
Original status: accepted-under-conditions, ratification gated on G1–G4; no core/ edits until
gates are green — this still holds for what remains in scope.

**Panel:** run (full compact panel, 2026-07-27): red → blue → arbiter + narrow red re-check (G5)
+ final codex consistency pass. codex (gpt-5.6-sol / xhigh-ultra) participated symmetrically on red
(session `019fa30a-bd6d`) and blue (session `019fa32f-35ab`) per ADR-016/ADR-018; the arbiter
personally re-verified the decisive git facts. Artifacts: session scratchpad `panel/`
(architecture-v1.md, red-r1.md, blue-r1.md, arbiter-r1.md, red-r2-recheck.md, architecture-v2.md).

## In short

Two independent autonomous field runs (different projects, different stacks, different driver
models) showed the same failure shape: **an unbounded assurance ratchet**. The loop kept adding
evidence obligations and re-adjudicating existing ones; process mass grew (~75% of commits),
product substance starved, integration drifted last. The naive fix — freeze acceptance criteria
at slice entry and forbid additions ("obligations-freeze", v1) — **died under panel attack**:
the process-vs-obligation membrane is not machine-enforceable as prose, the measured pain was
churn over *existing* obligations (which a freeze does not touch), and a freeze installed blindly
can destroy the loop's proven self-correction channel.

What survived is the principle with an inverted mechanism — **the loop verifies the definition of
done, but does not own its growth or its permanence**:

1. The loop **freely adds** evidence obligations mid-slice — but every addition is born
   **provisional** and does not survive slice-close without owner ratification. Irreversibility of
   rigor becomes an owner privilege, not a loop default.
2. A companion **churn-cap** (termination-guard pattern) bounds repeated acceptances /
   re-adjudications of the same obligation — this is the piece that actually addresses the
   measured pain.
3. Everything lives in an **autonomous-mode profile**, not in the core default; interactive
   projects are untouched.

The decision is **accepted under conditions**: four blocking gates (an evidence-audit of the field
histories, a vignette drill proving the membrane is executable, an event matrix for obligation
generators, and shadow-mode before enforcement) must pass before any core/ text lands. One gate
carries a self-destruct clause: if the history replay shows the mechanism would have blocked <50%
of the measured cost, the ledger is not built at all and only the churn-cap + an early
assembled-integration checkpoint ship.

## Context

- **GDS-2 autonomous run** (Claude-driven Workflow loop, ~70 in-regimen "days"): final audit named
  the characteristic failure mode "assurance-ratchet + integration-last" — ~75% of commits were
  process/documentation; one money-slot acceptance took 6 review rounds; a single HTTP slice took
  8 days and 3 acceptance passes (an acceptance → annulment → re-acceptance spiral); the anomaly
  count grew 14→22 in one week, each anomaly spawning a new standing mitigation.
- **Telerok run** (codex-driven, independent): the Day-0 gate self-inflated into a near
  production-grade evidence gateway; the driver itself concluded "the criterion became too heavy;
  I will stop expanding the evidence contour" — but only under live owner attention.
- **Counter-evidence the panel weighed:** the same self-extension machinery is how the GDS-2 loop
  *caught its own over-declare* (anomaly №21: a verdict line recorded against the loop's own
  mandatory second-model conclusion was annulled at next-day entry). Governance must not kill that.
- **Industry practice** (Superpowers, Devin-class agents, loop-engineering mainstream): every
  surviving system makes the definition of done external and immutable to the agent. emcee
  deliberately grants more process freedom; this ADR imports only the *permanence* asymmetry.

## Decision (binding composition — v2)

Authoritative text: `architecture-v2.md` (panel artifact; to be transcribed into the
autonomous-profile file when gates pass). Mandatory components — none may be dropped:

1. **Scope: autonomous-mode profile** (gating pattern per ADR-005/O1-D), bound to a **slice** with
   an immutable slice-ID. Obligation baseline = package default (QG-NN-01..05 + the finite
   conditional generators of ADR-020/021/QG-root) + justified deltas at slice entry.
2. **Class membrane "normative novelty"**: evidence mapping onto an already-authorized predicate
   (O-ID) is an instance — free; evidence requiring a **new** predicate is an obligation —
   provisional / owner sanction. A close refusal must cite its O-ID. Disposition taxonomy for
   anomalies/errata — four classes: `violates O-ID` / `proposes new O` / `restructures O-ID` /
   `correction`.
3. **Provisional-obligations ledger** (replaces the rejected counted budget N): additions are
   free but provisional; they do not survive slice-close without owner ratification; expiry is an
   explicit ledger event, never a silent drop. **Class-dependent expiry**: defect-derived
   provisionals (a concrete attached finding/repro) park at slice-close instead of expiring;
   ritual/process ones expire. Precedence: the class rule outranks queue expiry. Batch
   ratification is a distinct `ratified-without-itemized-review` telemetry event; batch size,
   review time and ratify-all share feed shadow-mode stop-metrics; telemetry is also keyed by
   evidence-pack × close-attempt (bundling-bypass detector).
4. **Companion churn-cap** (termination-guard pattern): N repeated acceptances/adjudications of
   one O-ID → escalation / parking / redecomposition. Never auto-waiver, never forced-green.
   Anti-bypass: counters inherit across O-ID lineage (parent-O-ID); `restructures O-ID` is
   provisional/sanctioned and not self-serve in ownerless mode.
5. **Ownerless default — three-tier semantics**: (a) violating an existing O-ID blocks that
   branch's close; (b) proposing a new O does not block — it queues and (unless defect-derived,
   which parks) expires unratified; (c) a pre-enumerated emergency invariant class parks the
   affected branch fail-closed while independent branches continue per the declared dependency
   graph. Full STOP only when every branch is blocked — the honest autonomy boundary. STOP-cascade
   and bare lease as defaults are rejected.
6. **Correction rule**: a git-provable restoration of a transcription omission (canonical-source
   hash in the entry form) is a correction, not a new obligation; a post-close finding → reopen,
   never a silent fix. **Re-entry contour (first-class)**: an expired obligation is "come back
   with evidence", not a verdict — a field incident/finding in an expired obligation's zone
   re-enters the ledger as defect-derived with the attached repro, keeping lineage to the expired
   record (churn-cap counters inherit). The **expiry-regret** metric — the share of expired
   obligations that later re-entered via incident — is a shadow-mode stop-metric: regret ≈ 0
   means the filter drops ritual weight; high regret means it cuts live protection and the class
   threshold is re-tuned by the owner on data, not on intuition.
7. **Panel outputs in autonomy are provisional by default** — never silently binding. A
   provisional guarding an already-applied change carries an explicit `condition ← action` ledger
   pointer and never expires silently: escalation, parking of the change, or reopen only.
8. **Shadow-mode before enforcement**; the governance layer is subject to itself (its own
   cost/yield telemetry line and sunset conditions; its overhead is a shadow-mode stop-metric).
   If counterfactual close is enabled: divergence is log-only, never blocks, never spawns an
   adjudication; the divergence aggregate is owner-review input, not a gate.

Optional (owner's call after shadow-mode data): counterfactual close (arbiter strongly
recommends), supersession default, lease + defect-yield, capability separation / reference
monitor (deferred — most expensive; only if shadow-mode shows membrane self-discipline failing).

**Rejected (do not revive without a new panel):** counted rigor budget N; extensional named
obligation registry at entry; package-level freeze forms on every day of every project; the claim
"freeze cures the re-acceptance spiral" (churn-cap does; the ledger governs the stock);
"churn-cap without a ledger" as the default choice (it is the G1 stop-condition fallback only).

## Ratification gates (blocking, in order; owners assigned)

- **G1 — permission-replay** of GDS-2 days 60–70 (incl. anomaly additions 14→22) + a chronology
  split of Telerok G0 (inflation before vs after gate fixation). Read-only history audit;
  runs are never modified. **Stop-condition: <50% of measured cost blocked by
  ledger+churn-cap → the ledger is not built; fallback = churn-cap + early assembled-integration
  checkpoint.**
- **G2 — provenance audit** of the two F-3 mandates (mandatory codex point; partial-acceptance
  ban) — same audit pass as G1. Outcome "added by the loop mid-run" → those classes enter the
  package baseline explicitly.
- **G3 — vignette drill**: 15 adversarial vignettes covering panel binding-outputs,
  regression-test-after-bug, wording errata, event-driven root-update, the `restructures O-ID`
  class and class-dependent expiry; + a label-swap rerun + the task "add 5 blocking checks without
  a new O-ID". Stop: inconsistent classification → the membrane is not executable → no
  ratification.
- **G4 — event matrix** for the obligation generators (ADR-020/021/QG-root/panel): every event
  must yield a single non-contradictory precedence result. Stop: an unresolvable conflict → no
  ratification.
- *(G5 — the narrow red re-check — already ran during the panel; its four MAJOR findings are
  folded into the composition above as R1–R4.)*

After core/ text, before enforcement: **P5** shadow-mode across 2–3 slices (stop-metrics: high
false-block, off-book churn, provisional batch size / `ratified-without-itemized-review` share,
governance overhead, expiry-regret — owner thresholds); **P6** ratchet-scan of interactive
histories — gates only scope expansion beyond the autonomous profile.

## Consequences

- **No core/ edits until G1–G4 are green.** The panel artifacts are the specification of record
  until transcription.
- Honest cost estimate (blue, accepted by arbiter): ~2–4 weeks of engineering + anomaly/errata
  disposition taxonomy + precedence matrix + shadow-mode instrumentation. The v1 claim "moderate
  cost, no mechanics touched" was retracted as false.
- The v1 "obligations-freeze" is recorded here as the rejected precursor (alternatives
  considered): 3 of its 4 load-bearing clauses fell; only the asymmetry principle survives.
- Named empirical unknowns (T1–T8, arbiter §10) carry into the gate work as TODOs with owners:
  T1 blocked-cost share (G1), T2 Telerok chronology (G1), T3 F-3 mandate provenance (G2),
  T4 membrane executability (G3), T5 generator precedence (G4), T6 ledger/cap holes (closed by
  G5 → R1–R4), T7 field false-block rate (P5), T8 interactive-project ratchet (P6).
- Field root, for the record: this is the package-level answer to the boundary found by the
  autonomous experiment — the loop lacks discharge authority (the right to judge "enough") and
  therefore defaults to maximal rigor; v2 gives the owner a cheap, structured discharge channel
  (ratify/expire/park) instead of either freezing the loop's hands or trusting it to self-limit.

## Amendment (2026-07-27): G1 verdict — the self-destruct clause fired

**In short.** The G1 permission-replay ran the same day on both field histories, and the two
halves split: on GDS-2 the ledger+cap combination would have blocked only **2.5–7%** of the
measured wasted cost (an order of magnitude under the 50% threshold), while on Telerok
**75–85%** of the gate inflation was exactly ledger-shaped. Per the clause as written, the
verdict is taken on the primary dataset: **the provisional ledger is not built now.** The cheap
fallback ships instead — as general package rules, not autonomous-only machinery — and the
autonomous profile itself is repositioned: not "autonomous development" but a **supervised
night shift** (bounded unattended stretches between human checkpoints).

**G1 findings of record.**

- *GDS-2 replay* (96 commits, days 60–70; report `g1-replay-gds2.md`, session scratchpad):
  process = 72/96 commits — exactly the 75% the cont22 audit claimed, independently recomputed.
  But the window is a single never-closed slice, so the ledger's main lever (expiry at
  slice-close) never fires; ~55% of process mass is the package's own day-cycle (baseline),
  ~28% is panels/codex points mandated by **owner directives** mid-run, and nearly every churn
  node yielded a real defect (Р-7, GC3-15, R-12→N-1) — repeated acceptances were productive.
  Two false-block counterexamples against v2 as designed: a churn-cap at N=2 would have parked
  the main branch mid-money-fix, and the self-serve redecomposition ban would have forbidden
  the (sensible) C3→C3a/C3b split.
- *Telerok chronology* (report `g1-telerok-chronology.md`): the G0 criteria list is
  **byte-identical** from kickoff to HEAD (18 days) — all inflation happened one level down, in
  "what counts as evidence": protected graph 36→155 paths, a 25-methodology evidence gateway
  born of an in-run panel, verifier code ~7× the verified code. ~75–85% of the final weight is
  post-fixation — ledger-shaped. Confound honestly noted: the run's spec was one line ("make it
  like Ragnarok"), rich in features, silent on assurance — a thin spec invites the loop to
  substitute proof-mass for the missing definition of done. Source note: the phrase "the Day-0
  criterion became too heavy" exists only in a codex chat message relayed by the owner, not in
  Telerok's committed canon.
- *G2 provenance*: the mandatory-codex-point class was added mid-run **by the owner**
  (directives of 07-14/07-15) — clean; the partial-acceptance ban was added mid-run **by the
  loop** (review 65-3, day 65) → per the soft stop-condition this class must enter the
  autonomous-profile baseline explicitly.

**What ships now (general package rules, dual-use in manual mode; still under G3/G4-style
text-acceptance before core/ merge).**

1. **Churn-cap counting barren rounds.** The counter is mechanical, not self-assessed: a round
   is non-empty iff it produced a finding with a **new id** (lineage-inherited — a renamed
   finding is not new) plus an attached remediation commit or red test, checkable by
   `regimen-doctor.py`/the orchestrator from git artifacts; prose-only fallback recorded in the
   portability map for hook-less harnesses. N consecutive barren rounds on one obligation →
   stop and surface to the owner. Productive review chains (each round yielding a real defect —
   the GDS-2 pattern) are never capped.
2. **Early assembled-integration checkpoint, subordinate to forks.** "Integrate what is
   ratified as early as possible", never "integrate everything now": load-bearing forks are
   still resolved by their own order (panel → verdict → ADR → wire-STOPs); once a contract is
   ratified, a thin assembled path through the real shipping root lands promptly instead of
   deferring integration for many slices. In overlay mode (the product is already end-to-end)
   this degenerates to: wire new work into the existing skeleton continuously — QG-NN-05
   applied continuously rather than once at close.
3. **Definition-of-done sign-off at entry for thin specs.** When the spec is thin, the loop
   presents "here is what I will treat as done" — one page, owner-signed — at kickoff/slice
   entry, instead of inventing acceptance criteria mid-run (the Telerok failure shape). This is
   the decision-surfacing channel the panel kept, not the rejected freeze registry.
4. The partial-acceptance-ban class enters the autonomous-profile baseline explicitly (G2).

**Deferred: the provisional-obligations ledger.** Not killed — shelved with two named re-entry
conditions: (a) a future run with a **properly specified** brief still inflates its evidence
contour Telerok-style ≥50% under replay (removes the thin-spec confound), or (b) the owner
decides to delegate value judgments over "enough" to the loop at long horizons — the boundary
this experiment found is one of authority, not intelligence, so the harness (or at minimum the
human checkpoint) outlives model-capability growth; the ledger becomes worth building when the
delegation decision is made, whichever model generation that happens under.

**Repositioning of record.** emcee's center of gravity is the manual/interactive mode — it is
field-proven. The autonomous profile is a supervised night shift: the loop produced real,
correct, adversarially-verified substance (55/55 independent re-verification on clean DBs), but
it is a poor product owner — throughput and judgment, not correctness, are where it fails
without a human. Heavy autonomous-only machinery is not built against that grain; cheap rules
that also serve manual mode are.
