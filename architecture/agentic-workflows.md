# Agentic Workflows — architecture pattern

Patterns for systems where AI agents perform multi-step tasks with tool use, memory, orchestration.

Applicable when: AI isn't just chat, but an actor that does things (reads files, calls APIs, makes decisions, iterates). For simple chat/completion use cases — see [ai-heavy.md](ai-heavy.md).

## Single agent vs multi-agent

### Single agent

One LLM with access to tools. The agent gets a task, plans, uses tools in a loop, returns a result.

~~~
User Request
    ↓
Agent (LLM with tools)
    ↓ loop:
    ├─ Reason
    ├─ Use tool(s)
    ├─ Observe result
    └─ Continue or finish
    ↓
Response
~~~

Suitable for:

- Tasks that fit within one context window
- Linear workflows
- When role specialization isn't needed

Problems:

- The context window is limited
- The agent "gets lost" in long tasks
- One prompt must cover every possible situation

### Multi-agent

Several specialized agents with different roles, coordinated through an orchestrator or a communication protocol.

~~~
User Request
    ↓
Orchestrator
    ├→ Agent 1 (specialist A)
    ├→ Agent 2 (specialist B)
    └→ Agent N
    ↓
Synthesized Response
~~~

Suitable for:

- Complex tasks requiring different types of expertise
- Workflows where explicit roles improve quality
- Parallelizable subtasks

Problems:

- Coordination is harder
- More tokens (each agent has its own system prompt)
- Communication between agents requires a clear protocol

This package's scheme is multi-agent (architect / developer / reviewer / QA / BA). Principle: each agent has a clearly defined role with a minimal scope, an orchestrator (the user or a meta-agent) switches between them as needed.

## Roles in multi-agent systems

### By function

- **Orchestrator** — breaks down the task, delegates to subagents, aggregates results
- **Specialists** — perform specific types of work (code, research, review, testing)
- **Critics** — evaluate specialists' work, find problems
- **Memory agents** — manage long-term memory, retrieval

### Each role has

- A system prompt describing responsibilities, constraints, output format
- Tools it has access to (not all agents have access to all tools)
- A context scope — what it reads, what it doesn't read
- Success criteria — when the task is done

## Orchestration patterns

### Linear workflow

Agent A → Agent B → Agent C. Sequential, each works on the previous one's output.

Use case: a defined process (research → analysis → writeup).

Simple to implement, predictable behavior. Not flexible to the unexpected.

### Router pattern

The orchestrator classifies the incoming request and routes it to the appropriate agent:

~~~
Request → Classifier → Route to:
                        ├─ Technical question → CodeAgent
                        ├─ Creative writing → WritingAgent
                        └─ Research → ResearchAgent
~~~

Use case: general assistants with different types of tasks.

### Hierarchical (tree)

A manager agent breaks down the task, delegates subtasks, each subagent can delegate further:

~~~
Manager
├── Researcher
│   ├── Web search agent
│   └── Document reader agent
└── Writer
    ├── Outline agent
    └── Draft agent
~~~

Use case: complex research, multi-stage planning.

Each level has its own context scope — it doesn't clutter the upper level with the lower level's details.

### Debate / Multi-perspective

Several agents discuss one problem from different angles, reach a consensus:

~~~
Problem
    ↓
┌─── Agent A (perspective 1) ───┐
├─── Agent B (perspective 2) ───┤
└─── Agent C (critic) ──────────┘
    ↓
Synthesis
~~~

Use case: complex decisions where checking from different angles matters, reducing single-agent bias.

### Supervisor pattern

One agent does the work, a supervisor checks it and approves/rejects:

~~~
Worker agent → Output → Supervisor agent → Approve/Reject
                                           ↓ (reject)
                                        Worker retries
~~~

Use case: when quality is critical, a double check is needed.

This package's scheme is the supervisor pattern: developer → reviewer.

## Memory in agentic workflows

### Short-term memory

Conversation history in the context window. Managed directly by the LLM.

Limits — the context window size. Long workflows exceed the limit.

### Long-term memory

Data that persists across sessions and is retrieved by relevance.

Architecture:

- **Storage** — vector DB (Pinecone, Qdrant, pgvector) + possibly key-value for structured data
- **Retrieval** — semantic search + metadata filtering
- **Update** — the agent or orchestrator decides what to save to memory

Pattern:

1. At the start of a task — retrieve relevant memories for the query
2. At the end of a task — save results that might be useful later
3. Periodically — consolidate memories (merge duplicates, remove outdated ones)

### Scratchpad

Temporary memory within a single task:

- Intermediate results
- The task plan (tree of subtasks)
- Uncertainty tracking (what's known, what's unknown)

Implemented as a file on disk or state in memory that the agent reads between iterations.

## Tool use

### Tool definitions

Each tool has:

- **Name** — a unique identifier
- **Description** — what it does, when to use it
- **Parameters** — a typed schema (JSON Schema)
- **Return value** — what it returns and in what format

The description is critical — it's what the LLM reads to decide whether to use the tool.

