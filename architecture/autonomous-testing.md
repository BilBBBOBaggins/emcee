# Autonomous Testing — архитектурный паттерн

Паттерн для автоматизации UI-тестирования через **встроенный в приложение IPC-сервер**, позволяющий тестам управлять приложением как real user через внешний tool.

Паттерн работает и позволяет автономное UI-тестирование для AI-агентов — критично когда автоматические gate-тесты (unit, integration) не могут проверить реальное поведение UI.

**Применимо для**: desktop apps (Qt, WPF, Tauri), mobile apps (Flutter, native), любых UI-heavy приложений где E2E automation через browser (Selenium, Playwright) не применим.

**Не применимо для**: web apps (у них Playwright и подобные решают проблему), headless services.

## Проблема которую решает

Automated gates (unit, integration) покрывают код в изоляции. Но **между слоями** бывают разрывы:

- Кнопка в UI не подключена к handler'у
- Signal из backend не прокидывается в model
- Model обновляется но UI не перерисовывается
- Action триггерит правильный call, но response не обрабатывается

Unit тесты не ловят эти проблемы — они mock'ают соседние слои. Manual testing ловит, но не автоматизируется.

Autonomous testing — UI-driven tests с полным стеком **без** human в цикле. AI-агент может запустить тест, проверить результат, диагностировать проблему.

## Базовая архитектура

~~~
┌──────────────────────┐
│  Test Script         │  (Python, JS, etc.)
│  (external)          │
└──────────────────────┘
           ↕ JSON-RPC / similar
┌──────────────────────┐
│  Application         │
│  ┌─────────────────┐ │
│  │  TestDriver     │ │  IPC server внутри приложения
│  │  (IPC server)   │ │
│  └─────────────────┘ │
│  ┌─────────────────┐ │
│  │  UI             │ │
│  │  Bridge         │ │  Real application code
│  │  Core           │ │
│  └─────────────────┘ │
└──────────────────────┘
           ↕
┌──────────────────────┐
│  External services   │  Real backend, databases
└──────────────────────┘
~~~

TestDriver — компонент внутри приложения который:

- Открывает IPC endpoint (socket, named pipe, HTTP)
- Принимает команды через стандартизированный протокол
- Выполняет actions на UI элементах
- Возвращает state UI в структурированном формате

External test script:

- Подключается к IPC endpoint
- Отправляет последовательность команд
- Проверяет results
- Сохраняет screenshots, logs, traces

## Активация TestDriver

TestDriver включён **только в специальной сборке** или через runtime flag.

### Compile-time flag

~~~cpp
#ifdef ENABLE_TEST_DRIVER
    testDriver = new TestDriver(this);
    testDriver->start();
#endif
~~~

Сборка:

~~~bash
cmake -B build-qa -DENABLE_TEST_DRIVER=ON
~~~

Production builds — TestDriver отсутствует, нет security risk.

### Runtime flag

~~~cpp
if (commandLine.contains("--test-mode")) {
    testDriver = new TestDriver(this);
    testDriver->start();
}
~~~

Запуск:

~~~bash
./MyApp --test-mode
~~~

Более гибко, но security concern — нужно убедиться что флаг не активируется случайно в production.

### Изоляция через отдельный билд

Рекомендуется — TestDriver в отдельной build directory, не в production build.

- Production: `build/` — без TestDriver
- Testing: `build-qa/` — с TestDriver

Предотвращает accidental deployment.

## Протокол IPC

### Требования

- Простой для debugging
- Typed commands с validation
- Async-friendly (приложение не блокируется на ответ)
- Language-agnostic (test scripts на разных языках)

### JSON-RPC 2.0

Рекомендуемый выбор. Стандартизирован, typed, async.

Request:

~~~json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "click",
  "params": {
    "objectName": "syncButton"
  }
}
~~~

Response:

~~~json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "success": true
  }
}
~~~

Error:

~~~json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32001,
    "message": "Object not found",
    "data": {"objectName": "syncButton"}
  }
}
~~~

### Transport

- **Local socket** (Unix socket, named pipe) — для same-machine tests. Быстрое, простое
- **TCP localhost** — если нужна cross-process communication
- **WebSocket** — если tests в browser или remote

Для большинства случаев local socket оптимален.

### Framing

Newline-delimited JSON — один message на строку. Простой parsing.

Для большого payload — length-prefixed frames.

## Categories of commands

### UI interaction

