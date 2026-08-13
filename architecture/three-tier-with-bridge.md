# Three-tier with Bridge — architectural pattern

A special case of layered architecture for desktop/mobile applications with native code + declarative UI. The middle layer (bridge) adapts the native world to the declarative one.

**When to apply**: Qt + QML, WPF + XAML with MVVM, Flutter with platform channels, Tauri (Rust + JS frontend), React Native bridge, Jetpack Compose with native state.

**When NOT to apply**: fullstack web apps (there backend/API/frontend have a different structure), pure backend services, CLI tools.

## Structure

Three layers with specific responsibilities:

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

Dependencies are strictly one-directional:

- UI → Bridge → Core
- Core never knows about Bridge or UI
- Bridge never knows about UI

## Why three layers (not two)

A direct call from UI to Core is technically possible, but problematic:

### Data types don't match

Core operates on native types (std::string, std::vector, custom classes). UI works with types its framework understands (QVariant for Qt, observable collections for XAML).

Bridge converts between them.

### Threading model differs

Core often runs in worker threads (network IO, heavy computation). UI is strictly single-threaded (main/UI thread).

Bridge ensures thread-safe communication — events/signals cross the boundary correctly.

### Object lifecycle

The UI framework manages the lifecycle of its objects (QML auto-deletes children, React components mount/unmount). Core manages its own lifecycle.

Bridge is a stable point that survives UI reconstruction.

### Testability

Core is tested without the UI framework. UI can be tested with a mock Bridge.

Without a bridge — Core is tightly coupled to the UI framework, testing is harder.

## Core layer

### Responsibilities

- Domain entities (business objects)
- Business logic (rules, use cases)
- Data access (database, file system)
- External integrations (API, protocols)
- No UI dependencies

### Core dependencies

Depending on the framework — some base libraries from the UI framework are acceptable:

**Qt example**:

- ✅ QtCore (QString, QByteArray, QThread, QJsonDocument) — base types
- ✅ QtNetwork — for network operations
- ❌ QtQuick, QtWidgets — UI-specific
- ❌ Qt Quick Controls — widgets

**WPF example**:

- ✅ .NET Standard libraries — base types
- ❌ PresentationCore, PresentationFramework — UI-specific

**Flutter example**:

- ✅ dart:core, dart:io — base libraries
- ❌ package:flutter/material.dart, package:flutter/widgets.dart — UI-specific

### Core rules

- All network operations are asynchronous (threads, isolates, tasks)
- Return types are typed errors (std::expected, Result<T>, Either<L, R>)
- Don't block the main thread
- No global state (dependencies injected)
- Testable in isolation (without bridge, without UI)

## Bridge layer

### Responsibilities

- Proxy data Core → UI in a UI-understandable format
- Pass user actions UI → Core
- Thread marshalling (worker thread ↔ UI thread)
- Object lifecycle management

### Implementation by framework

**Qt + QML**:

Bridge — classes inheriting QObject with:

- `Q_PROPERTY` for bindings
- `Q_INVOKABLE` for methods callable from QML
- Signals for notifying UI of changes
- `QAbstractListModel` subclasses for list views

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
- `ICommand` for user actions
- `ObservableCollection<T>` for lists

**Flutter + platform code**:

Bridge — platform channels + state management (Provider, Riverpod, Bloc):

- Method channels for async calls
- Event channels for streaming updates
- State management objects as bridge

**Tauri**:

Bridge — Rust commands + invoke handler:

- `#[tauri::command]` functions
- Event emitters for async updates
- State management through `tauri::State`

### Bridge rules

- **Thin layer** — only proxying data, no business logic
- Don't duplicate state — bridge holds view-specific state, Core holds the source of truth
- Signals/events passed by value, not by reference — thread safety
- Lifecycle — bridge outlives Core operations (weak refs back to Core for async callbacks)

### Bridge anti-patterns

**Business logic in Bridge**:

~~~cpp
// BAD — validation in bridge model
class UserFormModel {
    Q_INVOKABLE bool submit() {
        if (email.empty()) return false;  // ← business rule in bridge
        if (!email.contains('@')) return false;
        return service->createUser(email, name);
    }
};

// GOOD — validation in core, bridge just proxies
class UserFormModel {
    Q_INVOKABLE void submit() {
        auto result = service->createUser(email, name);  // core validates
        if (!result) emit errorOccurred(result.error());
    }
};
~~~

**Direct SQL in Bridge**:

~~~cpp
// BAD — bridge talks to the DB
class MessageListModel {
    void refresh() {
        auto messages = db.query("SELECT * FROM messages");  // ← bypassing core
        // ...
    }
};

// GOOD — bridge uses a core service
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

