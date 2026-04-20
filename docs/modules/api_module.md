---
tags: [module, api]
related:
  - "[Routes](../../app/modules/api/routes.py)"
  - "[Middleware](../../app/modules/api/middleware.py)"
  - "[API спецификация](../specs/api.md)"
---

# API модуль

> REST API на FastAPI. Аутентификация, rate limiting, CRUD для устройств/триггеров, запросы телеметрии.

---

## Middleware

**Путь:** `app/modules/api/middleware.py`

- **API Key Auth:** Проверка заголовка `X-API-Key` (кроме `/health`)
- **Rate Limiting:** 60 запросов/мин на IP (настраивается через RATE_LIMIT)

## Endpoints

### Системные
| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/health` | Health check (503 при проблемах) |
| GET | `/api/v1/stats` | Статистика системы |
| GET | `/api/v1/metrics` | Метрики |
| GET | `/api/v1/drivers` | Список драйверов |

### Устройства
| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/v1/devices` | Список устройств |
| POST | `/api/v1/devices` | Создание устройства |
| GET | `/api/v1/devices/{id}` | Получение устройства |
| PUT | `/api/v1/devices/{id}` | Обновление |
| DELETE | `/api/v1/devices/{id}` | Удаление |

### Телеметрия
| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/v1/telemetry` | Запрос с фильтрами |
| GET | `/api/v1/metrics/suggestions` | Подсказки метрик |

### Триггеры
| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/v1/triggers` | Список триггеров |
| POST | `/api/v1/triggers` | Создание |
| PUT | `/api/v1/triggers/{id}` | Обновление |
| DELETE | `/api/v1/triggers/{id}` | Удаление |

### Webhooks
| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/v1/webhooks/test` | Тестовый вызов |
| GET | `/api/v1/webhooks/logs` | Логи доставки |

---
**См. также:** [API спецификация](../specs/api.md) | [← Навигация](../index.md)
