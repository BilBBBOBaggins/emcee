# examples/ — one end-to-end worked example

This folder shows **what filled-in artifacts** of the package look like, using one small but end-to-end example. It is not copied into a real project — it demonstrates the format that roles and `core/task-protocol.md` reference.

## Example project

**Acme Teams** — a fictional B2B SaaS (team management). Stack: Go API (modular monolith) + Next.js frontend. Day-1 feature — **"Invite a teammate by email"**.

This is the `Go + modular-monolith + b2b-saas` bundle from the package: backend in [stack/go.md](../stack/go.md), frontend in [stack/react-nextjs.md](../stack/react-nextjs.md), composition [architecture/modular-monolith.md](../architecture/modular-monolith.md), domain [domain/b2b-saas.md](../domain/b2b-saas.md).

## What's inside

| File | What it demonstrates | Author in the pipeline |
|------|-------------------|------------------------|
| [CLAUDE.example.md](CLAUDE.example.md) | a filled-in `CLAUDE.md` — all `{{...}}` substituted, one testing variant kept | — (project start) |
| [docs/day-1-guide.example.md](docs/day-1-guide.example.md) | **the key artifact** — a day guide with tasks, a `Prompt for Claude Code` block, `After completion`, `Commit` | architect (breaks down the next slice) |
| [docs/PROJECT-STATE.example.md](docs/PROJECT-STATE.example.md) | the status file the architect reads on entering a day | architect |
| [docs/specs/invite-teammate.example.md](docs/specs/invite-teammate.example.md) | feature spec | SA |
| [docs/adr/001-modular-monolith.example.md](docs/adr/001-modular-monolith.example.md) | architecture decision record | architect |
| [docs/scenarios-1-2-invite-teammate.example.md](docs/scenarios-1-2-invite-teammate.example.md) | user scenarios (input for QA UAT) | BA |
| [docs/test-cases-1-2-invite-teammate.example.md](docs/test-cases-1-2-invite-teammate.example.md) | formal test cases (input for QA E2E) | QA UAT |
| [docs/PROCESS-METRICS.example.md](docs/PROCESS-METRICS.example.md) | **opt-in** log of whether the heavy process pays off (C+/panel/QA) — for checking the STOP gates of ADR-002/003; don't set it up for a simple project | operator |

`<DT>` in file names = "day-task". Here the feature is pinned to Day 1, Task 2 (frontend), so its scenarios and test cases are `…-1-2-…`. Full naming convention — [core/task-protocol.md](../core/task-protocol.md).

## How to use this

1. Read [docs/day-1-guide.example.md](docs/day-1-guide.example.md) — this is the heart of the `R D T` command system. Command `1 1 1` = developer takes Task 1 from this guide.
2. Look at the **scenarios → test-cases** link: how a BA user scenario turns into a formal test case with UI selectors and Given/When/Then.
3. Copy the formats you need into your own `docs/`, renaming `*.example.md` → `*.md` and filling them in for your feature.

The `.example.md` extension is so these files don't get confused with real project artifacts or picked up by tools as real tasks.
