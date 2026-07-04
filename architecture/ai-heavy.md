# AI-heavy products — architecture

For products where AI is a central component. How to organize the LLM layer so it stays maintainable and doesn't turn into a mess of prompts.

## Model-agnostic architecture

AI calls go through a single interface. The specific model is an implementation detail.

~~~go
type LLMClient interface {
    Complete(ctx context.Context, req CompletionRequest) (*CompletionResponse, error)
    Embed(ctx context.Context, texts []string) ([][]float32, error)
}

type CompletionRequest struct {
    Prompt      string
    MaxTokens   int
    Temperature float32
    Metadata    RequestMetadata  // tenant_id, feature, prompt version
}
~~~

Implementations:

- OpenAI / Anthropic / Google via their APIs
- Local models via Ollama
- Self-hosted via vLLM
- Mock implementation for tests

Switching between them — configuration, not a change to business code:

~~~yaml
# config.yaml
llm:
  provider: anthropic  # anthropic | openai | ollama | vllm
  model: claude-opus-4
  api_key_env: ANTHROPIC_API_KEY
~~~

## Prompt management

### Prompts live in separate files

Not inline in code. Not in config files. Separate `.md` or `.txt` files in a `prompts/` directory.

~~~
prompts/
  task_extraction/
    v1.md
    v2.md
    current.md  # symlink to the active version
  subtask_suggestion/
    v1.md
    current.md
  priority_scoring/
    v1.md
    current.md
~~~

### Versioning in git

Each prompt version — a separate file (v1, v2, v3), never overwritten. Changing a prompt — a new file + updating the symlink.

Why not just git history: fast rollback without git operations, ability to A/B test (part of users on v2, part on v3), an audit log of which prompt was applied to a specific request.

### Templates with variables

Prompts are templates with placeholders:

~~~markdown
# prompts/task_extraction/v2.md

You are extracting action items from a document for {{COMPANY_NAME}}.

Team profile:
- Industry: {{INDUSTRY}}
- Size: {{COMPANY_SIZE}}
- Region: {{REGION}}

Document text:
{{DOCUMENT_TEXT}}

Extract and provide:
1. Action items with owners
2. Suggested due dates
3. Priority of each
~~~

Substitution via a template engine (Go template, Jinja, Handlebars), not via string concatenation. This prevents prompt injection through user data:

~~~go
tmpl, _ := template.ParseFiles("prompts/task_extraction/current.md")
var buf bytes.Buffer
tmpl.Execute(&buf, PromptContext{
    CompanyName:  sanitize(company.Name),
    Industry:     company.Industry,
    DocumentText: sanitize(doc.Text),
})
~~~

### Metadata for each prompt

At the start of the prompt file — metadata:

~~~markdown
---
id: task_extraction
version: 2
model: claude-opus-4
temperature: 0.2
max_tokens: 4000
description: Extracts action items from documents into tasks
changelog:
  - v1: initial version
  - v2: added priority scoring, improved structure
---

You are extracting action items from a document for {{COMPANY_NAME}}.
...
~~~

## RAG layer

If RAG (Retrieval-Augmented Generation) is used, it's split into a separate module with clear abstractions.

### Components

~~~go
type VectorStore interface {
    Upsert(ctx context.Context, docs []Document) error
    Search(ctx context.Context, query []float32, limit int) ([]SearchResult, error)
    Delete(ctx context.Context, ids []string) error
}

type Embedder interface {
    EmbedQuery(ctx context.Context, text string) ([]float32, error)
    EmbedDocuments(ctx context.Context, texts []string) ([][]float32, error)
}

type Retriever interface {
    Retrieve(ctx context.Context, query string, filters Filters) ([]Document, error)
}
~~~

### Document preparation pipeline

~~~
Raw source → Parser → Chunker → Embedder → VectorStore
~~~

