# docs/evidence — эмпирическая база решений

Здесь лежат **верифицируемые артефакты**, на которые ссылаются ADR и `core/`-доки как на
несущую истину (живые тесты рантаймов, выводы арбитра панели). Раньше они жили в gitignored
`scratchpad/panel/` — но цитировать как авторитет можно только то, что есть в git и переживает
свежий клон. Перенесены сюда в рамках аудита 2026-06-29 (находка #1).

| Файл | Что это | Кто ссылается |
|------|---------|---------------|
| [g2-findings.md](g2-findings.md) | Эмпирика живого `codex 0.138.0` (песочница, G2, KL-7) — основа матрицы гарантий | [core/portability.md](../../core/portability.md), [overlays/codex/README.md](../../overlays/codex/README.md) |
| [runtime-capability-map.md](runtime-capability-map.md) | Фактическая карта возможностей рантаймов (Claude Code / Codex) | ADR-010, [overlays/codex/README.md](../../overlays/codex/README.md) |
| [p4form-arbiter.md](p4form-arbiter.md) | Вердикт арбитра панели по форме оверлеев (обоснование стоп-условия move-later) | [overlays/README.md](../../overlays/README.md) |

Это **исторические свидетельства** (snapshot на момент написания), не живой регламент. Правит их
только тот, кто перезапускает соответствующую верификацию.
