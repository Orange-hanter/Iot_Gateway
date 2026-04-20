---
tags: [tasks, active]
---

# Активные задачи

> Текущий спринт. Задачи в работе и готовые к выполнению.

---

## ✅ Завершено (этот цикл)

| ID | Задача | Результат |
|----|--------|----------|
| T-001 | Миграция документации в репозиторий | [MIGRATION_PLAN](../MIGRATION_PLAN.md) — все фазы ✅ |
| T-002 | Организация структуры docs/ | 48 файлов, Obsidian symlink |
| T-003 | Определить стек для продуктовой версии | Go + Python polyglot ([ADR-008](../decisions/index.md)) |

## 🔴 Блокеры (Фаза 0 → нужно закрыть)

| ID | Задача | Приоритет | Связь |
|----|--------|-----------|-------|
| T-009 | Принять решение по СУБД (ADR-005) | 🔴 | [ADR-005-database.md](../decisions/ADR-005-database.md) |
| T-010 | Определить структуру Go-монорепо (ADR-008 детали) | 🔴 | [open-decisions.md](../decisions/open-decisions.md) |

## 🟡 Готовы к выполнению (Фаза 2)

| ID | Задача | Приоритет | Связь |
|----|--------|-----------|-------|
| T-004 | Go: gateway-core — MQTT + HTTP ingest + normalization | 🔴 | [polyglot.md](../architecture/polyglot.md) |
| T-005 | Go: rule-engine — condition eval + cooldown + webhook dispatch | 🔴 | [rule_engine.md](../modules/rule_engine.md) |
| T-006 | Go: api-gateway — REST + JWT auth + RBAC | 🔴 | [FR-7.3](../business/requirements.md) |
| T-007 | Alembic аналог для Go + миграция схемы на TimescaleDB | 🔴 | [ADR-005](../decisions/ADR-005-database.md) |
| T-008 | Python: adapter-runtime сервис (gRPC bridge) | 🟡 | [polyglot.md](../architecture/polyglot.md) |
| T-011 | Python: Modbus TCP/RTU адаптер (первый клиент) | 🔴 | [FR-1](../business/requirements.md) |
| T-012 | Structured logging (JSON) для Go-сервисов | 🟡 | [US-5.2](../backlog/user_stories.md) |
| T-013 | Настроить GitHub Actions CI (lint + test + build) | 🟡 | [open-decisions.md](../decisions/open-decisions.md) |
| T-014 | Настроить Prometheus + Grafana метрики | 🟡 | [NFR-4.4](../business/requirements.md) |

---

## Как добавить задачу

1. Добавить строку в таблицу выше
2. Указать ID (T-NNN), приоритет (🔴/🟡/🟢), связь с требованием или US
3. При завершении — перенести в [completed.md](completed.md)
