# Модульный монолит — архитектурный паттерн

Как строить монолит правильно: один деплой, одна БД, но внутри — чёткие модули с явными границами.

## Что это и когда выбирать

**Модульный монолит** — архитектура где приложение развёрнуто как один бинарь/процесс, но код структурирован как набор модулей с явными API и изоляцией.

Противопоставление:

- **Классический монолит** ("big ball of mud") — всё в одной куче, любой код может вызвать любой другой, неявные зависимости
- **Микросервисы** — разные процессы, сеть между компонентами, сложный деплой и дебаг

Когда выбирать модульный монолит:

- Команда до 10-20 разработчиков
- Стартап/ранняя стадия — scope меняется, микросервисы замедлят итерации
- Нет specific scaling requirements для отдельных компонентов
- Нет organizational scaling (одна команда ответственна за весь продукт)

Модульный монолит — правильный выбор по умолчанию. Переход на микросервисы — когда появятся конкретные причины, не превентивно.

## Структура модулей

Каждый модуль содержит:

- **Domain entities** — бизнес-объекты (Order, User, Task)
- **Use cases** — бизнес-логика (CreateOrder, CompleteTask)
- **Ports** — интерфейсы к внешнему миру (OrderRepository, NotificationService)
- **Adapters** — реализации портов (PostgresOrderRepository, EmailNotificationService)

Пример структуры для Go:

~~~
internal/
  orders/                    # модуль Orders
    domain/
      order.go              # entity
      status.go             # value objects
    service/
      create_order.go       # use case
      approve_order.go      # use case
    port/
      repository.go         # interface
      notifier.go           # interface
    adapter/
      postgres_repo.go      # implementation
      email_notifier.go     # implementation
    api.go                  # public API модуля

  tasks/                     # модуль Tasks
    ...
~~~

Для TypeScript/Node.js аналогично, но через файловую структуру:

~~~
src/
  modules/
    orders/
      domain/
      service/
      port/
      adapter/
      index.ts              # публичный API
    tasks/
      ...
~~~

## Границы между модулями

Правило — модуль A использует модуль B **только через public API**. Прямое обращение к внутренним функциям или entities запрещено.

Public API модуля — явно обозначенный набор экспортов:

- В Go — функции и типы начинающиеся с большой буквы в основном пакете модуля
- В TypeScript — что экспортируется из `index.ts` модуля

Внутренние реализации скрыты:

- В Go — пакеты внутри модуля с lowercase именами или через `internal/`
- В TypeScript — файлы не реэкспортированные из `index.ts`

Проверка границ:

- Linter-правила которые запрещают импорт из "внутренностей" других модулей
- В Go — `internal/` пакеты автоматически не доступны снаружи
- В TypeScript — через `eslint-plugin-boundaries` или `dependency-cruiser`

## Взаимодействие модулей

Два паттерна, выбор зависит от ситуации.

### Синхронный вызов через public API

Для queries и простых commands:

~~~go
// orders module использует users module
func (s *OrderService) CreateOrder(ctx context.Context, cmd CreateOrderCommand) error {
    user, err := s.usersAPI.GetUser(ctx, cmd.UserID)
    if err != nil {
        return fmt.Errorf("getting user: %w", err)
    }

    if !user.CanPlaceOrder() {
        return ErrUserNotAllowed
    }

    // ... создание заказа
}
~~~

Когда использовать:

- Нужен немедленный ответ от другого модуля
- Простая операция без сложного workflow
- Модули тесно связаны по смыслу (orders невозможны без users)

### Событийная модель через in-process event bus

Для complex workflows и избежания сильного coupling:

~~~go
// orders module публикует событие
func (s *OrderService) CreateOrder(ctx context.Context, cmd CreateOrderCommand) error {
    order := domain.NewOrder(cmd)
    if err := s.repo.Save(ctx, order); err != nil {
        return err
    }

    s.events.Publish(OrderCreated{
        OrderID: order.ID,
        UserID:  order.UserID,
    })

    return nil
}

// notifications module подписан на событие
func (s *NotificationService) HandleOrderCreated(ctx context.Context, event OrderCreated) {
    s.sendEmail(ctx, event.UserID, "order_created_template", event)
}

// inventory module тоже подписан
func (s *InventoryService) HandleOrderCreated(ctx context.Context, event OrderCreated) {
    s.reserveItems(ctx, event.OrderID)
}
~~~

Когда использовать:

- Одно действие триггерит несколько независимых reactions
- Модули не должны знать друг о друге
- Операции могут выполняться параллельно или отложенно

## Общие зависимости

В модульном монолите часто возникает искушение создать "shared" модуль для общего кода. Правила:

- **shared не должен содержать бизнес-логики** — только infrastructure primitives (logger, config, database connection pool)
- Если в shared появилась бизнес-логика — это знак что нужен новый модуль, не shared
- Утилиты (formatters, validators) — в отдельных мелких модулях по темам, не одним "utils" свалкой

## База данных

В модульном монолите — одна БД, но разделение таблиц по модулям:

- Каждая таблица "принадлежит" одному модулю
- Только владелец таблицы делает DDL (create, alter, drop)
- Другие модули читают/пишут через public API модуля-владельца, не напрямую SQL к чужим таблицам
- Foreign keys между таблицами разных модулей — минимизировать, заменять на application-level consistency

Это подготовка к возможному выносу в отдельные сервисы. Если таблицы модулей независимы, модуль можно вынести вместе с его таблицами.

## Транзакции и границы consistency

- Транзакции внутри одного модуля — обычный database transaction
- Транзакции между модулями — **избегать**. Если нужна consistency между модулями — event-driven (eventual consistency) или saga pattern
- Если транзакция между модулями действительно нужна — значит модули разделены неправильно, пересмотреть границы

## Когда разделять на сервисы

Триггеры для выделения модуля в отдельный сервис:

- **Organizational**: разные команды разработки, разный release cadence
- **Scaling**: модуль требует специфичного scaling (memory-heavy, CPU-heavy, network-heavy)
- **Technology**: модуль требует другой стек (например, ML pipeline на Python, основное приложение на Go)
- **Availability**: модуль имеет другие SLA требования
- **Compliance**: модуль обрабатывает данные с особыми регуляторными требованиями (payments, health data)

Без этих триггеров — оставлять в монолите.

## Миграция монолит → сервисы

Если модули правильно изолированы, миграция в сервис — относительно простая:

1. Public API модуля уже существует (синхронные вызовы) — заменить на HTTP/gRPC
2. Events уже существуют — заменить in-process event bus на message broker (RabbitMQ, Kafka, Redis Streams)
3. Таблицы модуля выносятся в отдельную БД (или схему)
4. Транзакции между модулями уже заменены на eventual consistency — изменений не требуется
5. Deployment pipeline обновляется для нового сервиса

Это работа недели-месяца на модуль, не квартала. Если занимает больше — модули были разделены неправильно.

## Антипаттерны

- **Анемичный модуль** — модуль содержит только структуры данных без бизнес-логики, логика размазана по другим модулям. Решение: втянуть логику в модуль.
- **God module** — один модуль знает про всё остальное. Решение: split по responsibility.
- **Cyclic dependency** — модуль A зависит от B, B от A. Решение: выделить общий интерфейс, использовать dependency injection, или объединить модули если они действительно про одно.
- **Shared state** — два модуля мутируют одну структуру данных. Решение: один владелец данных, другие работают через его API.
- **Leaky abstraction** — public API модуля возвращает internal types или требует знания внутренней структуры. Решение: DTOs на границе модуля.