~~~
click(objectName) — single click
doubleClick(objectName)
rightClick(objectName)
hover(objectName)
scroll(objectName, direction, amount)
dragDrop(sourceObjectName, targetObjectName)
type(objectName, text)
keyPress(keyCombo)
clickIndex(listObjectName, index)  — клик по элементу списка
~~~

### Property access

~~~
getProperty(objectName, propertyName)
setProperty(objectName, propertyName, value)
getModel(modelName)  — весь model state
getModelCount(modelName)
~~~

### Waiting и verification

~~~
exists(objectName) → bool
isVisible(objectName) → bool
waitForObject(objectName, timeout)  — ждёт появления
waitForProperty(objectName, property, expectedValue, timeout)
~~~

### Visual

~~~
screenshot() → image path
screenshotObject(objectName) → image path
~~~

### State inspection

~~~
state() — snapshot всего UI tree
modelState() — ground truth data model
diff(previousState) — что изменилось
~~~

### Application control

~~~
getAppState() — high-level app state
resetState() — clear all data, return to clean state
waitForSync() — ждёт завершения background operations
invoke(method, args) — прямой вызов метода (для setup/teardown)
~~~

### External integration

Для тестирования интеграций с внешними сервисами:

~~~
externalCheck(params) — проверка данных на сервере
externalPut(params) — создание данных на сервере (для server→client тестов)
externalDelete(params)
~~~

## Object identification

Тест должен найти UI element для взаимодействия. Варианты:

### By object name

Каждый interactable element имеет уникальное `objectName`:

~~~qml
Button {
    objectName: "syncButton"
    text: "Send"
}
~~~

~~~python
driver.click("syncButton")
~~~

Рекомендуется — explicit, controlled, survives refactoring.

### By accessibility properties

Используя accessible name, role, etc.:

~~~python
driver.click(role="button", name="Send")
~~~

Плюсы: совмещается с accessibility testing. Минусы: менее controlled, может ломаться при UI changes.

### By path

Tree-based identification:

~~~python
driver.click("/mainWindow/sidebar/syncButton")
~~~

Fragile — ломается при изменении UI hierarchy. Использовать только при необходимости.

## Context properties access

Для bridge models (которые не live в UI tree):

~~~python
driver.get_property("@messageModel", "count")
driver.get_model("@userModel")
~~~

Prefix `@` указывает на context property.

## Test scenarios

### Format

Scenarios в JSON (или YAML) — declarative, легко generate, легко inspect:

~~~json
{
  "name": "Sync Task Scenario",
  "description": "User creates and syncs a task",
  "steps": [
    {
      "method": "click",
      "params": {"objectName": "newTaskButton"},
      "description": "Open task editor"
    },
    {
      "method": "waitForObject",
      "params": {"objectName": "taskEditorView", "timeout": 5000}
    },
    {
      "method": "type",
      "params": {"objectName": "titleField", "text": "Test task 001"}
    },
    {
      "method": "click",
      "params": {"objectName": "syncButton"}
    },
    {
      "method": "waitForProperty",
      "params": {
        "objectName": "statusLabel",
        "property": "text",
        "value": "Synced",
        "timeout": 30000
      }
    }
  ]
}
~~~

### Execution

Test runner читает scenario, выполняет steps последовательно, сохраняет outcomes.

### Generation

AI-агенты могут **generate scenarios** из тест-кейсов (written by QA UAT). Acceptance criteria в Given/When/Then → scenario steps.

## Integration с AI-agent workflow

TestDriver — критическая часть для автономного AI-driven development.

### Loop

1. Agent пишет код
2. Agent запускает scenario тест через TestDriver
3. TestDriver возвращает state после каждого шага
4. Agent анализирует state — expected vs actual
5. Если разрыв — agent диагностирует причину (читает код, логи, state)
6. Agent пишет fix, повторяет loop

### Key principle: state comparison

Agent сравнивает UI state с expected state в структурированном формате, не через скриншоты.

**Preferred flow**:

1. Agent запрашивает `state()` — structured JSON
2. Сравнивает с expected JSON
3. Finds diff

**Fallback**:

4. Если JSON недостаточен — screenshot для визуального inspection
5. Analyze screenshot (if needed)

Screenshot — expensive (visual analysis через VLM), use sparingly. JSON state — cheap и precise.

### Rules для agent

