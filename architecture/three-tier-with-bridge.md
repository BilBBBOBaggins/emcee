# Three-tier with Bridge — архитектурный паттерн

Специальный случай layered architecture для desktop/mobile приложений с native code + declarative UI. Middle layer (bridge) адаптирует нативный мир к декларативному.

**Когда применять**: Qt + QML, WPF + XAML с MVVM, Flutter с platform channels, Tauri (Rust + JS frontend), React Native bridge, Jetpack Compose с native state.

**Когда НЕ применять**: fullstack web apps (там backend/API/frontend — другая структура), pure backend services, CLI tools.

## Структура

Три слоя с конкретными responsibilities:

~~~
┌─────────────────────────────────────┐
│  UI Layer (declarative)             │  QML / XAML / React / Flutter widgets
│  - Decorative UI                    │
│  - User input                       │
│  - Animations, styling              │
└─────────────────────────────────────┘
           ↕ (bindings, signals)
┌─────────────────────────────────────┐
│  Bridge Layer (adapter)             │  Bridge models, view models
│  - QAbstractListModel (Qt)          │
│  - ViewModel (MVVM)                 │
│  - Platform channels (Flutter)      │
└─────────────────────────────────────┘
           ↕ (method calls, events)
┌─────────────────────────────────────┐
│  Core Layer (business logic)        │  Pure native code (C++, Rust, etc.)
│  - Domain entities                  │
│  - Business rules                   │
│  - Data access                      │
│  - External integrations            │
└─────────────────────────────────────┘
~~~

Зависимости строго однонаправленные:

- UI → Bridge → Core
- Core никогда не знает про Bridge или UI
- Bridge никогда не знает про UI

## Почему три слоя (не два)

Прямой call из UI в Core technically возможен, но проблемный:

### Типы данных не совпадают

Core оперирует native types (std::string, std::vector, custom classes). UI работает с типами которые понимает его framework (QVariant для Qt, observable collections для XAML).

Bridge конвертирует между ними.

### Threading model отличается

Core часто работает в worker threads (network IO, heavy computation). UI строго single-threaded (main/UI thread).

Bridge обеспечивает thread-safe коммуникацию — events/signals пересекают границу правильно.

### Object lifecycle

UI framework управляет lifecycle своих objects (QML auto-deletes children, React components mount/unmount). Core управляет своим lifecycle.

Bridge — стабильная точка которая переживает UI reconstruction.

### Testability

Core тестируется без UI framework. UI можно тестировать с mock Bridge.

Без bridge — Core tightly coupled к UI framework, тестирование сложнее.

## Core layer

### Responsibilities

- Domain entities (business objects)
- Business logic (rules, use cases)
- Data access (database, file system)
- External integrations (API, protocols)
- No UI dependencies

### Зависимости Core

В зависимости от framework — допустимы некоторые base libraries из UI framework:

**Qt пример**:

- ✅ QtCore (QString, QByteArray, QThread, QJsonDocument) — базовые типы
- ✅ QtNetwork — для network operations
- ❌ QtQuick, QtWidgets — UI-specific
- ❌ Qt Quick Controls — widgets

**WPF пример**:

- ✅ .NET Standard libraries — base types
- ❌ PresentationCore, PresentationFramework — UI-specific

**Flutter пример**:

- ✅ dart:core, dart:io — base libraries
- ❌ package:flutter/material.dart, package:flutter/widgets.dart — UI-specific

### Правила Core

- Все сетевые операции — асинхронные (threads, isolates, tasks)
- Return types typed errors (std::expected, Result<T>, Either<L, R>)
- Не блокировать main thread
- No global state (dependencies injected)
- Testable в isolation (без bridge, без UI)

## Bridge layer

### Responsibilities

- Proxy данных Core → UI в UI-понятном формате
- Pass user actions UI → Core
- Thread marshalling (worker thread ↔ UI thread)
- Object lifecycle management

### Реализация по frameworks

**Qt + QML**:

Bridge — классы наследующие QObject с:

- `Q_PROPERTY` для bindings
- `Q_INVOKABLE` для методов вызываемых из QML
- Signals для notification UI об изменениях
- `QAbstractListModel` subclasses для list views

~~~cpp
class UserListModel : public QAbstractListModel {
    Q_OBJECT
    Q_PROPERTY(int count READ rowCount NOTIFY countChanged)

public:
    Q_INVOKABLE void refresh();

signals:
    void countChanged();
    void errorOccurred(QString message);

private:
    UserService* m_service;  // Core layer
    QList<User> m_users;
};
~~~

**WPF + MVVM**:

Bridge — ViewModel classes:

- `INotifyPropertyChanged` interface
- `ICommand` для user actions
- `ObservableCollection<T>` для lists

**Flutter + platform code**:

Bridge — platform channels + state management (Provider, Riverpod, Bloc):

- Method channels для async calls
- Event channels для streaming updates
- State management объекты как bridge

**Tauri**:

Bridge — Rust commands + invoke handler:

- `#[tauri::command]` функции
- Event emitters для async updates
- State management через `tauri::State`

### Правила Bridge

- **Тонкий слой** — только proxying данных, никакой business логики
- Не дублировать state — bridge держит view-specific state, Core держит source of truth
- Signals/events передаются по значению, не по reference — thread safety
- Lifecycle — bridge переживает Core operations (weak refs back to Core for async callbacks)

### Anti-patterns Bridge

**Business logic в Bridge**:

~~~cpp
// BAD — validation в bridge model
class UserFormModel {
    Q_INVOKABLE bool submit() {
        if (email.empty()) return false;  // ← business rule в bridge
        if (!email.contains('@')) return false;
        return service->createUser(email, name);
    }
};

// GOOD — validation в core, bridge просто proxies
class UserFormModel {
    Q_INVOKABLE void submit() {
        auto result = service->createUser(email, name);  // core validates
        if (!result) emit errorOccurred(result.error());
    }
};
~~~

**Прямое SQL в Bridge**:

~~~cpp
// BAD — bridge обращается к БД
class MessageListModel {
    void refresh() {
        auto messages = db.query("SELECT * FROM messages");  // ← bypassing core
        // ...
    }
};

// GOOD — bridge использует core service
class MessageListModel {
    void refresh() {
        service->fetchMessages([this](auto messages) {  // core handles
            updateItems(messages);
        });
    }
};
~~~

## UI layer

### Responsibilities

- Declarative UI definition
- User input (clicks, typing, gestures)
- Animations, transitions, styling
- Accessibility
- Localization rendering

### Правила UI

- **No business logic** — UI описывает что показать, не что делать
- **All strings through i18n** — `qsTr()`, localized strings
- **All colors/spacing through theme** — no hardcoded values
- **No raw data access** — UI binds to bridge models, не к Core
- **Lazy loading** для длинных списков

### Binding к Bridge

UI "биндится" к properties bridge объектов. Изменение bridge property → UI обновляется автоматически.

**Qt/QML**:

~~~qml
import QtQuick

ListView {
    model: userListModel  // bridge model
    delegate: Rectangle {
        Text { text: model.name }
    }
}

Connections {
    target: userListModel
    function onErrorOccurred(message) {
        errorDialog.show(message)
    }
}
~~~

**WPF/XAML**:

~~~xml
<ListView ItemsSource="{Binding Users}">
    <ListView.ItemTemplate>
        <DataTemplate>
            <TextBlock Text="{Binding Name}"/>
        </DataTemplate>
    </ListView.ItemTemplate>
</ListView>
~~~

**Flutter**:

~~~dart
Consumer<UserListProvider>(
  builder: (context, provider, child) {
    return ListView.builder(
      itemCount: provider.users.length,
      itemBuilder: (context, index) => Text(provider.users[index].name),
    );
  },
)
~~~

## Threading

### Проблема

