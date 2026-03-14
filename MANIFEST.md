# PAPA Architecture Manifest
## Zero-Hallucination Development Philosophy

**Главное правило:** pl scan (знание) → pl audit (диагностика) → pl collect (точечное действие).
Никогда не угадываем — всегда спрашиваем БД.

## Три инструмента

- pl scan   — разведчик, пишет в architecture.db
- pl audit  — диагностик, находит проблемы
- pl collect — умный сборщик файлов для AI задач

## Workflow

Утром: pl scan → pl audit
Под задачу: pl collect --task 'описание' --files-only → в контекст AI
Вечером: pl scan --diff → pl audit --fix-suggest

## Модули

| Модуль | Статус |
|--------|--------|
| std/scan (pl scan + pl collect) | написан |
| std/studio/audit (pl audit) | запушен |
| std/search (Tavily→SearXNG→Meilisearch) | запушен |
| std/ai/researcher | не начат |
| std/voice (CWB) | не начат |
| std/knowledge (Obsidian) | не начат |
