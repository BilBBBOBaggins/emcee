# G2 — docs-only on Codex: empirical result (live binary codex 0.138.0)

> Test conducted by the P4 agent on `codex-cli 0.138.0` (`/opt/homebrew/bin/codex`), macOS
> seatbelt (`sandbox-exec`). Method: `codex sandbox -- <command>` runs an arbitrary command under
> the same OS sandbox as the agent. This tests the **hardware boundary below the tool layer** —
> `apply_patch`, raw shell, and MCP writes all reduce to the same write syscalls, which seatbelt
> either allows or blocks. So a raw-write test under the profile covers all three "attack vectors"
> at once.

## What's proven (hardware facts)

| Tier | Codex config | Result | Class |
|---|---|---|---|
| **read-only** (reviewer, auditor) | `sandbox_mode = "read-only"` | Write to `src/` AND `docs/` → `Operation not permitted`. Blocked by seatbelt. Reproduced multiple times. | **GREEN — hardware** |
| **full** (developer, qa-e2e, debugger, devops, architect-code) | `sandbox_mode = "workspace-write"` | Documented stable path; makes the workspace writable in a real agent session. | **GREEN — hardware** (stable, documented config) |
| **docs-only** (ba, qa-uat, sa, arbiter, red/blue — write only to `docs/`/`scratchpad/`, not `src/`) | stable path is structurally incapable; per-path only via the unstable `[permissions]` enum | **CONFIRMED by a live agent:** the "write `docs/`, deny `src/`" carve-out is unreachable with a practical config (see below). | **RED (stable path) — degrades to prose+accountability** |

## Why docs-only = AMBER, not GREEN/RED

1. **The machinery is present** (not RED — the capability is not absent). Reverse-engineered
   from the binary's schema:
   - Stable path: `sandbox_mode = "workspace-write"` + `[sandbox_workspace_write]` with
     `writable_roots = [...]`, `exclude_tmpdir_env_var`, `exclude_slash_tmp`.
   - Unstable path (gated behind "unstable features"): the `[permissions.<profile>]` system,
     `default_permissions = "<profile>"` (top-level), `--permissions-profile <name>`. Profile
     structure (`PermissionProfileToml`): fields `deny_read`, `description`, `extends`, `workspace_roots`
     (a `WorkspaceRootsToml` struct), `filesystem` (`FilesystemPermissionsToml`), `network`. The
     filesystem filter is `FileSystemSandboxEntry { access, glob/path, permission_profile }`,
     `glob_scan_max_depth`, `entries`. Could not pin down the exact TOML incantation for the
     untagged enum `FilesystemPermissionToml` within a reasonable timebox (the schema is
     undocumented and marked unstable).
