# ADR-016: Second model in the adversarial panel — mandatory when available

Date: 2026-07-03
Status: Accepted

> Provenance: a holistic package audit on 2026-07-03 (finding B1) uncovered a "canon ↔ ADR" drift: [core/adversarial-panel.md](../../core/adversarial-panel.md) required "codex is mandatory, symmetrically," while [ADR-001](001-scope-process-overlay.md) item 3 recorded "recommended, but not mandatory," and `.claude/commands/panel.md` contradicted itself (line 11 "must" ↔ line 19 "recommended"). No ADR had ratified the escalation. Verdict of the audit's codex pass (gpt-5.5 xhigh): the finding is real; ratify "mandatory when available + an honest fallback" — red/blue symmetry is a load-bearing guarantee of the panel, "recommended" leaves a loophole for an asymmetric skip. Accepted by the operator.

## In short

In the adversarial panel, a second independent frontier model (codex) is **mandatory when available, symmetrically for red team and blue team**. If physically unavailable (no CLI/network/quota), the panel is not skipped: an **honest fallback** applies ([core/adversarial-panel.md](../../core/adversarial-panel.md) §Second model — reinforced self-critique + an explicit note that "there was no second model, residual blind-spot risk is higher"). "Recommended" from ADR-001 item 3 is **clarified** by this ADR; ADR-001 itself is not rewritten (immutability), its status header carries a pointer here.

## Decision

1. **The mandate is conditional on availability, not on preference.** Skipping codex while the CLI is live is a violation of the panel protocol; skipping it due to physical unavailability is a legitimate fallback, on the record.
2. **Symmetry is a load-bearing guarantee.** Decorrelation works only when the second model stands both in attack (red) and in defense (blue); an asymmetric hookup skews the verdict.
3. **This does not concern the arbiter**: for the arbiter, codex is only a fact-checker of disputed empirical claims, not a co-judge (unchanged, [core/adversarial-panel.md](../../core/adversarial-panel.md) §"The codex arbiter does NOT issue a verdict").

## Consequences

- Wording synchronized across: `core/adversarial-panel.md`, `.claude/commands/panel.md` (the internal 11↔19 contradiction resolved), `.claude/agents/red-team.md` §Engaging the second model.
- The fallback protocol is neither weakened nor changed.
- The operational ceiling (ChatGPT-Max quota, xhigh rate limit) remains an accepted residual of ADR-001: "mandatory when available" does not require expanding the quota — unavailability due to quota = fallback.
