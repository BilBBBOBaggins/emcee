# Second model (codex) — a second pair of eyes on high-stakes output

A single model (Claude) is prone to blind spots and plausible hallucinations from one error
distribution. **A second, independent frontier model (codex)** attacks from a different distribution
and catches what one alone misses. Today it's wired into the adversarial panel and spec-driven C+;
this file generalizes it as an **opt-in second pair of eyes for any role** — narrowly, on
high-stakes output.

This reinforces [principles.md](principles.md) → PR-NN-03 (verification pass): on expensive output,
the second pass is done not by the same model, but by an independent one.

## When to call it in (narrow triggers — NOT on every step)

Call codex in when the output = **a consequential judgment with blind-spot risk**, whose cost of
error justifies a second pass:

- **reviewer** — on high-importance findings before the verdict (are they real, was anything
  missed).
- **architect** — on the spec/trade-offs before an ADR (non-trivial/irreversible → that's already
  [adversarial-panel.md](adversarial-panel.md), the full protocol).
- **SA/BA** — on requirements/scenarios where missing a boundary case is costly.
- **debugger** — on the cause hypothesis before an expensive fix (did it guess from just one
  distribution).

**Don't call it** for trivial/clean code, small edits, routine work: developer/devops are already
under reviewer + mechanical gates — a second pass there is redundant (noise + burned quota).

## Honest limitations

- **codex is a code/reasoning model.** As a reviewer of **code and hard contracts** — strong; as a
  reviewer of **design and product requirements** — weaker. On non-code output, flag it "second
  model, weaker on this class" and **measure the payoff** ([spec-driven.md](spec-driven.md) →
  PROCESS-METRICS): doesn't catch a defect class in 2-3 features → narrow the triggers back down to
  reviewer/architect/C+.
- **opt-in, not mandatory.** "codex on every step of every role" was rejected: a dead ritual + an
  operational ceiling — codex runs on the ChatGPT Max quota, and frequent xhigh calls hit the plan's
  rate limit.
- **This does NOT weaken local protocols.** If the adversarial panel, C+, or an audit
  ([../roles/auditor.md](../roles/auditor.md) — where the codex pass on high-stakes findings is
  mandatory, ADR-005) is running — THEIR codex rule applies (recommended/mandatory with an honest
  fallback). second-model is the general opt-in for ordinary roles, not a replacement for or a
  loosening of the panel/C+/audit.

## How to call it

Command (max effort, full project read, web — prompt on stdin):

~~~bash
codex exec -s read-only -c 'sandbox_permissions=["disk-full-read-access"]' \
  -c tools.web_search=true -m <codex-model-id> -c model_reasoning_effort=<max-effort> -
~~~

**The placeholder `<codex-model-id>` — canonical source (this file; every codex command in the
package refers to it, ADR-001).** Substitute the live top codex model, checking
`~/.codex/models_cache.json` before the run; at time of writing the top is `gpt-5.6-sol`.
`<max-effort>` = the highest reasoning effort the model/CLI pair accepts — at time of writing
`ultra` on `gpt-5.6-sol` (requires codex-cli >= 0.144; older models cap at `xhigh`). On a 400
`invalid_enum_value`/`requires a newer version` error: upgrade the CLI or step down ONE effort
tier — and say so in the report, never silently. Don't hardcode the id into commands — only this one footnote gets updated. No codex
/ no second model — the honest fallback: reinforced self-critique from a different angle + a flag
"no second model was available, residual blind-spot risk is higher" (as in the panel), rather than a
silent skip.
