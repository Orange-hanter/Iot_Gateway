---
tags: [tasks, backlog]
---

# Бэклог задач

> Задачи, запланированные для будущих спринтов. Отсортированы по приоритету.

---

## Высокий приоритет (🔴)

| ID | Задача | Связь | Оценка |
|----|--------|-------|--------|
| B-001 | Миграция на PostgreSQL | [NFR-1](../business/requirements.md) | 13 SP |
| B-002 | Полноценный RBAC (роли, скоупы) | [US-7.1](../backlog/user_stories.md) | 8 SP |
| B-003 | OPC UA адаптер | [US-2.1](../backlog/user_stories.md) | 13 SP |
| B-004 | Профили устройств (шаблоны маппинга) | [US-1.2](../backlog/user_stories.md) | 8 SP |

## Средний приоритет (🟡)

| ID | Задача | Связь | Оценка |
|----|--------|-------|--------|
| B-005 | Node-RED интеграция | [US-3.3](../backlog/user_stories.md) | 25 SP |
| B-006 | Prometheus + Grafana метрики | [NFR-4.4](../business/requirements.md) | 5 SP |
| B-007 | Система экспорта данных (CSV, Parquet) | [Concept](../architecture/concept.md) | 30 SP |
| B-008 | DLQ для неудачных событий | — | 5 SP |
| B-009 | Redis кэш текущих значений (Live Cache) | [Ядро](../architecture/core_engine.md) | 5 SP |
| B-010 | WebSocket подписки | [US-4.3](../backlog/user_stories.md) | 8 SP |
| B-011 | Сложный маппинг данных (bit masks, composite) | [US-2.3](../backlog/user_stories.md) | 8 SP |
| B-012 | Машина состояний событий | [US-3.4](../backlog/user_stories.md) | 5 SP |
| B-013 | Аудит изменений конфигурации | [US-7.2](../backlog/user_stories.md) | 5 SP |
| B-014 | Шифрование секретов (AES-256) | [US-7.3](../backlog/user_stories.md) | 8 SP |
| B-015 | Оконная агрегация триггеров (duration) | [FR-4.6](../business/requirements.md) | 8 SP |

## Низкий приоритет (🟢)

| ID | Задача | Связь | Оценка |
|----|--------|-------|--------|
| B-016 | Горячее обновление конфигурации | [US-1.3](../backlog/user_stories.md) | 8 SP |
| B-017 | Метаданные тегов (units, ranges) | [US-4.4](../backlog/user_stories.md) | 3 SP |
| B-018 | Обновление без простоя (blue-green) | [US-5.4](../backlog/user_stories.md) | 13 SP |
| B-019 | Автоинициализация edge-устройств | [US-6.1](../backlog/user_stories.md) | 8 SP |
| B-020 | Kubernetes конфигурация | — | 8 SP |
| B-021 | Multi-node federation | [US-6.2](../backlog/user_stories.md) | 20 SP |

---

## Как работать с бэклогом

1. Задачи берутся в [active.md](active.md) при начале спринта
2. Приоритеты пересматриваются владельцем продукта
3. Новые задачи добавляются с ID (B-NNN), связью и оценкой
