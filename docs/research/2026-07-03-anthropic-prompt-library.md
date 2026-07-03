# Библиотека промптов Anthropic → что применимо в emcee

**Источник:** <https://code.claude.com/docs/en/prompt-library> (стянуто 2026-07-03).
**Статус: принято и внесено 2026-07-03** — §1 (чеклист промпта → architect.md) и все пункты §2
(coverage → стаб стека + go/python/react-nextjs + qa-e2e/developer; self-check UI → developer.md;
git-археология → auditor.md; захват сессии → core/memory.md). Решение оператора.
Это 52 копипаст-промпта для Claude Code, собранных Anthropic из Common workflows, Best practices,
«How Anthropic teams use Claude Code» и enterprise-гайда. Каждый промпт снабжён разбором
«Why this works». Аудитория — пользователь, который вводит промпты руками; emcee — регламент,
который большинство этих паттернов уже институционализирует ролями и гейтами. Поэтому извлекаемая
ценность — не сами промпты, а **паттерны их устройства** и несколько точечных приёмов.

---

## 1. Главный актив: шесть мета-паттернов промпта

Раздел «What makes these prompts work» — свод того, что делает промпт эффективным. Дословно:

1. **Опиши исход, не шаги** («add rate limiting to the public API and make sure existing tests
   still pass») — модель сама находит файлы.
2. **Дай способ самопроверки в том же промпте** («write the migration, run it against the dev
   database, and confirm the schema matches») — агент итерирует сам, а не останавливается после
   первой попытки.
3. **Укажи на образец** («add a settings page that follows the same layout as the profile page») —
   без референса модель падает в «общие best practices», с референсом — в конвенции проекта.
4. **Назови измеримую цель** («get the bundle size under 200KB and show me what you removed») —
   однозначное определение done.
5. **Дай артефакт, не пересказ** («why is the build failing? @build.log») — модель читает
   первоисточник, а не твоё описание первоисточника.
6. **Скажи, в каком виде нужен ответ** (формат, длина, аудитория).

**Куда в emcee:** architect — единственный «автор промптов» пакета (блок «Промпт для Claude Code»
в гайдах дня). Сейчас в [roles/architect.md](../../roles/architect.md) §«Разбивка следующего
среза» единственное правило качества промпта — «конкретен и однозначен». Предложение: добавить
туда чеклист из паттернов 2–6 (самопроверка в том же промпте; ссылка на существующий образец в
кодовой базе; измеримая цель; артефакт вместо пересказа; формат ожидаемого выхода).

Оговорка по паттерну 1: он для интерактивного пользователя. В emcee промпт для developer
**намеренно** точный (developer не принимает архитектурных решений) — «исход, не шаги» применим
на уровне контракта («что»), а не как размывание ТЗ.

---

## 2. Точечные приёмы, которых в пакете нет

| Промпт библиотеки | Суть | Куда в emcee |
|---|---|---|
| **fill-gaps-from-a-coverage-report** | «read coverage-summary.json and add tests for the lowest-covered files until each is above N%» — цели по тестам от фактического отчёта покрытия, не от ощущения | приём для qa-e2e/developer; опционально упоминание в [core/quality-gates.md](../../core/quality-gates.md) как способ находить дыры (не как самоцель-метрику) |
| **implement-from-a-screenshot** | «implement this design, then take a screenshot, compare to the original, and fix differences» — визуальный self-check-цикл | [roles/developer.md](../../roles/developer.md): цикл верификации на этапе **реализации** UI (designer в emcee только производит вайрфрейм, морду реализует developer); картинка — эталон сравнения, не источник кода; средство рендера — `origin: harness` |
| **trace-how-code-evolved** | «look through the commit history of {path} and summarize how it evolved and why» — git-археология для вопроса «почему», а не «что» | явный приём в [roles/auditor.md](../../roles/auditor.md) (вход в чужой/старый проект); частично уже покрыто «git = searchable холодная память» в task-protocol |
| **capture-what-to-remember** | «summarize what we did this session and suggest what to add to CLAUDE.md» — ручной захват знаний в конце сессии | [core/memory.md](../../core/memory.md): как ручное дополнение к PreCompact-хуку (хук пишет recovery-чекпойнт, но не смысловое «что добавить в регламент») |
| **see-what-depends-on** | «what would break if I deleted {target}?» — оценка blast radius до удаления | микро-приём для developer/architect при refactor-задачах; кандидат в architect-чеклист разбивки |

---

## 3. Уже покрыто регламентом (карта соответствия)

Подтверждение дизайна: библиотека независимо сходится к тем же паттернам, что зашиты в emcee —
в большинстве случаев emcee строже.