~~~json
{
  "name": "search_codebase",
  "description": "Search the codebase for files matching a pattern. Use when you need to find code related to a specific feature, class, or function.",
  "parameters": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "Search query. Can be regex or plain text."
      },
      "file_type": {
        "type": "string",
        "description": "Optional file extension filter (e.g., 'py', 'go')"
      }
    },
    "required": ["query"]
  }
}
~~~

### Tool granularity

Too-specific tools — there are many of them, the agent gets confused. Too generic — the agent doesn't know when to use them.

Rule: a tool covers an atomic operation at a level a human can understand.

- ✅ `read_file(path)` — atomic, clear
- ✅ `search_codebase(query)` — atomic, clear
- ❌ `refactor_class(class_name)` — too high-level, unpredictable
- ❌ `str_operation(string, op_type)` — too generic

### Tool permissions

Agents have different tool scopes:

- Research agent — read-only tools (search, read)
- Developer agent — write tools (edit files, run code)
- Debugger agent — read + observation tools (logs, traces)

Principle of least privilege — an agent has only the tools it needs.

### Error handling

Tool calls can fail:

- Network errors
- Invalid parameters
- Resource not found
- Permission denied

Errors are returned to the agent in a structured format. The agent decides — retry, escalate, or report back to the user.

## Plan execution

### Chain of thought

The agent explicitly thinks before acting:

~~~
Thought: I need to find the authentication logic. I'll search the codebase.
Action: search_codebase(query="authentication")
Observation: Found 3 files: auth/handler.go, auth/service.go, auth/middleware.go
Thought: The handler is entry point. Let me read it first.
Action: read_file(path="auth/handler.go")
...
~~~

Improves reasoning quality, makes the process debuggable.

### Plan-then-execute

The agent first forms a plan for the whole task, then executes:

~~~
Plan:
1. Search codebase for current implementation
2. Analyze dependencies
3. Make required changes
4. Run tests
5. Report results

Execution:
Step 1: ...
Step 2: ...
~~~

Suitable for predictable workflows. Less flexible than chain of thought but more structured.

### ReAct (Reasoning + Acting)

A combination — the agent interleaves reasoning and actions, without explicit pre-planning:

~~~
Thought → Action → Observation → Thought → Action → ...
~~~

The most flexible, works well for a wide class of tasks.

## Context management

### Context window constraints

LLMs have a context window limit (often 200K+ tokens for modern models, but there's still a limit).

Problem: long agentic sessions accumulate context, hit the limit.

Solutions:

**Summarization** — periodically summarize the past part of the conversation into a short version, replace it with the original.

**Sliding window** — keep only the last N turns.

**External memory** — move details to long-term memory, keep only pointers in context.

**Hierarchical** — subtasks are executed by subagents with a separate context, they return a summary to the parent.

### Context hygiene

From [core/principles.md](../core/principles.md): the principle of minimal context.

Specific to agents:

- The agent reads only the files specified in the task or explicitly required
- It doesn't explore the codebase "just in case"
- After a subtask — it returns a summary, not the full context

## Debugging multi-agent systems

Harder than debugging a single LLM call. Principles:

### Tracing

Every action (LLM call, tool use, agent transition) is logged with:

- Timestamp
- Agent ID
- Input
- Output
- Duration
- Cost

OpenTelemetry or specialized observability (LangSmith, Langfuse, Helicone).

### Replay-ability

The ability to replay sessions with the same inputs for debugging:

- Deterministic execution requires temperature=0, but that's not always applicable
- Record-replay frameworks for reproducibility
- Snapshot state at key points

### Agent output inspection

The chain of thought must be visible and saved. When there's a problem — read the agent's reasoning to understand where it went wrong.

## Quality control

### Eval suite for agents

Different from evaluating simple completions:

- Input — not a single query, but a full task description
- Output — the agent's final answer + optionally a trace of actions
- Evaluation — may require checking side effects (files created, actions performed)
- Rubric — often multi-dimensional (correctness, efficiency, safety)

### Golden traces

Saved examples of successful agent sessions. Used for:

- Testing (regression detection)
- Training (fine-tuning on successful patterns)
- Documentation (showing what the agent can do)

### Guard rails

Protection against unsafe or suboptimal behavior:

- **Action filters** — forbidding certain actions (file deletion outside scope, external API calls with sensitive data)
- **Budget limits** — maximum steps, maximum tokens, maximum cost per session
- **Human-in-the-loop** — approval required for critical actions

## Specific to the Claude Code workflow

If a project uses Claude Code as the main agentic engine:

### CLAUDE.md as agent configuration

CLAUDE.md — a persistent system prompt for all sessions in the project. Contains:

- Project context
- Architectural rules
- Code conventions
- Role definitions
- Quality gates

Every session starts by reading this file.

### Task definitions via guides

Structured tasks in `docs/day-N-guide.md` files:

- Explicit prompts for the agent
- Expected output
- Acceptance criteria
- Verification commands

The agent receives a task via a short command, reads the guide, executes it.

### Role switching via short commands

Short commands (numbers) switch the active role:

- The same Claude Code instance becomes developer / reviewer / QA depending on the command
- Each role — a separate role description file
- The user decides when which role is needed

This approach is simple and works. The alternative — full multi-agent orchestration via separate processes — is complexity that may not pay off for solo/small-team projects.
