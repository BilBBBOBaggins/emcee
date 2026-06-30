# Layered Architecture — общий паттерн слоёв

Разделение кода на слои с чётким направлением зависимостей. Один из самых фундаментальных архитектурных паттернов — применим в любом типе приложения.

## Базовый принцип

Код организован в слои, зависимости между ними **однонаправленные**:

~~~
Layer N   ↓
Layer N-1 ↓
...
Layer 1
~~~

Каждый слой может использовать слои **ниже**, но не слои **выше**. Обратные импорты — запрещены.

Это единственный инвариант паттерна. Количество слоёв, их назначение, конкретные названия — варьируются по проектам.

## Когда применять

Почти всегда. Layered architecture — настолько фундаментальный паттерн что почти не является выбором.

**Не применять** имеет смысл только в:

- Простые скрипты (< 100 строк)
- Чистые библиотеки с единственной функцией
- Prototype/throwaway код

Для всего остального — слои.

## Количество слоёв

Зависит от сложности и типа проекта. Типичные варианты:

### 2 слоя — для простых приложений

~~~
Application Logic
Data Access
~~~

Или:

~~~
Handlers / Entry Points
Business Logic
~~~

Подходит для: CLI tools, simple APIs, scripts с persistence.

### 3 слоя — самый распространённый вариант

Классическое разделение:

~~~
Presentation   (UI / API handlers / CLI commands)
Business       (Domain logic, use cases)
Persistence    (Data access, external services)
~~~

Подходит для: большинства business applications, backend services, web apps.

### 4 слоя — с явным domain слоем

~~~
Presentation   (UI / API)
Application    (Use cases / orchestration)
Domain         (Business rules, entities)
Infrastructure (Persistence, external)
~~~

Разница с 3-слойной — application слой оркестрирует use cases, а domain слой содержит pure business rules без зависимостей. Это структура близкая к Clean Architecture и Hexagonal.

Подходит для: сложные business applications, проекты с rich domain model, long-lived enterprise systems.

### 5+ слоёв — обычно over-engineering

