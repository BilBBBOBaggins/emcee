# Autonomous Testing — architecture pattern

A pattern for automating UI testing via an **IPC server embedded in the application**, letting tests drive the application like a real user through an external tool.

The pattern works and enables autonomous UI testing for AI agents — critical when automated gate tests (unit, integration) can't verify real UI behavior.

**Applicable to**: desktop apps (Qt, WPF, Tauri), mobile apps (Flutter, native), any UI-heavy applications where E2E automation via browser (Selenium, Playwright) doesn't apply.

**Not applicable to**: web apps (Playwright and similar solve the problem for them), headless services.

## The problem it solves

Automated gates (unit, integration) cover code in isolation. But gaps happen **between layers**:

- A UI button isn't wired to its handler
- A signal from the backend doesn't propagate to the model
- The model updates but the UI doesn't redraw
- An action triggers the right call, but the response isn't handled

Unit tests don't catch these problems — they mock neighboring layers. Manual testing catches them, but doesn't automate.

Autonomous testing — UI-driven tests with the full stack **without** a human in the loop. An AI agent can run a test, check the result, diagnose the problem.

## Basic architecture

~~~
┌──────────────────────┐
│  Test Script         │  (Python, JS, etc.)
│  (external)          │
└──────────────────────┘
           ↕ JSON-RPC / similar
┌──────────────────────┐
│  Application         │
│  ┌─────────────────┐ │
│  │  TestDriver     │ │  IPC server inside the application
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

TestDriver — a component inside the application that:

- Opens an IPC endpoint (socket, named pipe, HTTP)
- Accepts commands via a standardized protocol
- Performs actions on UI elements
- Returns the UI state in a structured format

External test script:

- Connects to the IPC endpoint
- Sends a sequence of commands
- Checks results
- Saves screenshots, logs, traces

## Activating TestDriver

TestDriver is enabled **only in a special build** or via a runtime flag.

### Compile-time flag

~~~cpp
#ifdef ENABLE_TEST_DRIVER
    testDriver = new TestDriver(this);
    testDriver->start();
#endif
~~~

Build:

~~~bash
cmake -B build-qa -DENABLE_TEST_DRIVER=ON
~~~

Production builds — TestDriver is absent, no security risk.

### Runtime flag

~~~cpp
if (commandLine.contains("--test-mode")) {
    testDriver = new TestDriver(this);
    testDriver->start();
}
~~~

Launch:

~~~bash
./MyApp --test-mode
~~~

More flexible, but a security concern — need to make sure the flag isn't accidentally activated in production.

### Isolation via a separate build

Recommended — TestDriver in a separate build directory, not in the production build.

- Production: `build/` — without TestDriver
- Testing: `build-qa/` — with TestDriver

Prevents accidental deployment.

## IPC protocol

### Requirements