Core выполняет тяжёлые operations в worker threads. UI обновляется только в main/UI thread. Bridge должен пересекать границу.

### Решение

**Qt подход** — Queued connections:

~~~cpp
connect(worker, &Worker::finished,
        bridge, &Bridge::onWorkerFinished,
        Qt::QueuedConnection);
~~~

Queued connection — signal из worker thread поставлен в event queue main thread, обработан там.

**Dispatcher подход (WPF, Flutter)**:

~~~cpp
// Worker thread
auto result = heavyComputation();

Application::Current->Dispatcher->Invoke([=]() {
    bridge->UpdateState(result);  // runs on UI thread
});
~~~

**Async/await подход**:

~~~cs
// ViewModel method
async Task LoadUsersAsync() {
    var users = await Task.Run(() => service.FetchUsers());  // worker
    // After await — обратно на UI thread automatically
    Users = new ObservableCollection<User>(users);
}
~~~

### Правила

- Heavy computation — в worker thread
- UI updates — always main thread
- Data passing между threads — immutable value types или thread-safe containers

## Testing

### Core — unit tests

Pure unit tests без UI framework. Mock для external dependencies.

~~~cpp
TEST(UserServiceTest, CreatesUser) {
    MockRepository mockRepo;
    UserService service(&mockRepo);

    auto result = service.createUser("test@example.com");

    EXPECT_TRUE(result.isOk());
}
~~~

### Bridge — integration tests

Tests что bridge правильно проксирует данные. Mock Core, проверка что signals emitted, properties updated.

### UI — QML tests / widget tests / ui tests

Tests declarative UI:

- Компонент показывает правильное содержимое из bindings
- User actions trigger expected bridge methods
- Visual states правильно отражают model states

### E2E — полный стек

Real Core, real bridge, real UI, automated tool driving. См. [autonomous-testing.md](autonomous-testing.md).

## Common issues

### Signal spam

Bridge emits слишком много signals → UI constantly re-renders.

Решение: batch updates, throttle signals, emit только при реальном изменении.

### Memory leaks через reference cycles

Bridge держит reference to Core, Core держит reference to Bridge callback — cycle.

Решение: weak references для back-pointers, explicit lifecycle management.

### Threading violations

UI update из worker thread → crash или undefined behavior.

Решение: strict threading model с compile-time или runtime checks. Testing under thread sanitizers.

### Business logic leaking в UI

Если bridge — anemic proxy, разработчик склонен писать logic в UI:

~~~qml
Button {
    enabled: userModel.balance > 0 && userModel.isActive  // ← бизнес-правило в UI
}
~~~

Решение: expose computed properties из bridge:

~~~cpp
Q_PROPERTY(bool canPlaceOrder READ canPlaceOrder NOTIFY canPlaceOrderChanged)

bool canPlaceOrder() const {
    return m_user.balance > 0 && m_user.isActive;  // в core или bridge
}
~~~

~~~qml
Button {
    enabled: userModel.canPlaceOrder  // ← declarative
}
~~~

### Partial class split для больших bridges

Bridge-класс разрастается (> 250 LOC header, > 700 LOC impl). Signs of God Object.

Решение: split impl на несколько .cpp files по functional groups:

~~~
AppController.h  (один header)
AppController.cpp               (базовые методы)
AppController_Startup.cpp       (startup logic)
AppController_Navigation.cpp    (navigation methods)
AppController_Sync.cpp          (sync operations)
~~~

Каждый .cpp — отдельная responsibility. Header один. Класс логически cohesive но физически split для maintainability.

## Эволюция паттерна

В сложных приложениях three-tier может эволюционировать:

- Добавление слоя abstractions (interfaces между Core и Bridge) для полной testability
- Выделение shared infrastructure в отдельный модуль
- Разделение Core на sub-layers (domain, application, infrastructure) — см. [layered-architecture.md](layered-architecture.md)

Базовый three-tier достаточен для большинства desktop/mobile приложений. Complex evolution — когда приложение переросло базовую структуру.