Исключение — specialized systems (финансовые системы с несколькими slice'ами compliance, multi-tenant SaaS с явными tenant-level concerns).

Для большинства проектов 5+ слоёв — сигнал что структура слишком сложная и нужен рефакторинг.

## Направление зависимостей

Главное правило: зависимости идут **вниз**, не вверх.

Что это значит на практике:

- Presentation импортирует Business, но не наоборот
- Business импортирует Persistence (через интерфейсы), но не наоборот
- Domain не знает о существовании Presentation

### Dependency Inversion

Чтобы Business мог использовать Persistence не зависая от конкретной реализации — Dependency Inversion через интерфейсы:

Business layer определяет интерфейс что ему нужно:

~~~go
// internal/business/user_service.go
type UserRepository interface {
    FindByID(ctx context.Context, id UserID) (*User, error)
    Save(ctx context.Context, user *User) error
}
~~~

Persistence layer реализует этот интерфейс:

~~~go
// internal/persistence/postgres_user_repo.go
type PostgresUserRepository struct {
    db *sql.DB
}

func (r *PostgresUserRepository) FindByID(ctx context.Context, id UserID) (*User, error) {
    // ...
}
~~~

Результат — Business не импортирует Persistence. Интерфейс определён в Business, реализация — в Persistence. Зависимость инвертирована.

## Конкретные варианты структуры

### Для backend API (Go/Node/Python)

~~~
handlers/          # HTTP handlers, request/response
service/           # Business logic, use cases
repository/        # Data access
model/             # Domain entities, shared types
~~~

### Для fullstack web app

~~~
frontend/
  components/      # UI components
  hooks/           # React state
  api/             # API client

backend/
  handlers/        # HTTP handlers
  service/         # Business logic
  repository/      # Data access
~~~

Frontend и backend — разные physical layers (разные процессы), каждый со своими логическими слоями.

### Для CLI tool

~~~
cmd/               # Command parsing, entry points
app/               # Application logic
domain/            # Core entities, rules
infra/             # File system, network, APIs
~~~

### Для desktop app с native UI и declarative UI

Специальный случай — см. [three-tier-with-bridge.md](three-tier-with-bridge.md). Паттерн включает middle layer (bridge/adapter) между native code и declarative UI.

### Для игры

~~~
engine/            # Game engine, rendering
gameplay/          # Game rules, entities
scripting/         # Scripted content
content/           # Assets
~~~

### Для ML pipeline

~~~
ingestion/         # Data collection
preprocessing/     # Cleaning, feature engineering
training/          # Model training
inference/         # Model serving
api/               # External API
~~~

## Правила слоёв

### Слой делает одну вещь

Каждый слой имеет чёткую ответственность:

- Presentation — трансформация input/output (HTTP → domain, domain → HTTP)
- Business — enforcement бизнес-правил
- Persistence — сохранение и загрузка данных

Если слой делает несколько не связанных вещей — возможно нужно разделить на два слоя или выделить отдельный компонент.

### Слой не знает о слоях выше

Business не знает про HTTP. Domain не знает про UI. Persistence не знает про use cases.

Это даёт свойства:

- Business logic тестируется без HTTP
- Domain тестируется без БД
- Persistence может быть заменена (PostgreSQL → MongoDB) без изменения Business

### DTOs на границе слоёв

Объекты которые пересекают границу слоёв — DTOs (Data Transfer Objects), не domain entities.

Почему:

- Domain entity имеет бизнес-методы которые не нужны снаружи
- DTO — простая структура, легко serializable
- Изменение domain entity не ломает external API

### Anti-corruption layer

Между доменом и внешними системами (third-party APIs, legacy systems) — anti-corruption layer:

- Трансформирует внешние модели в domain модели
- Защищает domain от изменений во внешних системах
- Localizes знание о внешнем формате в одном месте

## Anti-patterns

### Leaky abstraction

Верхний слой знает детали реализации нижнего:

~~~go
// BAD: business code работает с SQL exceptions
func (s *UserService) Register(ctx context.Context, email string) error {
    err := s.repo.Save(ctx, user)
    if pgErr, ok := err.(*pq.Error); ok && pgErr.Code == "23505" {
        return ErrDuplicateEmail
    }
}
~~~

Решение: Persistence преобразует SQL errors в domain errors.

### God layer

Один слой разросся, делает всё:

- "Service layer" из 1000 LOC содержит и business logic, и HTTP handling, и caching, и retry logic

Решение: разделить на более мелкие слои или компоненты с чёткими responsibilities.

### Bypassing layers

Presentation напрямую дёргает Persistence минуя Business:

~~~go
// BAD: controller напрямую запрашивает БД
func (h *Handler) GetUser(w http.ResponseWriter, r *http.Request) {
    user := h.db.QueryUserByID(userID)  // обходит service
    json.NewEncoder(w).Encode(user)
}
~~~

Решение: все запросы через Business layer.

### Cyclic dependencies

Business импортирует Persistence, Persistence импортирует Business. Нарушает фундаментальный принцип.

Решение: Dependency Inversion через интерфейсы.

### Shared utilities that grow into god modules

"Utils" или "Common" который импортируется всеми. Становится высоко-coupled.

Решение: мелкие специализированные модули, каждый про одну тему.

## Проверка правильности разделения

Вопросы себе:

1. Могу ли я протестировать Business без Persistence и без HTTP?
2. Могу ли я заменить БД (PostgreSQL → SQLite для тестов) не меняя Business?
3. Знает ли Domain слой про HTTP или БД? (Не должен)
4. Сколько файлов надо изменить чтобы добавить новое поле в entity? (Должно быть 2-3, не 10+)

Если ответы "нет" или "много" — слои разделены неправильно.

## Эволюция паттерна

Layered architecture — не догма. По мере роста проекта возможны адаптации:

- **Hexagonal / Ports and Adapters** — обобщение layered с несколькими входными и выходными портами
- **Clean Architecture** — Uncle Bob формализация с жёсткими правилами зависимостей
- **Onion Architecture** — похожа на Clean, с domain в центре и слоями вокруг
- **Vertical slicing / Feature folders** — альтернатива, где вместо слоёв — vertical slices по features

Все эти паттерны — variations на ту же тему однонаправленных зависимостей. Изучать их стоит когда базовый layered approach начинает ограничивать.

Для большинства проектов — классический 3-4 слой с Dependency Inversion достаточен на годы вперёд.