- **Parser** — extracts text from PDF/DOCX/HTML
- **Chunker** — splits into chunks with overlap (typically 500-1000 tokens, overlap 100-200)
- **Embedder** — turns them into vectors (OpenAI embeddings, local BGE-M3, etc.)
- **VectorStore** — Qdrant, Weaviate, pgvector, etc.

### Fact-check before use

Retrieved documents can be irrelevant or stale. Rule: retrieved documents don't go into the prompt blindly.

- **Relevance check** — re-evaluate relevance (re-ranker model or LLM-based evaluation)
- **Freshness check** — filter by date when currency matters
- **Source attribution** — passed into the prompt with sources, the LLM knows where the information came from
- **Groundedness check** — for critical applications, verify that the LLM's answer is actually grounded in retrieved documents, not a hallucination

### Hybrid search

Vector search alone is often insufficient. A combination:

- Vector search for semantic similarity
- Keyword search (BM25) for exact matches
- Metadata filtering for structured constraints
- Re-ranking for the final order

## Eval suite

A set of test cases for AI quality. Critical — without it, you can't assess the impact of changes.

### Structure

~~~
evals/
  task_extraction/
    cases.jsonl           # test cases
    rubric.md             # evaluation criteria
    run.go                # runner
    results/
      2026-04-18.json     # run results
~~~

### Test case format

~~~json
{
  "id": "doc_001",
  "input": {
    "company": {...},
    "document": {...}
  },
  "expected": {
    "extracted_count_min": 3,
    "must_mention": ["owner", "due_date", "priority"]
  },
  "rubric_weight": 1.0
}
~~~

### Rubric — evaluation criteria

When an exact expected output is impossible (the LLM generates free text), a rubric is used — a set of criteria:

~~~markdown
# Action-item extraction rubric

Score each dimension 0-10:

1. **Completeness** — covers all action items (title, owner, due date)
2. **Accuracy** — no hallucinated facts, grounded in source document
3. **Actionability** — provides clear next steps
4. **Structure** — follows expected format
5. **Tone** — professional, no unnecessary padding

Aggregate: weighted average.
Passing threshold: 7.5
~~~

Rubric evaluated automatically (LLM-as-judge) or manually on sample runs.

### Runner

The eval suite — a separate command, not part of the regular test suite (slow, expensive):

~~~bash
go run ./cmd/evals -suite=task_extraction -model=claude-opus-4
~~~

Output: results/YYYY-MM-DD.json with metrics (pass rate, per-dimension scores, failures with details).

### Regression alerts

Comparing the new run against a baseline:

- If pass rate drops > 5% — alert, review the new failures
- If a per-dimension score drops — investigate which dimension and why
- CI can block a merge on eval regression

## Cost tracking

Every LLM call is logged with structured data.

~~~go
type LLMCallLog struct {
    Timestamp     time.Time
    TenantID      uuid.UUID
    UserID        uuid.UUID
    Feature       string        // "task_extraction", "subtask_suggestion"
    PromptVersion string        // "v2"
    Model         string        // "claude-opus-4"
    InputTokens   int
    OutputTokens  int
    CostUSD       float64
    LatencyMs     int
    Success       bool
    Error         string
}
~~~

Aggregation:

- Per tenant — for billing
- Per feature — which features are expensive
- Per user — for user-level quotas
- Per model — comparing cost/quality of models

Alerts:

- A spike in one tenant's spend — possible abuse or a bug
- Spend exceeded budget — automatic throttling or notification
- Unusual patterns (nightly mass calls, repeated identical requests) — investigation

## Caching

LLM calls are expensive. Caching — a mandatory component.

### Embedding cache

Embeddings are deterministic and stable for the same text. Always cached.

