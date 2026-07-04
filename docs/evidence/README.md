# docs/evidence — empirical basis for decisions

This directory holds **verifiable artifacts** that ADRs and `core/` docs cite as load-bearing
truth (live runtime tests, panel arbiter verdicts). They used to live in the gitignored
`scratchpad/panel/` — but only things that are in git and survive a fresh clone can be cited as
authority. Moved here as part of the 2026-06-29 audit (finding #1).

| File | What it is | Who cites it |
|------|---------|---------------|
| [g2-findings.md](g2-findings.md) | Empirical findings from live `codex 0.138.0` (sandbox, G2, KL-7) — basis of the guarantee matrix | [core/portability.md](../../core/portability.md), [overlays/codex/README.md](../../overlays/codex/README.md) |
| [runtime-capability-map.md](runtime-capability-map.md) | Factual map of runtime capabilities (Claude Code / Codex) | ADR-010, [overlays/codex/README.md](../../overlays/codex/README.md) |
| [p4form-arbiter.md](p4form-arbiter.md) | Panel arbiter verdict on overlay form (rationale for the move-later stop-condition) | [overlays/README.md](../../overlays/README.md) |

These are **historical evidence** (a snapshot at time of writing), not a living regimen. Only
whoever reruns the corresponding verification may amend them.
