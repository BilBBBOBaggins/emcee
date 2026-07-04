# EN translation glossary — emcee canon

Frozen terminology for the RU→EN migration. Every translation subagent MUST use these
renderings consistently. When a term below appears in the source, use exactly the EN form
given — do not improvise synonyms (no "protocol"/"ruleset" where "regimen" is fixed, etc.).

## Style rules

1. **Translate, don't paraphrase.** Agent-facing files (`core/`, `roles/`, entry files) are
   deliberately dense — preserve the density and the normative force. "Запрещено" = "forbidden",
   not "discouraged". "Обязан" = "must", not "should".
2. **Preserve untouched:** code blocks, file paths, `{{placeholders}}`, `<<SENTINELS>>`,
   role names in tables, command grammar (`R D T`, `/kickoff`, `/panel`, `N`), proper nouns
   (Claude Code, Codex, emcee, Master of Ceremonies, GitHub), artifact names
   (`day-<N>-guide.md`, `PROJECT-STATE.md`, `MVP-SCOPE-FREEZE.md`), gate IDs (`QG-NN-05`),
   ADR numbers, Given/When/Then.
3. **Markdown anchors:** when a header is translated, update every in-file and cross-file
   anchor link to the new slug (e.g. `#как-пользоваться` → `#how-to-use`). Verify no anchor
   link is left pointing at a Russian slug.
4. **Voice:** Russian «ты»-form instructions → English imperative ("заполни" → "fill in").
   Keep second person where the source addresses the user ("ваш проект" → "your project").
5. **Do not add content.** No explanatory asides, no softening, no new examples. 1:1 semantic
   fidelity; sentence structure may be anglicized freely.

## Term table (RU → EN, frozen)

| RU | EN |
|---|---|
| регламент | regimen |
| входной файл регламента | regimen entry file |
| обвязка (исполняемая, `.claude/`) | executable wiring |
| роль | role |
| дормантная роль | dormant role |
| день | day |
| гайд дня | day guide |
| срез (роадмапа) | slice |
| гейт | gate |
| mechanical / accountability гейты | mechanical / accountability gates |
| несущее (решение, правило) | load-bearing |
| адверсивная панель / состязательная панель | adversarial panel |
| red-team / blue-team / arbiter | red team / blue team / arbiter (unchanged) |
| вторая модель | second model |
| прозовый режим | prose mode |
| числовые команды | numeric commands |
| маппинг ролей | role map |
| контракт-первый цикл (C+) | contract-first cycle (C+) |
| спецификация / спека | spec |
| пользовательские сценарии | user scenarios |
| тест-кейсы | test cases |
| приёмка | acceptance |
| заморозка объёма / замороженный scope | scope freeze / frozen scope |
| достижимость (фичи) в сборе | assembled reachability |
| точка сборки | composition root |
| самотест | self-test |
| висячая ссылка | dangling link |
| плейсхолдер | placeholder |
| дрейф (план/реальность) | drift (plan vs. reality) |
| «снимок, а не журнал» | "a snapshot, not a journal" |
| owned-долг (версионный долг) | owned debt (versioned maintenance debt) |
| solo-collapse / схлопывание ролей | solo-collapse |
| холистический аудит | holistic audit |
| конституция | constitution |
| протокол сверки preflight/exit | preflight/exit check protocol |
| правило трёх попыток | three-attempt rule |
| «факт, не гипотеза» | "fact, not hypothesis" |
| качество важнее экономии токенов (north star) | quality over token economy (north star) |
| «зелёные тесты ≠ фича подключена» | "green tests ≠ wired feature" |
| разведка / производство (отделение) | reconnaissance vs. production (separation of) |
| дискавери | discovery |
| доменный эксперт | domain expert |
| кикстарт | kickstart |
| роутер (скиллов, регламентов) | router |
| перенос / переносимость | porting / portability |
| рантайм / харнесс | runtime / harness |
| оверлей (codex-оверлей, process-overlay) | overlay |
| генератор | generator |
| скелет (stack-файла) | skeleton |
| вычитка (адверсивная) | (adversarial) review pass |
| ре-план / репланинг | replanning |
| статус дня | day status |
| задача дня | day task |
| «Промпт для Claude Code» (метка блока) | "Prompt for Claude Code" |
| «После выполнения» | "After completion" |
| «Коммит» | "Commit" |
| «Обязательно читать» | "Required reading" |
| «По ситуации» | "Situational" |
| «Маппинг ролей» | "Role map" |
| раскрытие (фаза опроса, ADR-013) | divergence (phase) |
| схождение / «подтверждение» (фаза опроса, ADR-013) | convergence (phase) |
| «Опрос пользователя» (секция task-protocol) | "User Q&A" |
| фазы-контракты | phase contracts |
| Depth-тиры | depth tiers |
| «Ручной рецепт» | "Manual recipe" |
| «Основной путь» | "Main path" |
| «первый километр» (ADR-003) | "first kilometer" |
| ФЗ-152 | Russia's Federal Law No. 152-FZ (expand on first use) |
| энфорсмент | enforcement |
| «Коротко» (секция ADR) | "In short" |
| «Контекст» (секция ADR) | "Context" |
| «Решение» (секция ADR) | "Decision" |
| «Последствия» (секция ADR) | "Consequences" |
| «Альтернативы (отклонены)» (секция ADR) | "Alternatives (rejected)" |
| «Формат вызова» (секция ролей) | "Invocation format" |
| «Чистая сборка» (секция stack-файлов) | "Clean build" |
| «Специфика проекта» | "Project specifics" |
| «Эволюция этого документа» | "Evolution of this document" |