| Промпт библиотеки | Эквивалент в emcee | Кто строже |
|---|---|---|
| draft-a-spec-by-interview («interview me… then write SPEC.md») | sa.md §Discovery (Socratic-опрос) + ADR-013 раскрытие/схождение | emcee: по одному вопросу, фазы формы вопроса |
| map-edge-cases-before | sa.md §Edge cases, ba.md (сценарии-edge), qa-uat.md | паритет |
| drive-implementation-from-tests | core/spec-driven.md (цикл C+) | emcee: независимый автор тестов + адверсивная вычитка |
| review-your-changes («reads changed files in full, not just diff») | reviewer.md: «читай каждый затронутый файл целиком» + авторитетный diff от диспетчера | emcee |
| run-a-security-review (субагент в своём контексте) | hardware-scoped reviewer, security-блок ревью | emcee |
| fix-a-build-error (root cause + verify) | core/debugging.md (запрет угадывания) + debugger.md (минимальный фикс + regression test) | emcee |
| investigate-a-production-incident («correlate evidence sources, not steps») | core/debugging.md: одновременный сбор логов со всех слоёв цепочки | паритет |
| optimize-against-a-measurable | философия quality-gates: измеримое done | паритет |
| work-an-issue-end-to-end («give the number, not a summary») | task-protocol «Вход в сессию»: роль читает гайд сама, не пересказ | паритет |
| follow-an-existing-pattern | developer.md: «используй существующие паттерны из кодовой базы» | паритет (но в architect-чеклист стоит добавить явно — §1) |
| turn-a-correction-into-a-rule (правка → правило в CLAUDE.md) | CLAUDE.md §«Эволюция этого документа» | паритет |
| turn-a-recurring-task-into-a-skill | core/skills.md (quality-bar «когда заводить») | emcee: есть анти-триггеры When-NOT |
| commit-with-a-generated-message | task-protocol §Команды коммита | emcee: агент не коммитит; формат из гайда |
| plan-a-multi-file («plan, don't edit yet») | разделение ролей: architect не пишет код | emcee: институционализировано аппаратно (нет Edit) |
| scope-a-change-before («which files to touch») | гайд дня: «Задача T — что и где (затронутые файлы)» | паритет |
| get-oriented / ask-the-codebase | architect вход в день N (читает весь проект, статус) | паритет |
| course-correct / narrow-the-scope (steer) | task-protocol §Протокол при неоднозначности + exit-отчёты | другая механика: emcee предотвращает, библиотека чинит постфактум |

## 4. Не применимо к пакету

Одноразовые user-facing промпты вне регламента разработки: meeting→tickets, маркетинговые вариации
из ads-CSV, анализ data-файла, диагностика по скриншоту облачной консоли, query-logs через MCP,
обновление копирайта по кодбазе, «собери internal tool на vanilla JS», подключение MCP-серверов.
Release notes из git-истории и CI-workflow покрываются devops-ролью ad-hoc — отдельного правила
не нужно.

---

## 5. Полный каталог (52 промпта, сжато)

Формат: **título** — промпт (суть «why it works»). `{x}` — слоты для подстановки.

### Discover
- **Get oriented in a new repository** — "give me an overview of this codebase: architecture, key directories, and how the pieces connect" (описывай, что хочешь узнать, не какие файлы читать).
- **Explain unfamiliar code** — "explain what {path} does and how data flows through it. write it up as {format}" (назови файл и формат ответа).
- **Find where something happens** — "where do we {behavior}?" (поиск по поведению, не по имени файла).
- **Check what breaks before you delete** — "what would break if I deleted {target}?" (blast radius до удаления).
- **Trace how code evolved** — "look through the commit history of {path} and summarize how it evolved and why" (история — для вопроса «почему»).
- **Scope a change before you start** — "which files would I need to touch to {change}?" (оценка размера до роадмапа).
- **Ask the codebase a product question** — "I am a {role}. walk me through what happens when a user {action}" (назови роль — ответ на нужном уровне).

### Design
- **Plan a multi-file change** — "plan how to refactor {target} to {goal}. list the files you would change, but don't edit anything yet" («don't edit yet» отделяет разведку от правок).
- **Draft a spec by interview** — "I want to build {feature}. interview me about implementation, UX, edge cases, and tradeoffs until we have covered everything, then write the spec to SPEC.md" (модель интервьюирует тебя, не наоборот).
- **Turn a meeting into tickets** — "read {notes} and write up the action items, then create a {tracker} ticket for each with acceptance criteria".
- **Map edge cases before building** — "list the error states, empty states, and edge cases for {feature} that the design needs to cover" (спроси про отсутствующее, не про существующее).
- **Turn a mockup into a working prototype** — "here is a mockup. build a working prototype I can click through, matching the layout and states shown".
- **Implement from a screenshot and self-check** — "implement this design, then take a screenshot of the result, compare it to the original, and fix any differences" (цикл верификации без человека).

### Build
- **Follow an existing pattern** — "look at how {example} is implemented to understand the pattern, then build {new} the same way" (референс > общие best practices).
- **Generate docs for undocumented code** — "find {scope} without {format} comments and add them, matching the style already used in the file".
- **Add a small, well-defined feature** — "add a {endpoint} endpoint that returns {payload}" (входы/выходы, не «как строить»).
- **Build a small internal tool** — "create a {tool} using HTML, CSS, and vanilla JavaScript, then open it in my browser".
- **Work an issue end to end** — "read issue #{issue}, implement the fix, and run the tests" (номер тикета, не пересказ).
- **Find and update copy across the codebase** — "find every place we say '{copy}' or a close variant… update to '{new}'. leave tests and the changelog alone" (проси варианты и называй исключения).
- **Draft a document from past examples** — "read the {examples} in {folder} to learn the structure and voice, then draft a new one for {topic}".
- **Write tests, run them, fix failures** — "write tests for {path}, run them, and fix any failures" (write+run+fix в одном промпте = самостоятельная итерация).
- **Drive implementation from tests** — "write tests for {feature} first, then implement it until they pass".
- **Fill gaps from a coverage report** — "read {report} and add tests for the lowest-covered files until each is above {target}%" (цели от фактических цифр).
- **Migrate a pattern across the codebase** — "migrate everything from {from} to {to}: identify every place that needs to change, then make the changes" (сначала перечисли — проверяемость).
- **Port code to another language** — "port {source} to {target}, keeping the same {keep}" (назови, что сохранить — это контракт проверки).
- **Optimize against a measurable target** — "optimize {target} to bring {metric} from {current} down to under {goal}".
- **Fix a precise visual bug** — "the {element} extends {amount} beyond the {container} on {viewport}. fix it." (точный вход → точный фикс).
- **Review your changes before commit** — "review my uncommitted changes and flag anything that looks risky before I commit" (читает файлы целиком, не только diff).
- **Review a pull request** — "review PR #{pr} and summarize what changed, then list any concerns" (ревью со всей кодбазой в контексте).
- **Review infrastructure changes** — "here is my Terraform plan output. what is this going to do, and is anything here going to cause problems?".
- **Run a security review with a subagent** — "use a subagent to review {path} for security issues and report what it finds" (аудит в отдельном контексте).
- **Catch issues before formal review** — "review {file} for {concerns} and list anything I should fix before it goes to {reviewer}" (назови проверяемые риски).
- **Course-correct a wrong approach** — "that is not right: {feedback}. try a different approach" (назови нарушенное ограничение, не просто «неправильно»).
- **Narrow the scope of a change** — "that is too much. keep only the changes to {scope} and undo your other edits" (граница вместо полного отката).
- **Turn a correction into a rule** — "you keep {mistake}. add a rule to CLAUDE.md so this stops happening".

### Ship
- **Resolve merge conflicts** — "resolve the merge conflicts in this branch and explain what you kept from each side" (просить обоснование = ревьюируемый merge).
- **Commit with a generated message** — "commit these changes with a message that summarizes what I did".
- **Open a pull request from a ticket** — "find the {tracker} ticket about {topic} and open a PR that implements it".
- **Draft release notes from git history** — "compare {v1} to {v2} and draft release notes grouped by feature, fix, and breaking change".
- **Write a CI workflow** — "write a GitHub Actions workflow that {steps} on every push to {branch}".

### Operate
- **Find and fix a failing test** — "the {test} test is failing, find out why and fix it" (симптом, не диагноз).
- **Investigate a reported error** — "users are seeing {symptom} on {where}. investigate and tell me what is going on".
- **Fix a build error at the root** — "here is a build error. fix the root cause and verify the build succeeds" (root cause + verify против поверхностных заплаток).
- **Investigate a production incident** — "{symptom}. check the logs, recent deploys, and config changes, then tell me the most likely cause" (перечисли источники улик, не шаги).
- **Diagnose from a console screenshot** — "here is a screenshot of {console}. walk me through why {resource} is failing and give me the exact commands to fix it".
- **Query logs in plain English** — "show me all {events} for {scope} over {timeframe}. write the query, run it, and tell me what stands out" (показывает и запрос, и результат).
- **Analyze a data file** — "read {file}, summarize the key patterns, and write the results to {output}".
- **Generate variations from performance data** — "read {file}, find the underperforming {items}, and generate {n} new variations that stay under {limit} characters".
- **Turn a recurring task into a skill** — "create a /{name} skill for this project that {steps}".
- **Add a hook for repeat behavior** — "write a hook that {action} after every {event}".
- **Connect a tool with MCP** — "set up the {server} MCP server so you can read my {data} directly".
- **Capture what to remember for next time** — "summarize what we did this session and suggest what to add to CLAUDE.md" (спроси до того, как забыл — модель знает, что ей пришлось выяснять).
