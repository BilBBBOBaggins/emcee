# Agentic Workflows — архитектурный паттерн

Паттерны для систем где AI-агенты выполняют многошаговые задачи с tool use, memory, оркестрацией.

Применимо когда: AI — не просто chat, а actor который делает вещи (читает файлы, вызывает API, принимает решения, итерирует). Для простых chat/completion use cases — см. [ai-heavy.md](ai-heavy.md).

## Single agent vs multi-agent

### Single agent

Один LLM с доступом к tools. Agent получает задачу, планирует, использует tools в цикле, возвращает результат.

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

Подходит для:

- Задач которые укладываются в один context window
- Линейных workflows
- Когда специализация по ролям не нужна

Проблемы:

- Context window ограничен
- Agent "теряется" в длинных задачах
- Один промпт должен покрывать все возможные ситуации

### Multi-agent

Несколько специализированных агентов с разными ролями, координируются через orchestrator или через communication protocol.

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

Подходит для:

- Сложных задач требующих разных типов expertise
- Workflows где явные роли повышают качество
- Параллелизируемых подзадач

Проблемы:

- Координация сложнее
- Больше tokens (каждый agent имеет свой system prompt)
- Коммуникация между agents требует чёткого протокола

Схема этого пакета — multi-agent (architect / developer / reviewer / QA / BA). Принцип: каждый agent имеет чётко определённую role с минимальным scope, orchestrator (пользователь или meta-agent) переключает между ними по мере необходимости.

## Роли в multi-agent системах

### По функции

- **Orchestrator** — разбивает задачу, делегирует subagents, агрегирует результаты
- **Specialists** — выполняют специфичные типы работы (code, research, review, testing)
- **Critics** — оценивают работу specialists, находят проблемы
- **Memory agents** — управляют long-term memory, retrieval

### Каждая роль имеет

- System prompt описывающий responsibilities, constraints, output format
- Tools которые ей доступны (не все agents имеют доступ ко всем tools)
- Context scope — что она читает, что не читает
- Success criteria — когда task выполнена

## Паттерны оркестрации

### Linear workflow

Agent A → Agent B → Agent C. Sequential, каждый работает с output предыдущего.

Применение: определённый процесс (research → analysis → writeup).

Простая имплементация, предсказуемое поведение. Не гибко к unexpected.

### Router pattern

Orchestrator классифицирует входящий запрос и роутит на подходящего agent:

~~~
Request → Classifier → Route to:
                        ├─ Technical question → CodeAgent
                        ├─ Creative writing → WritingAgent
                        └─ Research → ResearchAgent
~~~

Применение: общие assistants с разными типами задач.

### Hierarchical (tree)

Manager agent разбивает задачу, делегирует subtasks, каждый subagent может дальше делегировать:

~~~
Manager
├── Researcher
│   ├── Web search agent
│   └── Document reader agent
└── Writer
    ├── Outline agent
    └── Draft agent
~~~

Применение: complex research, multi-stage planning.

Каждый уровень имеет свой context scope — не загромождает verhний уровень деталями нижнего.

### Debate / Multi-perspective

Несколько agents обсуждают одну проблему с разных углов, приходят к consensus:

~~~
Problem
    ↓
┌─── Agent A (perspective 1) ───┐
├─── Agent B (perspective 2) ───┤
└─── Agent C (critic) ──────────┘
    ↓
Synthesis
~~~

Применение: сложные решения где важна проверка разными углами, reducing single-agent bias.

### Supervisor pattern

Один agent делает работу, supervisor проверяет и approve/reject:

~~~
Worker agent → Output → Supervisor agent → Approve/Reject
                                           ↓ (reject)
                                        Worker retries
~~~

Применение: когда качество критично, нужна двойная проверка.

Схема этого пакета — supervisor pattern: developer → reviewer.

## Memory в agentic workflows

### Short-term memory

Conversation history в context window. Управляется LLM напрямую.

Ограничения — context window size. Длинные workflows выходят за лимит.

### Long-term memory

Данные которые сохраняются между sessions и retrieve по релевантности.

Архитектура:

- **Storage** — vector DB (Pinecone, Qdrant, pgvector) + possibly key-value для structured data
- **Retrieval** — semantic search + filtering по metadata
- **Update** — agent или orchestrator решает что сохранить в memory

Паттерн:

1. В начале задачи — retrieve relevant memories по запросу
2. В конце задачи — сохранить результаты которые могут быть полезны позже
3. Периодически — consolidate memories (merge duplicates, remove outdated)

### Scratchpad

Временная память в рамках одной задачи:

- Промежуточные результаты
- План задачи (tree of subtasks)
- Uncertainty tracking (что известно, что неизвестно)

Реализуется как файл на диске или state в memory который agent читает между итерациями.

## Tool use

### Tool definitions

Каждый tool имеет:

- **Name** — уникальный идентификатор
- **Description** — что делает, когда использовать
- **Parameters** — типизированная schema (JSON Schema)
- **Return value** — что возвращает и в каком формате

Description критичен — это то что LLM читает чтобы решить использовать tool.

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