- Анализируй state/JSON в первую очередь
- Screenshot только когда JSON показывает аномалию и нужно понять визуально
- Максимум 1 screenshot за раз, не накапливать
- Если тест падает 3 раза после fixes — остановиться, описать проблему
- Не менять публичные API core/bridge без подтверждения
- Не менять архитектурные решения
- Один коммит = один fix

## Test accounts и data

E2E тесты требуют реальных данных. Зафиксированные test accounts — лучший подход:

| Account | Data volume | Purpose |
|---------|------------|---------|
| heavy | огромный | stress tests |
| medium | средний | типичный случай |
| small | маленький | быстрые тесты |
| empty | пустой | edge case |

Каждый test specifies которые accounts нужны. Минимум в прогоне — 3 account разного типа.

Accounts не меняются между прогонами — reproducibility.

## Observations и assertions

### Что наблюдать

- Visible UI state (элементы, text, images)
- Internal model state (data в bridge models)
- External state (данные на сервере, files в filesystem)
- Changes over time (что произошло после action)

### Уровни verification

**L1 — UI**: кнопка появилась, text отобразился. Быстро но может пропустить semantic issues.

**L2 — Model**: bridge model имеет ожидаемые данные. Более глубокая проверка.

**L3 — External**: данные доехали до сервера / БД. Самая полная проверка.

Хорошие тесты используют все три уровня — action → L1 check → L2 check → L3 check → (опционально) back to L1 после sync.

### 4-step pattern

Для каждого теста:

~~~
1. ACTION через UI (click, type, etc.)
2. IMMEDIATE VISUAL RESULT (toast, dialog, state change)
3. REAL RESULT (data на external system)
4. UI IN SYNC WITH SERVER (UI не откатился, UI отражает серверное состояние)
~~~

Шаг 4 ловит два типа багов:

- **UI откатился**: optimistic update отменён после server failure
- **UI застыл**: server обновил, но UI не перечитал

Все 4 шага обязательны. Детали — см. [roles/qa-e2e.md](../roles/qa-e2e.md).

## Implementation specifics

### Thread safety

TestDriver получает команды в отдельном потоке, но UI operations должны быть в main thread.

Marshalling:

~~~cpp
void TestDriver::handleClick(const QString& objectName) {
    QMetaObject::invokeMethod(mainWindow, [=]() {
        // runs on main thread
        auto obj = findObject(objectName);
        QMouseEvent click(...);
        QApplication::sendEvent(obj, &click);
    }, Qt::BlockingQueuedConnection);
}
~~~

`BlockingQueuedConnection` — caller ждёт выполнения. Важно для deterministic testing.

### Finding objects

Рекурсивный поиск в object tree:

~~~cpp
QObject* findByObjectName(QObject* root, const QString& name) {
    if (root->objectName() == name) return root;

    for (auto child : root->children()) {
        if (auto found = findByObjectName(child, name)) {
            return found;
        }
    }

    return nullptr;
}
~~~

Для QML — специфика: context properties, repeater instances, loaders.

### State serialization

`state()` команда возвращает JSON представление UI tree:

~~~json
{
  "mainWindow": {
    "visible": true,
    "children": {
      "sidebar": {
        "visible": true,
        "properties": {...}
      },
      "contentArea": {
        "visible": true,
        "currentView": "messages",
        "properties": {...}
      }
    }
  }
}
~~~

Useful for:

- Comparison (expected vs actual)
- Debugging (what's visible now?)
- Diff (what changed?)

## Ограничения

### Что TestDriver не заменяет

**Unit tests** — быстрые, isolated, много. TestDriver — медленный, integrated, мало. Разные concerns.

**Visual testing** — pixel-perfect проверка визуальной корректности. Screenshot comparison tools для этого.

**Performance testing** — TestDriver добавляет overhead, misleading для perf tests.

**Manual exploratory testing** — человек лучше находит unexpected issues.

### Поддержка

TestDriver — infrastructure code который требует поддержки:

- Добавление новых commands по мере роста приложения
- Maintenance при major UI changes
- Documentation для new team members

Invest в это соразмерно размеру проекта.

## Эволюция от manual к autonomous

Для существующего проекта — постепенный подход:

1. **Manual E2E тесты сначала** — через human tester или Selenium/Playwright если web
2. **Semi-autonomous** — TestDriver commands, но test scenarios written by humans
3. **Autonomous** — AI-агенты генерируют и выполняют scenarios on demand
4. **Self-healing** — агенты не только тестируют но и reporting issues + suggesting fixes

Each step — investment. Start simple, evolve by demonstrated need.
