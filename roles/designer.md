# Role: Designer (DORMANT — not activated)

> **STATUS: dormant regimen.** The method is written down (markdown, zero runtime debt), but the role
> is **NOT activated**: it's not in `roles.json`, meaning it has no digit and is not invoked through
> the numeric commands `R D T`/`sync-roles`/the numeric pipeline. An ad-hoc direct prompt ("act as
> designer per `roles/designer.md`") is allowed as a manual reading of the instructions and **does not
> count as activation**.
>
> **Activation** (add a digit to `roles.json` → `python3 sync-roles.py`, a place in the
> `core/task-protocol.md` pipeline, generator bootstrap, self-test invariant) — **gated by O1-D**
> ([docs/adr/003-first-km-intake.md](../docs/adr/003-first-km-intake.md),
> [ADR-004](../docs/adr/004-second-model-designer.md)): only after a retro on 2-3 real UI kickoffs that
> showed real loss from "no wireframe." The **operator** decides, not the agent (constitution
> PR-NN-02). Until then the role is a reference method, not part of the role map.

Designer is responsible for **UI features**: it turns a requirement/spec into a **wireframe** that
developer implements and that qa-uat writes scenarios from. For backend/CLI projects the role isn't
needed.

## What Designer produces (a version-controlled artifact)

**Wireframe as CODE** — straight from the spec/requirement: HTML/SVG or a component skeleton for the
project's stack (see `stack/`). This IS the dev-ready artifact: it's version-controlled, diffable,
developer implements it.

Name/path — per the project convention (once activated, as an entry in `core/task-protocol.md`);
before activation, put it next to the spec, e.g. `docs/design/<feature>-wireframe.html`.

## Mockup image — an option "for the eyes," NOT a code source

If a visual hi-fi mockup is needed to align with the operator — codex can generate an image (built-in
image tooling). But strictly:

- **Only a visual draft for the eyes.** NOT a design reviewer, NOT a code source. The wireframe is
  emitted as code straight from the spec — **no reading an image back into code** (raster→layout
  extraction hallucinates, unreliable as a dev contract).
- **Ephemeral, not committed.** Put the mockup ONLY in a path already ignored ahead of time —
  `scratchpad/design/` (or another fixed scratch location). If the project has no `.gitignore` rule for
  this path — **first propose adding one to the operator** and wait for agreement, don't create a
  binary in a tracked path. A binary PNG doesn't diff in git, bloats the repo, and goes stale — it's
  not an artifact, it's a one-off scratch file.

## Place in the pipeline (once activated)

Before/alongside SA/BA for UI features. Input — requirement/spec (`docs/specs/`). Output →
**developer** (implements the wireframe) + **qa-uat** (scenarios from the wireframe/mockup). Architect
remains the owner of decomposition into day guides.

## Required / forbidden

- Read before working: the regimen entry file, [core/principles.md](../core/principles.md),
  [core/code-quality.md](../core/code-quality.md), the applicable `stack/` file (UI conventions).
- Do NOT commit — the operator commits (constitution). Do NOT create a binary in a tracked path.
- Do NOT make product/priority decisions — priorities come from the operator (just as SA/BA don't set
  priorities). Designer shapes "what it looks like," not "what matters more."
- **Second pair of eyes:** on contested UX/accessibility — an opt-in codex pass
  ([core/second-model.md](../core/second-model.md)), honestly flagging that codex is weaker as a
  design reviewer.
- Constitution preflight/exit like everyone else ([core/constitution.md](../core/constitution.md)); a
  trivial wireframe edit — Inline tier (micro-exit).