Слишком специфичные tools — их много, agent запутывается. Слишком общие — agent не знает когда использовать.

Правило: tool покрывает atomic operation на уровне понятном человеку.

- ✅ `read_file(path)` — atomic, clear
- ✅ `search_codebase(query)` — atomic, clear
- ❌ `refactor_class(class_name)` — too high-level, unpredictable
- ❌ `str_operation(string, op_type)` — too generic

### Tool permissions

Agents имеют разный scope tools:

- Research agent — read-only tools (search, read)
- Developer agent — write tools (edit files, run code)
- Debugger agent — read + observation tools (logs, traces)

Принцип least privilege — agent имеет только те tools которые ему нужны.

### Error handling

Tool вызовы могут fail:

- Network errors
- Invalid parameters
- Resource not found
- Permission denied

Ошибки возвращаются agent в structured формате. Agent решает — retry, escalate, или report back to user.

## Plan execution

### Chain of thought

Agent перед действием explicitly думает:

~~~
Thought: I need to find the authentication logic. I'll search the codebase.
Action: search_codebase(query="authentication")
Observation: Found 3 files: auth/handler.go, auth/service.go, auth/middleware.go
Thought: The handler is entry point. Let me read it first.
Action: read_file(path="auth/handler.go")
...
~~~

Улучшает quality reasoning, делает процесс debuggable.

### Plan-then-execute

Agent сначала формирует план всей задачи, потом выполняет:

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

Подходит для предсказуемых workflows. Менее гибкий чем chain of thought но более структурированный.

### ReAct (Reasoning + Acting)

Комбинация — agent перемежает reasoning и actions, без явного pre-planning:

~~~
Thought → Action → Observation → Thought → Action → ...
~~~

Наиболее гибкий, работает хорошо для широкого класса задач.

## Context management

### Context window constraints

LLM имеют лимит context window (часто 200K+ tokens у современных моделей, но всё равно лимит).

Проблема: долгие agentic sessions накапливают context, упираются в лимит.

Решения:

**Summarization** — периодически summarize прошлую часть conversation в короткую версию, заменять ей original.

**Sliding window** — держать только последние N turns.

**External memory** — переносить детали в long-term memory, держать в context только pointers.

**Hierarchical** — подзадачи выполняются subagents с отдельным context, возвращают summary в parent.

### Context hygiene

Из [core/principles.md](../core/principles.md): принцип минимального контекста.

Специфично для agents:

- Agent читает только файлы указанные в task или явно необходимые
- Не исследует codebase "на всякий случай"
- После subtask — возвращает summary, не full context

## Debugging multi-agent systems

Сложнее чем debug одной LLM call. Принципы:

### Tracing

Каждое действие (LLM call, tool use, agent transition) логируется с:

- Timestamp
- Agent ID
- Input
- Output
- Duration
- Cost

OpenTelemetry или specialized observability (LangSmith, Langfuse, Helicone).

### Replay-ability

Возможность replay sessions с теми же inputs для debugging:

- Deterministic execution requires temperature=0, но это не всегда применимо
- Record-replay frameworks для reproducibility
- Snapshot state at key points

### Agent output inspection

Chain of thought должно быть видимо и сохранено. При проблеме — читать reasoning agent'а чтобы понять где пошло не так.

## Quality control

### Eval suite для agents

Отличается от eval для simple completions:

- Input — not single query, а full task description
- Output — agent's final answer + optionally trace of actions
- Evaluation — может требовать проверки side effects (созданные файлы, выполненные actions)
- Rubric — часто multi-dimensional (correctness, efficiency, safety)

### Golden traces

Сохранённые примеры successful agent sessions. Используются для:

- Testing (regression detection)
- Training (fine-tuning на successful patterns)
- Documentation (показать что agent может)

### Guard rails

Защита от unsafe или suboptimal behavior:

- **Action filters** — запрет определённых actions (file deletion вне scope, external API calls с sensitive data)
- **Budget limits** — максимум steps, максимум tokens, максимум cost per session
- **Human-in-the-loop** — для critical actions требуется approval

## Specific to Claude Code workflow

Если проект использует Claude Code как основной agentic engine:

### CLAUDE.md как agent configuration

CLAUDE.md — это persistent system prompt для всех sessions в проекте. Содержит:

- Project context
- Architectural rules
- Code conventions
- Roles definitions
- Quality gates

Каждый session начинается с чтения этого файла.

### Task definitions через guides

Структурированные задачи в `docs/day-N-guide.md` файлах:

- Явные промпты для agent
- Ожидаемый output
- Acceptance criteria
- Команды проверки

Agent получает задачу через короткую команду, читает guide, выполняет.

### Role switching через short commands

Короткие команды (цифры) переключают активную роль:

- Один и тот же Claude Code становится developer / reviewer / QA в зависимости от команды
- Каждая роль — отдельный файл role description
- Пользователь определяет когда какая роль нужна

Этот подход простой и работает. Альтернатива — полноценная multi-agent orchestration через отдельные processes — complexity которая может не окупиться для solo/small team проектов.
