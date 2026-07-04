# Anthropic prompt library → what applies to emcee

**Source:** <https://code.claude.com/docs/en/prompt-library> (pulled 2026-07-03).
**Status: accepted and incorporated 2026-07-03** — §1 (prompt checklist → architect.md) and all items
of §2 (coverage → stack stub + go/python/react-nextjs + qa-e2e/developer; UI self-check →
developer.md; git archaeology → auditor.md; session capture → core/memory.md). Operator's decision.
These are 52 copy-paste prompts for Claude Code that Anthropic collected from Common workflows, Best
practices, "How Anthropic teams use Claude Code," and the enterprise guide. Each prompt comes with a
"Why this works" breakdown. The audience is a user who types prompts by hand; emcee is a regimen that
already institutionalizes most of these patterns through roles and gates. So the value worth
extracting is not the prompts themselves but **the patterns behind their design** and a handful of
specific techniques.

---

## 1. The main asset: six prompt meta-patterns

The "What makes these prompts work" section is a compendium of what makes a prompt effective.
Verbatim:

1. **Describe the outcome, not the steps** ("add rate limiting to the public API and make sure
   existing tests still pass") — the model finds the files itself.
2. **Give a way to self-check within the same prompt** ("write the migration, run it against the
   dev database, and confirm the schema matches") — the agent iterates on its own instead of
   stopping after the first attempt.
3. **Point to an example** ("add a settings page that follows the same layout as the profile page")
   — without a reference the model falls back on "general best practices"; with a reference, on the
   project's conventions.
4. **Name a measurable target** ("get the bundle size under 200KB and show me what you removed") —
   an unambiguous definition of done.
5. **Give the artifact, not a summary** ("why is the build failing? @build.log") — the model reads
   the primary source, not your description of the primary source.
6. **Say what form the answer should take** (format, length, audience).

**Where this goes in emcee:** the architect is the package's only "prompt author" (the "Prompt for
Claude Code" block in day guides). Right now, in [roles/architect.md](../../roles/architect.md)
§"Breaking down the next slice," the only prompt-quality rule is "concrete and unambiguous."
Proposal: add a checklist of patterns 2–6 there (self-check within the same prompt; a reference to
an existing example in the codebase; a measurable target; artifact instead of a summary; the
expected output format).

A caveat on pattern 1: it's meant for an interactive user. In emcee, the prompt for the developer is
**deliberately** precise (the developer doesn't make architectural decisions) — "outcome, not steps"
applies at the level of the contract (the "what"), not as a way to blur the spec.

---

## 2. Specific techniques not in the package

| Library prompt | Gist | Where in emcee |
|---|---|---|
| **fill-gaps-from-a-coverage-report** | "read coverage-summary.json and add tests for the lowest-covered files until each is above N%" — test targets from the actual coverage report, not a gut feeling | a technique for qa-e2e/developer; optionally mention in [core/quality-gates.md](../../core/quality-gates.md) as a way to find gaps (not as a metric-as-an-end-in-itself) |
| **implement-from-a-screenshot** | "implement this design, then take a screenshot, compare to the original, and fix differences" — a visual self-check loop | [roles/developer.md](../../roles/developer.md): a verification loop at the **implementation** stage of the UI (in emcee the designer only produces a wireframe; the developer implements the actual interface); the image is a comparison reference, not a source of code; the rendering means is `origin: harness` |
| **trace-how-code-evolved** | "look through the commit history of {path} and summarize how it evolved and why" — git archaeology for the "why" question, not the "what" | an explicit technique in [roles/auditor.md](../../roles/auditor.md) (entering an unfamiliar/old project); partly already covered by "git = searchable cold memory" in task-protocol |
| **capture-what-to-remember** | "summarize what we did this session and suggest what to add to CLAUDE.md" — manual knowledge capture at the end of a session | [core/memory.md](../../core/memory.md): as a manual complement to the PreCompact hook (the hook writes a recovery checkpoint, but not the substantive "what to add to the regimen") |
| **see-what-depends-on** | "what would break if I deleted {target}?" — a blast-radius assessment before deletion | a micro-technique for developer/architect on refactor tasks; a candidate for the architect breakdown checklist |

---

## 3. Already covered by the regimen (correspondence map)

Confirmation of the design: the library independently converges on the same patterns already built
into emcee — in most cases emcee is stricter.

| Library prompt | emcee equivalent | Who is stricter |
|---|---|---|
| draft-a-spec-by-interview ("interview me… then write SPEC.md") | sa.md §Discovery (Socratic Q&A) + ADR-013 divergence/convergence | emcee: one question at a time, phases for the shape of the question |
| map-edge-cases-before | sa.md §Edge cases, ba.md (edge-case scenarios), qa-uat.md | parity |
| drive-implementation-from-tests | core/spec-driven.md (the C+ cycle) | emcee: an independent test author + an adversarial review pass |
| review-your-changes ("reads changed files in full, not just diff") | reviewer.md: "read every affected file in full" + an authoritative diff from the dispatcher | emcee |
| run-a-security-review (a subagent in its own context) | hardware-scoped reviewer, the security block of the review | emcee |
| fix-a-build-error (root cause + verify) | core/debugging.md (no guessing allowed) + debugger.md (minimal fix + regression test) | emcee |
| investigate-a-production-incident ("correlate evidence sources, not steps") | core/debugging.md: simultaneous log collection from every layer of the chain | parity |
| optimize-against-a-measurable | quality-gates philosophy: measurable done | parity |
| work-an-issue-end-to-end ("give the number, not a summary") | task-protocol "Entering a session": the role reads the guide itself, not a summary | parity |
| follow-an-existing-pattern | developer.md: "use existing patterns from the codebase" | parity (but worth adding explicitly to the architect checklist — §1) |
| turn-a-correction-into-a-rule (a correction → a rule in CLAUDE.md) | CLAUDE.md §"Evolution of this document" | parity |
| turn-a-recurring-task-into-a-skill | core/skills.md (the quality bar for "when to create one") | emcee: has When-NOT anti-triggers |
| commit-with-a-generated-message | task-protocol §Commit commands | emcee: the agent doesn't commit; the format comes from the guide |
| plan-a-multi-file ("plan, don't edit yet") | separation of roles: the architect doesn't write code | emcee: institutionalized at the tool level (no Edit) |
| scope-a-change-before ("which files to touch") | day guide: "Task T — what and where (files touched)" | parity |
| get-oriented / ask-the-codebase | architect entering day N (reads the whole project, status) | parity |
| course-correct / narrow-the-scope (steer) | task-protocol §Protocol for ambiguity + exit reports | different mechanics: emcee prevents it, the library fixes it after the fact |

## 4. Not applicable to the package

One-off user-facing prompts outside the development regimen: meeting→tickets, marketing variations
from an ads CSV, analyzing a data file, diagnosing from a cloud console screenshot, querying logs
via MCP (Model Context Protocol), updating copy across the codebase, "build an internal tool in
vanilla JavaScript," connecting MCP servers. Release notes from git history and CI workflows are
covered by the devops role ad hoc — no separate rule is needed.

---

## 5. Full catalog (52 prompts, condensed)

Format: **title** — the prompt (the gist of "why it works"). `{x}` — placeholder slots.

### Discover
- **Get oriented in a new repository** — "give me an overview of this codebase: architecture, key directories, and how the pieces connect" (describe what you want to learn, not which files to read).
- **Explain unfamiliar code** — "explain what {path} does and how data flows through it. write it up as {format}" (name the file and the answer's format).
- **Find where something happens** — "where do we {behavior}?" (search by behavior, not by file name).
- **Check what breaks before you delete** — "what would break if I deleted {target}?" (blast radius before deletion).
- **Trace how code evolved** — "look through the commit history of {path} and summarize how it evolved and why" (history — for the "why" question).
- **Scope a change before you start** — "which files would I need to touch to {change}?" (sizing before the roadmap).
- **Ask the codebase a product question** — "I am a {role}. walk me through what happens when a user {action}" (name the role — the answer comes at the right level).

### Design
- **Plan a multi-file change** — "plan how to refactor {target} to {goal}. list the files you would change, but don't edit anything yet" ("don't edit yet" separates reconnaissance from edits).
- **Draft a spec by interview** — "I want to build {feature}. interview me about implementation, UX, edge cases, and tradeoffs until we have covered everything, then write the spec to SPEC.md" (the model interviews you, not the other way around).
- **Turn a meeting into tickets** — "read {notes} and write up the action items, then create a {tracker} ticket for each with acceptance criteria".
- **Map edge cases before building** — "list the error states, empty states, and edge cases for {feature} that the design needs to cover" (ask about what's missing, not what already exists).
- **Turn a mockup into a working prototype** — "here is a mockup. build a working prototype I can click through, matching the layout and states shown".
- **Implement from a screenshot and self-check** — "implement this design, then take a screenshot of the result, compare it to the original, and fix any differences" (a verification loop with no human in the loop).

### Build
- **Follow an existing pattern** — "look at how {example} is implemented to understand the pattern, then build {new} the same way" (a reference beats general best practices).
- **Generate docs for undocumented code** — "find {scope} without {format} comments and add them, matching the style already used in the file".
- **Add a small, well-defined feature** — "add a {endpoint} endpoint that returns {payload}" (inputs/outputs, not "how to build it").
- **Build a small internal tool** — "create a {tool} using HTML, CSS, and vanilla JavaScript, then open it in my browser".
- **Work an issue end to end** — "read issue #{issue}, implement the fix, and run the tests" (the ticket number, not a summary).
- **Find and update copy across the codebase** — "find every place we say '{copy}' or a close variant… update to '{new}'. leave tests and the changelog alone" (ask for variants and name the exceptions).
- **Draft a document from past examples** — "read the {examples} in {folder} to learn the structure and voice, then draft a new one for {topic}".
- **Write tests, run them, fix failures** — "write tests for {path}, run them, and fix any failures" (write+run+fix in one prompt = the agent iterates on its own).
- **Drive implementation from tests** — "write tests for {feature} first, then implement it until they pass".
- **Fill gaps from a coverage report** — "read {report} and add tests for the lowest-covered files until each is above {target}%" (targets from actual numbers).
- **Migrate a pattern across the codebase** — "migrate everything from {from} to {to}: identify every place that needs to change, then make the changes" (list first — for verifiability).
- **Port code to another language** — "port {source} to {target}, keeping the same {keep}" (name what to preserve — that's the verification contract).
- **Optimize against a measurable target** — "optimize {target} to bring {metric} from {current} down to under {goal}".
- **Fix a precise visual bug** — "the {element} extends {amount} beyond the {container} on {viewport}. fix it." (a precise input → a precise fix).
- **Review your changes before commit** — "review my uncommitted changes and flag anything that looks risky before I commit" (reads files in full, not just the diff).
- **Review a pull request** — "review PR #{pr} and summarize what changed, then list any concerns" (a review with the whole codebase in context).
- **Review infrastructure changes** — "here is my Terraform plan output. what is this going to do, and is anything here going to cause problems?".
- **Run a security review with a subagent** — "use a subagent to review {path} for security issues and report what it finds" (an audit in a separate context).
- **Catch issues before formal review** — "review {file} for {concerns} and list anything I should fix before it goes to {reviewer}" (name checkable risks).
- **Course-correct a wrong approach** — "that is not right: {feedback}. try a different approach" (name the constraint that was violated, not just "wrong").
- **Narrow the scope of a change** — "that is too much. keep only the changes to {scope} and undo your other edits" (a boundary instead of a full rollback).
- **Turn a correction into a rule** — "you keep {mistake}. add a rule to CLAUDE.md so this stops happening".

### Ship
- **Resolve merge conflicts** — "resolve the merge conflicts in this branch and explain what you kept from each side" (asking for a rationale = a reviewable merge).
- **Commit with a generated message** — "commit these changes with a message that summarizes what I did".
- **Open a pull request from a ticket** — "find the {tracker} ticket about {topic} and open a PR that implements it".
- **Draft release notes from git history** — "compare {v1} to {v2} and draft release notes grouped by feature, fix, and breaking change".
- **Write a CI workflow** — "write a GitHub Actions workflow that {steps} on every push to {branch}".

### Operate
- **Find and fix a failing test** — "the {test} test is failing, find out why and fix it" (a symptom, not a diagnosis).
- **Investigate a reported error** — "users are seeing {symptom} on {where}. investigate and tell me what is going on".
- **Fix a build error at the root** — "here is a build error. fix the root cause and verify the build succeeds" (root cause + verify, against surface-level patches).
- **Investigate a production incident** — "{symptom}. check the logs, recent deploys, and config changes, then tell me the most likely cause" (list the sources of evidence, not the steps).
- **Diagnose from a console screenshot** — "here is a screenshot of {console}. walk me through why {resource} is failing and give me the exact commands to fix it".
- **Query logs in plain English** — "show me all {events} for {scope} over {timeframe}. write the query, run it, and tell me what stands out" (shows both the query and the result).
- **Analyze a data file** — "read {file}, summarize the key patterns, and write the results to {output}".
- **Generate variations from performance data** — "read {file}, find the underperforming {items}, and generate {n} new variations that stay under {limit} characters".
- **Turn a recurring task into a skill** — "create a /{name} skill for this project that {steps}".
- **Add a hook for repeat behavior** — "write a hook that {action} after every {event}".
- **Connect a tool with MCP** — "set up the {server} MCP server so you can read my {data} directly".
- **Capture what to remember for next time** — "summarize what we did this session and suggest what to add to CLAUDE.md" (ask before you forget — the model knows what it had to figure out).
