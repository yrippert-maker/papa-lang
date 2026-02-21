# PAPA Lang — AI Development Guidelines

## Инфраструктура (обновлено)

### Серверы
| Сервис | URL | Хостинг |
|--------|-----|---------|
| Gitea | git.papa-ai.ae | DigitalOcean |
| PAPA DevOps | papa-ai.ae | DigitalOcean |
| n8n | n8n.papa-ai.ae | DigitalOcean |
| PAPA Lang Site | lang.papa-ai.ae | DigitalOcean |
| КЛГ АСУТК | 158.160.22.166:3000 | Yandex Cloud |

### AI Провайдеры
| Provider | Роль | Модель |
|----------|------|--------|
| Claude | Primary | claude-sonnet-4-5 |
| GPT | Fallback 1 | gpt-4o |
| Gemini | Fallback 2 | gemini-3-flash |

### CI/CD Pipeline
Push → Gitea → Actions → Build → Docker → Deploy → n8n webhook → Telegram

### n8n Workflows
1. Gitea Auto Deploy
2. AI Code Review
3. PAPA Lang Test Runner
4. Security Scanner
5. RAG Documentation Bot

---

## Enterprise (Wave 3)
- **std/verify** — Vericoding: AI-verified code + formal proofs
- **std/chain** — Blockchain Audit Trail: immutable compliance log (GDPR, 152-ФЗ, HIPAA)
- **std/voice_prog** — Voice Programming: code by speaking (Gemini Live)
- **std/guard** — AI Guardrails: PII, injection, cost control

---

## Модули и архитектура

### std/orchestrator — AI Safety Layer
- **orc_review(task)** — проверка задачи на архитектурные риски
- **orc_check_file(action, path)** — проверка действий над файлами
- **orc_verify(task, plan)** — валидация плана
- **orc_cycle(task, max_steps)** — цикл review→verify→autofix

### std/design — AI Design
- design_tokens, design_component, design_palette, design_review, design_layout
- design_propose, design_from_industry, design_refine

### std/docs — Document Generation
- docs_brand, docs_logo, docs_generate, docs_templates, docs_preview_letterhead

### std/studio — Development Studio
- studio_analyze, studio_structure, studio_estimate

### std/cwb — CWB Mobile Assistant
- cwb_process, cwb_idea, cwb_ideas_list, cwb_command
- cwb_task_add, cwb_task_list, cwb_task_done, cwb_context

## Защищённые файлы (orchestrator)
- src/interpreter.py, src/lexer.py, src/parser.py
- papa.py, middleware.ts, lib/auth.ts

## Рекомендации для AI
1. Используйте orc_review перед крупными изменениями
2. Для protected files — только точечные str_replace
3. Разбивайте большие задачи на мелкие PR