- Simple to debug
- Typed commands with validation
- Async-friendly (the application doesn't block waiting for a response)
- Language-agnostic (test scripts in different languages)

### JSON-RPC 2.0

The recommended choice. Standardized, typed, async.

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

- **Local socket** (Unix socket, named pipe) — for same-machine tests. Fast, simple
- **TCP localhost** — if cross-process communication is needed
- **WebSocket** — if tests run in a browser or remotely

For most cases, a local socket is optimal.

### Framing

Newline-delimited JSON — one message per line. Simple parsing.

For large payloads — length-prefixed frames.

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
clickIndex(listObjectName, index)  — click on a list element
~~~

### Property access

~~~
getProperty(objectName, propertyName)
setProperty(objectName, propertyName, value)
getModel(modelName)  — the whole model state
getModelCount(modelName)
~~~

### Waiting and verification

~~~
exists(objectName) → bool
isVisible(objectName) → bool
waitForObject(objectName, timeout)  — waits for it to appear
waitForProperty(objectName, property, expectedValue, timeout)
~~~

### Visual

~~~
screenshot() → image path
screenshotObject(objectName) → image path
~~~

### State inspection

~~~
state() — snapshot of the whole UI tree
modelState() — ground truth data model
diff(previousState) — what changed
~~~

### Application control

~~~
getAppState() — high-level app state
resetState() — clear all data, return to clean state
waitForSync() — waits for background operations to finish
invoke(method, args) — direct method call (for setup/teardown)
~~~

### External integration

For testing integrations with external services:

~~~
externalCheck(params) — check data on the server
externalPut(params) — create data on the server (for server→client tests)
externalDelete(params)
~~~

## Object identification

A test must find a UI element to interact with. Options:

### By object name

Every interactable element has a unique `objectName`:

~~~qml
Button {
    objectName: "syncButton"
    text: "Send"
}
~~~

~~~python
driver.click("syncButton")
~~~

Recommended — explicit, controlled, survives refactoring.

### By accessibility properties

Using accessible name, role, etc.:

~~~python
driver.click(role="button", name="Send")
~~~

Pros: aligns with accessibility testing. Cons: less controlled, can break on UI changes.

### By path

Tree-based identification:

~~~python
driver.click("/mainWindow/sidebar/syncButton")
~~~

Fragile — breaks when the UI hierarchy changes. Use only when necessary.

## Context properties access

For bridge models (which don't live in the UI tree):

~~~python
driver.get_property("@messageModel", "count")
driver.get_model("@userModel")
~~~

The `@` prefix indicates a context property.

## Test scenarios

### Format

Scenarios in JSON (or YAML) — declarative, easy to generate, easy to inspect:

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

The test runner reads the scenario, executes steps sequentially, saves outcomes.

### Generation

AI agents can **generate scenarios** from test cases (written by QA UAT). Acceptance criteria in Given/When/Then → scenario steps.

## Integration with the AI-agent workflow

TestDriver — a critical part for autonomous AI-driven development.

### Loop

1. The agent writes code
2. The agent runs a scenario test via TestDriver
3. TestDriver returns the state after each step
4. The agent analyzes the state — expected vs actual
5. If there's a gap — the agent diagnoses the cause (reads code, logs, state)
6. The agent writes a fix, repeats the loop

### Key principle: state comparison

The agent compares the UI state with the expected state in a structured format, not via screenshots.

**Preferred flow**:

1. The agent requests `state()` — structured JSON
2. Compares it with the expected JSON
3. Finds the diff

**Fallback**:

4. If JSON isn't sufficient — screenshot for visual inspection
5. Analyze the screenshot (if needed)

Screenshots — expensive (visual analysis via VLM), use sparingly. JSON state — cheap and precise.

### Rules for the agent

- Analyze state/JSON first
- Screenshot only when JSON shows an anomaly and visual understanding is needed
- Maximum 1 screenshot at a time, don't accumulate
- If a test fails 3 times after fixes — stop, describe the problem
- Don't change public core/bridge APIs without confirmation
- Don't change architectural decisions
- One commit = one fix — granularity for whoever owns the commit: in the human-in-the-loop default
  the agent prints the command and the user commits (PR-NN-02); the agent itself commits only in an
  autonomous run / under a guide-assigned commit
  ([core/task-protocol.md](../core/task-protocol.md) → "Commit commands")

## Test accounts and data

E2E tests require real data. Fixed test accounts — the best approach:

| Account | Data volume | Purpose |
|---------|------------|---------|
| heavy | huge | stress tests |
| medium | medium | typical case |
| small | small | fast tests |
| empty | empty | edge case |

Each test specifies which accounts it needs. Minimum in a run — 3 accounts of different types.

Accounts don't change between runs — reproducibility.

## Observations and assertions

### What to observe

- Visible UI state (elements, text, images)
- Internal model state (data in bridge models)
- External state (data on the server, files in the filesystem)
- Changes over time (what happened after an action)

### Verification levels

**L1 — UI**: a button appeared, text was displayed. Fast but may miss semantic issues.

**L2 — Model**: the bridge model has the expected data. A deeper check.

**L3 — External**: the data reached the server / DB. The most complete check.

Good tests use all three levels — action → L1 check → L2 check → L3 check → (optionally) back to L1 after sync.

### 4-step pattern

For each test:

~~~
1. ACTION via UI (click, type, etc.)
2. IMMEDIATE VISUAL RESULT (toast, dialog, state change)
3. REAL RESULT (data on the external system)
4. UI IN SYNC WITH SERVER (the UI hasn't rolled back, the UI reflects server state)
~~~

Step 4 catches two types of bugs:

- **UI rolled back**: an optimistic update was reverted after a server failure
- **UI froze**: the server updated, but the UI didn't re-read

All 4 steps are mandatory. Details — see [roles/qa-e2e.md](../roles/qa-e2e.md).

## Implementation specifics

### Thread safety

TestDriver receives commands on a separate thread, but UI operations must run on the main thread.

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

`BlockingQueuedConnection` — the caller waits for execution to complete. Important for deterministic testing.

### Finding objects

Recursive search in the object tree:

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

For QML — specifics: context properties, repeater instances, loaders.

### State serialization

The `state()` command returns a JSON representation of the UI tree:

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

## Limitations

### What TestDriver doesn't replace

**Unit tests** — fast, isolated, plentiful. TestDriver — slow, integrated, few. Different concerns.

**Visual testing** — pixel-perfect verification of visual correctness. Screenshot comparison tools for that.

**Performance testing** — TestDriver adds overhead, misleading for perf tests.

**Manual exploratory testing** — a human is better at finding unexpected issues.

### Maintenance

TestDriver — infrastructure code that requires maintenance:

- Adding new commands as the application grows
- Maintenance during major UI changes
- Documentation for new team members

Invest in it proportionally to the project's size.

## Evolution from manual to autonomous

For an existing project — a gradual approach:

1. **Manual E2E tests first** — via a human tester or Selenium/Playwright if it's a web app
2. **Semi-autonomous** — TestDriver commands, but test scenarios written by humans
3. **Autonomous** — AI agents generate and execute scenarios on demand
4. **Self-healing** — agents not only test but also report issues + suggest fixes

Each step — an investment. Start simple, evolve by demonstrated need.