### UI rules

- **No business logic** — UI describes what to show, not what to do
- **All strings through i18n** — `qsTr()`, localized strings
- **All colors/spacing through theme** — no hardcoded values
- **No raw data access** — UI binds to bridge models, not to Core
- **Lazy loading** for long lists

### Binding to Bridge

UI "binds" to properties of bridge objects. Changing a bridge property → UI updates automatically.

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

### The problem

Core performs heavy operations in worker threads. UI updates only on the main/UI thread. Bridge must cross the boundary.

### The solution

**Qt approach** — Queued connections:

~~~cpp
connect(worker, &Worker::finished,
        bridge, &Bridge::onWorkerFinished,
        Qt::QueuedConnection);
~~~

Queued connection — the signal from the worker thread is placed on the main thread's event queue, handled there.

**Dispatcher approach (WPF, Flutter)**:

~~~cpp
// Worker thread
auto result = heavyComputation();

Application::Current->Dispatcher->Invoke([=]() {
    bridge->UpdateState(result);  // runs on UI thread
});
~~~

**Async/await approach**:

~~~cs
// ViewModel method
async Task LoadUsersAsync() {
    var users = await Task.Run(() => service.FetchUsers());  // worker
    // After await — automatically back on the UI thread
    Users = new ObservableCollection<User>(users);
}
~~~

### Rules

- Heavy computation — in a worker thread
- UI updates — always the main thread
- Data passing between threads — immutable value types or thread-safe containers

## Testing

### Core — unit tests

Pure unit tests without the UI framework. Mocks for external dependencies.

~~~cpp
TEST(UserServiceTest, CreatesUser) {
    MockRepository mockRepo;
    UserService service(&mockRepo);

    auto result = service.createUser("test@example.com");

    EXPECT_TRUE(result.isOk());
}
~~~

### Bridge — integration tests

Tests that the bridge correctly proxies data. Mock Core, verify signals emitted, properties updated.

### UI — QML tests / widget tests / ui tests

Tests for declarative UI:

- The component shows the right content from bindings
- User actions trigger expected bridge methods
- Visual states correctly reflect model states

### E2E — full stack

Real Core, real bridge, real UI, automated tool driving. See [autonomous-testing.md](autonomous-testing.md).

## Common issues

### Signal spam

Bridge emits too many signals → UI constantly re-renders.

Solution: batch updates, throttle signals, emit only on actual change.

### Memory leaks through reference cycles

Bridge holds a reference to Core, Core holds a reference to a Bridge callback — a cycle.

Solution: weak references for back-pointers, explicit lifecycle management.

### Threading violations

UI update from a worker thread → crash or undefined behavior.

Solution: a strict threading model with compile-time or runtime checks. Testing under thread sanitizers.

### Business logic leaking into UI

If bridge is an anemic proxy, developers tend to write logic in UI:

~~~qml
Button {
    enabled: userModel.balance > 0 && userModel.isActive  // ← business rule in UI
}
~~~

Solution: expose computed properties from the bridge:

~~~cpp
Q_PROPERTY(bool canPlaceOrder READ canPlaceOrder NOTIFY canPlaceOrderChanged)

bool canPlaceOrder() const {
    return m_user.canPlaceOrder();  // the rule itself lives in core; the bridge only exposes it
}
~~~

~~~qml
Button {
    enabled: userModel.canPlaceOrder  // ← declarative
}
~~~

### Partial class split for large bridges

The bridge class grows (> 250 LOC header, > 700 LOC impl). Crossing the threshold is a
**suspicion, not a verdict** ([core/quality-gates.md](../core/quality-gates.md) §LOC): either give a
reasoned "it does one thing, here's why" — a `Q_PROPERTY` facade's header is inherent surface, cap
it with a documented ceiling instead of a mechanical cut (see `stack/cpp-qt.md`) — or split.

For a genuine God Object, split the impl across several .cpp files by functional groups:

~~~
AppController.h  (one header)
AppController.cpp               (base methods)
AppController_Startup.cpp       (startup logic)
AppController_Navigation.cpp    (navigation methods)
AppController_Sync.cpp          (sync operations)
~~~

Each .cpp is a separate responsibility. One header. The class is logically cohesive but physically split for maintainability.

## Evolution of the pattern

In complex applications, three-tier can evolve:

- Adding a layer of abstractions (interfaces between Core and Bridge) for full testability
- Extracting shared infrastructure into a separate module
- Splitting Core into sub-layers (domain, application, infrastructure) — see [layered-architecture.md](layered-architecture.md)

The base three-tier is sufficient for most desktop/mobile applications. Complex evolution — when the application has outgrown the base structure.