2. **The stable path (`workspace-write` + `writable_roots`) is STRUCTURALLY INCAPABLE — confirmed
   by a live agent.** Decisive test (`codex exec -s workspace-write`, `writable_roots=["<proj>/docs"]`,
   the agent was tasked to write to `docs/ok.md` AND `src/bad.go`): **both writes succeeded**
   (ground-truth files on disk confirm `src/bad.go` was written). Structural cause (cross-checked
   against the binary's `SandboxWorkspaceWrite.ts`): the fields are `writable_roots`,
   `network_access`, `exclude_tmpdir_env_var`, `exclude_slash_tmp` — **there is no option to
   exclude cwd**. `writable_roots` **adds to** the default writable set (cwd), it does not
   restrict it. cwd is always writable → `src/` under cwd is always writable.
3. **`workspace_roots` (a profile field) is boolean toggles, not a list of paths** (`expected a
   boolean` on `["docs"]`; fields like `git`/`local`/`enabled`). Does not give "writable = docs only".
4. **The only per-path mechanism is the unstable `[permissions].filesystem` untagged enum**
   (`FilesystemPermissionToml`: `entries`/`glob`/`deny_read`). Marked "unstable features"; could not
   pin down the exact TOML incantation after ~15 attempts across two sessions. Building the
   docs-only tier on it would be fragile (the schema changes between codex versions; 0.138→0.142+
   has already shipped) — not engineering-justified.

**Conclusion (definitive):** hardware docs-only on Codex 0.138.0 **is unreachable with a
practical config** — the stable path is structurally incapable (cwd is always writable, proven by
a live agent), `workspace_roots` is toggles, per-path only via the unstable enum. This is **RED for
the stable path**, stronger than the previous AMBER. **Consequence for the matrix:** docs-only
roles = `sandbox_mode="workspace-write"` + a **prose constraint "write only to
`docs/`/`scratchpad/`"** (accountability), because `read-only` would break their ability to produce
artifacts. The cell degrades to prose — closed, not a TODO.

## KL-7 — Codex hook activation: VERIFIED on live `codex exec` (6 sessions)

**Verdict: not a single hook fired in headless `codex exec` (0.138.0).** This is not "untested" —
it's "tested exhaustively, does not activate from user/repo config in exec mode".

**What's firmly established:**
- The `CodexHooks` feature is on by default (visible in the session log `features=[…,CodexHooks,…]`).
- Events (enum, PascalCase in config): `PreToolUse`, `PermissionRequest`, `PostToolUse`, `PreCompact`,
  `PostCompact`, `SessionStart`, `UserPromptSubmit`, `Stop`, `SubagentStart`, `SubagentStop`.
- **The canonical format is a Claude-Code-compatible `hooks.json`** (from real plugin hooks at
  `~/.codex/.tmp/plugins/*/hooks.json`): `{"hooks":{"PostToolUse":[{"matcher":"Bash","hooks":[{"type":
  "command","command":"./scripts/x.sh"}]}],"Stop":[…]}}`. Event keys are **PascalCase**, `command` is
  a **path string** (not an array), `matcher` is the tool name.
- **Two activation gates:** (1) the feature is enabled; (2) **persisted trust** — an interactive TUI
  prompt ("These hooks run outside the sandbox after you trust them. [Trust all and continue] /
  [Continue without]"); for automation, the `--dangerously-bypass-hook-trust` flag.
- **Silent validation failure:** `[hooks]` in `config.toml` accepts arbitrary event names and types
  WITHOUT an error (checked via `codex sandbox`). A hook misconfiguration gives no feedback.

**What did NOT fire (exhaustively):** the hook did not run in `codex exec` with — the correct
canonical schema (PascalCase `Stop` + a path string to a real `.sh`), `--dangerously-bypass-hook-trust`
(the "hooks may run without review" warning confirmed active), several events (`Stop`, `PostToolUse`,
`session_start`, `user_prompt_submit`), different sandbox modes, completed sessions (tool calls
executed, the agent stopped). The marker file never appeared, not once.

**Interpretation:** working hooks in 0.138.0 exist as **plugin hooks** (`hooks.json` via a plugin
manifest — a separate, heavyweight loading path), and the trust prompt is a **TUI affordance**. The
"user/repo `[hooks]` in `config.toml` → exec" path is either unsupported, or requires an
interactive TUI session to grant trust. In the **interactive `codex` TUI**, hooks probably do fire
(after granting trust) — but that's unavailable to a headless agent/CI without interaction.

**Consequence for the regimen:** on Claude Code, hook gates (`settings.json`) fire in ALL modes
(including headless). On Codex 0.138.0, regimen hook gates from config **do NOT activate** in
headless mode → the "hooks" matrix cell **degrades to accountability** (an obligation on record),
and for hard enforcement on Codex, **CI/pre-commit** are preferred over runtime hooks. This is
stronger than the previous "KL-7-pending": confirmed empirically, not deferred.

Doc caveat (still holds): `PreToolUse` is not a complete enforcement boundary → docs-only via a
PreToolUse hook would be a false guarantee (ADR-010 already rejected this in favor of a
permission-profile).

## Verification status (all closed by a live session)

- [x] **docs-only hardware feasibility** — CLOSED (RED, live `codex exec`): the stable path is
      structurally incapable (cwd is always writable, the agent wrote to `src/`),
      `workspace_roots` = toggles, per-path only via the unstable `[permissions]` enum. The cell =
      prose+accountability. Not a TODO.
- [x] **KL-7** — CLOSED (live `codex exec`, 6 sessions): hooks from config do not fire in
      headless mode. The hooks cell = accountability; hard gating on Codex → CI/pre-commit.
- [ ] **(low priority, not a blocker)** The exact shape of the `[permissions].filesystem`
      profile — should hardware docs-only/secret-deny ever be needed; unstable schema, wait for
      codex to stabilize/document it. Not engineering-justified right now (fragile across
      versions).

---

**Bottom line for G2+KL-7:** both live verifications are closed. The guarantee matrix
([core/portability.md](../../core/portability.md)) is now fully grounded in 0.138.0 empirics, with
no "pending" cells left. Hardware-backed on Codex: read-only, full-write, skills, auto-read of the
entry file. Prose/accountability: docs-only, scratchpad-only, no-Bash, slash-dispatch, hooks. This
is a deliberate degradation (ADR-010/011), not a defect.
