# AI-heavy products — архитектура

Для продуктов где AI — центральный компонент. Как правильно организовать LLM-слой чтобы он был поддерживаемым и не превратился в хаос промптов.

## Model-agnostic architecture

AI-вызовы идут через единый интерфейс. Конкретная модель — деталь реализации.

~~~go
type LLMClient interface {
    Complete(ctx context.Context, req CompletionRequest) (*CompletionResponse, error)
    Embed(ctx context.Context, texts []string) ([][]float32, error)
}

type CompletionRequest struct {
    Prompt      string
    MaxTokens   int
    Temperature float32
    Metadata    RequestMetadata  // tenant_id, feature, version промпта
}
~~~

Реализации:

- OpenAI / Anthropic / Google через их API
- Local models через Ollama
- Self-hosted через vLLM
- Mock implementation для тестов

Переключение между ними — конфигурация, не изменение бизнес-кода:

~~~yaml
# config.yaml
llm:
  provider: anthropic  # anthropic | openai | ollama | vllm
  model: claude-opus-4
  api_key_env: ANTHROPIC_API_KEY
~~~

## Prompt management

### Промпты живут в отдельных файлах

Не inline в коде. Не в конфиг-файлах. Отдельные `.md` файлы или `.txt` в директории `prompts/`.

~~~
prompts/
  task_extraction/
    v1.md
    v2.md
    current.md  # symlink на активную версию
  subtask_suggestion/
    v1.md
    current.md
  priority_scoring/
    v1.md
    current.md
~~~

### Версионирование в git

Каждая версия промпта — отдельный файл (v1, v2, v3), не перезаписывается. Изменение промпта — новый файл + обновление symlink.

Почему не просто history git: быстрый rollback без git operations, возможность A/B test (часть пользователей на v2, часть на v3), audit log который промпт применялся к конкретному запросу.

### Templates с переменными

Промпты — это templates с placeholders:

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

Подстановка через template engine (Go template, Jinja, Handlebars), не через string concatenation. Это предотвращает prompt injection через user data:

~~~go
tmpl, _ := template.ParseFiles("prompts/task_extraction/current.md")
var buf bytes.Buffer
tmpl.Execute(&buf, PromptContext{
    CompanyName:  sanitize(company.Name),
    Industry:     company.Industry,
    DocumentText: sanitize(doc.Text),
})
~~~

### Metadata каждого промпта

В начале файла промпта — metadata:

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

## RAG-слой

Если используется RAG (Retrieval-Augmented Generation), он выделен в отдельный модуль с чёткими абстракциями.

### Компоненты

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

- **Parser** — извлекает текст из PDF/DOCX/HTML
- **Chunker** — разбивает на куски с оверлапом (типично 500-1000 токенов, overlap 100-200)
- **Embedder** — превращает в векторы (OpenAI embeddings, local BGE-M3, etc.)
- **VectorStore** — Qdrant, Weaviate, pgvector, etc.

### Fact-check перед использованием

Retrieved documents могут быть нерелевантными или устаревшими. Правило: retrieved documents не попадают в промпт слепо.

- **Relevance check** — повторная оценка релевантности (re-ranker модель или LLM-based evaluation)
- **Freshness check** — фильтрация по дате если актуальность важна
- **Source attribution** — в промпт передаются с источниками, LLM знает откуда информация
- **Groundedness check** — для critical applications, проверка что ответ LLM действительно основан на retrieved documents, не галлюцинация

### Hybrid search

Vector search часто недостаточен. Комбинация:

- Vector search для semantic similarity
- Keyword search (BM25) для exact matches
- Metadata filtering для structured constraints
- Re-ranking для финального порядка

## Eval suite

Набор тестовых кейсов для качества AI. Критичен — без него невозможно оценить влияние изменений.

### Структура

~~~
evals/
  task_extraction/
    cases.jsonl           # test cases
    rubric.md             # критерии оценки
    run.go                # runner
    results/
      2026-04-18.json     # результаты прогона
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

### Rubric — критерии оценки

Когда точный expected output невозможен (LLM генерирует free-text), используется rubric — набор критериев:

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

Rubric evaluated automatically (LLM-as-judge) или вручную на sample прогонах.

### Runner

Eval suite — отдельная команда, не часть обычного test suite (медленная, дорогая):

~~~bash
go run ./cmd/evals -suite=task_extraction -model=claude-opus-4
~~~

Output: results/YYYY-MM-DD.json с метриками (pass rate, per-dimension scores, failures с деталями).

### Regression alerts

Сравнение нового прогона с baseline:

- Если pass rate упал > 5% — alert, review новых failures
- Если per-dimension score упал — investigate какая dimension и почему
- CI может блокировать merge если eval regression

## Cost tracking

Каждый LLM-вызов логируется со структурированными данными.

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

Агрегация:

- Per tenant — для billing
- Per feature — какие фичи дорогие
- Per user — для user-level quotas
- Per model — сравнение стоимости/качества моделей

Alerts:

- Spike в расходах одного tenant — возможное злоупотребление или баг
- Расходы превысили budget — automatic throttling или notification
- Unusual patterns (ночные массовые вызовы, повторяющиеся одинаковые запросы) — investigation

## Caching

LLM calls дорогие. Caching — обязательный компонент.

### Embedding cache

Embeddings детерминированы и стабильны для одного и того же текста. Кэшируются всегда.

Key: hash(text) + model_id.
Storage: Redis или БД с TTL (embeddings не меняются, но model может deprecated).

### LLM response cache

Детерминированные запросы (temperature=0, stable context) — кэшируются.

Key: hash(prompt_template_id + prompt_version + input_variables + model + temperature).
TTL: зависит от use case (короткий если данные часто меняются).

**Важно**: инвалидация при изменении промпта. Поэтому prompt_version в key — при выкате новой версии промпта cache miss для всех запросов.

### Semantic cache

Для non-deterministic запросов — опционально. "Похожий запрос уже был, ответ переиспользуется".

Риск — плохая semantic match может дать неправильный ответ. Использовать только для non-critical applications с высоким threshold similarity.

## Fallback и degradation

LLM providers падают. Сеть медленная. Rate limits.

### Primary / fallback модели

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

Для критичных функций — fallback на non-AI путь:

- Если AI недоступен для task_extraction — показать документ без анализа, с сообщением "AI analysis временно недоступен"
- Если AI для subtask_suggestion падает — показать пустой template без pre-fill

Функция должна продолжать работать в degraded mode, не падать полностью.

### Timeout и retry

- Жёсткий timeout на LLM call (обычно 30-60 секунд)
- Retry с exponential backoff для retryable errors (5xx, rate limits)
- Максимум 2-3 retry, дальше fallback или error к пользователю

## Streaming и async

LLM calls — долгие (секунды-минуты для длинных ответов). UX требует правильной обработки.

### Streaming для UI

Для chat-like interfaces — streaming response через Server-Sent Events или WebSocket:

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

### Async jobs для long-running

Для operations которые занимают минуты (анализ большого документа, batch processing):

- User создаёт job через API
- Job попадает в queue
- Worker обрабатывает, обновляет status в БД
- User polls status или получает notification по завершению

Не блокировать HTTP request на минуты.

## Prompt injection defense

User input никогда не попадает в промпт напрямую. Санитизация:

- **Escape specific markers** — если промпт использует specific delimiters (```, XML tags), они удаляются/escapеются из user input
- **Length limits** — user input ограничен разумным размером
- **Content filters** — детектирование prompt injection patterns ("ignore previous instructions", "you are now...")
- **Output validation** — LLM response проверяется на ожидаемую структуру, не слепо показывается пользователю

Для critical applications — двух-этапная обработка: LLM сначала классифицирует intent user input, только разрешённые intents обрабатываются.

## Sensitive data в промптах

Чувствительные данные (ПД, коммерческая тайна) не отправляются во внешние API без compliance проверки.

Правила:

- **Self-hosted models** — для processing sensitive data предпочтительно
- **Data masking** — перед отправкой в external API, ПД заменяются на tokens (`[EMAIL_1]`, `[NAME_1]`), восстанавливаются после ответа
- **Opt-in consent** — user явно соглашается на processing внешним AI
- **Audit log** — каждый call с sensitive data логируется для compliance

## Fine-tuning workflow

Если используется fine-tuning:

- **Training data curation** — отдельный pipeline с review качества
- **Versioning** — модели версионируются как промпты
- **A/B testing** — новая версия не заменяет старую мгновенно, постепенный rollout
- **Rollback plan** — возможность быстро вернуться к предыдущей версии
- **Eval suite** — обязателен для каждой новой версии модели

## Observability

Дополнительно к обычной observability:

- **Prompt trace** — для каждого вызова: какой промпт использовался (ID + version), какой input, какой output
- **Token distribution** — метрики input/output tokens per feature
- **Latency histograms** — p50, p95, p99 per model и feature
- **Error categorization** — rate limits, timeouts, content filter, validation failures отдельно
- **Quality metrics** — через eval suite, тренды во времени

Dashboards для монитора AI-системы в realtime.
