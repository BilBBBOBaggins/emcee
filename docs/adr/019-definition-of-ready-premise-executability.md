# ADR-019: Definition of Ready — a premise-executability gate on the day plan

**Status:** accepted (2026-07-16)

## In short

The single most repeated failure class in a long autonomous run was not a bad implementation — it was a
**premise defect in the day plan**: the guide asserted that a resource, port, or precedent *exists*
without ever checking it against the actual code, and a whole day cascaded off that false premise. Four
separate lost days traced to the same shape:

- a sanctioned edit perimeter that a closed, exhaustive `match` *outside* the perimeter silently broke;
- a gate that needed a schema column which had **no read-port** on any owner that could consume it;
- a "precedent" cited for a cross-schema foreign key that in fact **contradicted** the written doctrine;
- a parked-fact semantics that **no test carrier** actually covered end to end.

Each premise was plausible on the surface and false against the source. The fix is a **Definition of
Ready (DoR)**: before a task is dispatched, the architect (and the reviewer, when reviewing the guide)
runs four grep-verifiable checks — preconditions exist on disk, every consumer's read-port exists, the
role's mandate and tools cover the task, and every cited precedent is verified against the source rather
than asserted. A task that fails DoR is **not ready to dispatch**; readiness is proven, not assumed.

## Context

The autonomous run drove a mature production project for many day-increments. Implementation quality was
high and the accountability layer held (honest STOPs, red day-closes recorded red). What still burned
whole days was upstream of implementation: the **plan** told an executor to build on something that was
not there. Because the premise read as reasonable, the executor did not stop — it built, hit the missing
port or the broken invariant late, and the day was lost to a cascade that no amount of executor diligence
could have prevented. The defect lived in the guide, not in the hands that followed it.

The common root across all four incidents: a design or guide **asserted the existence of a thing the task
consumes** — an edit perimeter, a column's reader, a precedent, a test carrier — **without checking the
consumer's actual read-port** against the code on disk. "Plausible" is not "executable." A premise is
executable only if the thing it names can be pointed at in the source right now.

This is deliberately **method-level and domain-neutral**: the four examples are from one project's schema
and edit-perimeter work, but the gate is about how any premise is validated before it is handed to an
executor, in any stack.

## Decision

Add a **Definition of Ready** to day-guide production. A task is *ready to dispatch* only when all four
checks pass, each recorded as verified-against-source (a grep hit, a file:line, a command output) rather
than asserted:

1. **Preconditions exist on disk.** Every artifact the task builds on — a file, a module, a migration, a
   fixture, a declared shipping root — is present now, at the path the task names. Not "will be created by
   an earlier task whose completion is unconfirmed"; if it is a dependency, it is either already there or
   the ordering makes its creation a hard predecessor.
2. **The consumer's read-port exists.** For every resource the task assumes will be *read/consumed* by
   some owner (a schema column read by a query, a config key loaded by a component, an event consumed by a
   handler, a symbol imported across a boundary), the **read-port on that consumer is grep-verifiable**. A
   value that is written but has no reader, or a reader that does not exist yet, is a premise defect —
   surface it before dispatch.
3. **Mandate and tools cover the task.** The role assigned to the task can actually perform it with the
   tools it has: a read-only role is not asked to edit; a docs-only role is not asked to write production
   code; a task needing a shell is not handed to a shell-less surface (cf. ADR-018 reachability). If the
   mandate or the toolset does not cover the task, re-assign or re-scope — do not dispatch and hope.
4. **Cited precedents are verified, not asserted.** Any "we already do X here" / "this follows the
   pattern in Y" claim used to justify the task is checked **against the source it cites**. A precedent
   that turns out to contradict the written doctrine (as in the cross-schema FK incident) is worse than no
   precedent — it launders a wrong decision as an established one.

The check is proportional: it is a fast pre-dispatch pass, not a second design phase. Its output is a
one-line-per-item confirmation in the guide (or a flagged failing item), not a report. The architect owns
DoR at guide-production time; the reviewer applies it when reviewing a guide. A task that fails any check
is sent back to decomposition, not to an executor.

## Consequences

- **Cascade prevention moves upstream.** The cheapest place to catch a premise defect is before an
  executor spends a day on it. DoR converts a class of whole-day losses into a few minutes of
  grep-verification at planning time.
- **"Executable" replaces "plausible" as the readiness bar.** A premise is admitted only when the thing
  it names can be pointed at in the source — which is exactly the package's standing "never assume, prove
  it" discipline applied to the *plan* rather than to a claim about behavior.
- **The read-port check is the load-bearing one.** Three of the four incidents were a resource that
  existed on the producer side but had no consumer able to read it. Making the consumer's read-port a
  first-class, grep-verifiable precondition is what turns this from advice into a gate.
- **Small added cost at dispatch.** Guide production gains a short verification pass. On a task with no
  external premises (a self-contained refactor) it is nearly free; its weight scales with how much the
  task assumes about the rest of the system — which is exactly where the risk is.