Key: hash(text) + model_id.
Storage: Redis or a DB with TTL (embeddings don't change, but a model can be deprecated).

### LLM response cache

Deterministic requests (temperature=0, stable context) — cached.

Key: hash(prompt_template_id + prompt_version + input_variables + model + temperature).
TTL: depends on the use case (short if the data changes often).

**Important**: invalidation on prompt change. That's why prompt_version is in the key — rolling out a new prompt version causes a cache miss for all requests.

### Semantic cache

For non-deterministic requests — optional. "A similar request has already been made, the answer is reused."

Risk — a poor semantic match can give the wrong answer. Use only for non-critical applications with a high similarity threshold.

## Fallback and degradation

LLM providers go down. The network is slow. Rate limits.

### Primary / fallback models

~~~go
func (s *Service) Complete(ctx context.Context, req CompletionRequest) (*Response, error) {
    resp, err := s.primaryLLM.Complete(ctx, req)
    if err == nil {
        return resp, nil
    }

    if isRetryable(err) {
        s.logger.Warn("primary LLM failed, trying fallback", "error", err)
        return s.fallbackLLM.Complete(ctx, req)
    }

    return nil, err
}
~~~

### Non-AI fallback

For critical functions — fallback to a non-AI path:

- If AI is unavailable for task_extraction — show the document without analysis, with a message "AI analysis temporarily unavailable"
- If AI for subtask_suggestion fails — show an empty template with no pre-fill

The feature should keep working in degraded mode, not fail completely.

### Timeout and retry

- A hard timeout on the LLM call (usually 30-60 seconds)
- Retry with exponential backoff for retryable errors (5xx, rate limits)
- Maximum 2-3 retries, then fallback or an error to the user

## Streaming and async

LLM calls are long (seconds-minutes for long responses). UX requires handling this properly.

### Streaming for the UI

For chat-like interfaces — streaming response via Server-Sent Events or WebSocket:

~~~go
func (h *Handler) StreamCompletion(w http.ResponseWriter, r *http.Request) {
    // SSE headers
    w.Header().Set("Content-Type", "text/event-stream")

    stream, err := h.llm.CompleteStream(ctx, req)
    if err != nil { /* handle */ }

    for chunk := range stream {
        fmt.Fprintf(w, "data: %s\n\n", chunk.Text)
        w.(http.Flusher).Flush()
    }
}
~~~

### Async jobs for long-running work

For operations that take minutes (analyzing a large document, batch processing):

- The user creates a job via the API
- The job goes into a queue
- A worker processes it, updates status in the DB
- The user polls status or gets a notification on completion

Don't block the HTTP request for minutes.

## Prompt injection defense

User input never goes into the prompt directly. Sanitization:

- **Escape specific markers** — if the prompt uses specific delimiters (```, XML tags), they're removed/escaped from user input
- **Length limits** — user input is capped at a reasonable size
- **Content filters** — detecting prompt injection patterns ("ignore previous instructions", "you are now...")
- **Output validation** — the LLM response is checked against the expected structure, not shown to the user blindly

For critical applications — two-stage processing: the LLM first classifies the intent of the user input, only allowed intents are processed.

## Sensitive data in prompts

Sensitive data (personal data, trade secrets) isn't sent to external APIs without a compliance check.

Rules:

- **Self-hosted models** — preferred for processing sensitive data
- **Data masking** — before sending to an external API, personal data is replaced with tokens (`[EMAIL_1]`, `[NAME_1]`), restored after the response
- **Opt-in consent** — the user explicitly consents to processing by external AI
- **Audit log** — every call with sensitive data is logged for compliance

## Fine-tuning workflow

If fine-tuning is used:

- **Training data curation** — a separate pipeline with quality review
- **Versioning** — models are versioned like prompts
- **A/B testing** — the new version doesn't replace the old one instantly, gradual rollout
- **Rollback plan** — the ability to quickly revert to the previous version
- **Eval suite** — mandatory for every new model version

## Observability

In addition to regular observability:

- **Prompt trace** — for every call: which prompt was used (ID + version), what input, what output
- **Token distribution** — input/output token metrics per feature
- **Latency histograms** — p50, p95, p99 per model and feature
- **Error categorization** — rate limits, timeouts, content filter, validation failures tracked separately
- **Quality metrics** — via the eval suite, trends over time

Dashboards for monitoring the AI system in real time.
