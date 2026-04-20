---
tags: [specs, data-model]
related:
  - "[Storage модуль](../modules/storage.md)"
  - "[Ядро системы](../architecture/core_engine.md)"
---

# Модель данных

> Описание ORM-моделей и схемы базы данных.  
> Реализация: [app/database/models.py](../../app/database/models.py)

---

## Таблицы

### Device (устройства)

| Поле | Тип | Описание |
|------|-----|----------|
| id | String(36) PK | UUID устройства |
| name | String(100) | Имя устройства |
| driver_type | String(50) | Тип драйвера (generic_json, arduino_mq2, etc.) |
| config | Text (JSON) | Конфигурация подключения |
| status | String(20) | online / offline / error |
| last_seen | DateTime | Последний контакт |
| created_at | DateTime | Дата создания |
| updated_at | DateTime | Дата обновления |

**Индексы:** `idx_device_status` (status)

### Telemetry (телеметрия)

| Поле | Тип | Описание |
|------|-----|----------|
| id | Integer PK | Auto-increment ID |
| device_id | String(36) FK | Ссылка на Device |
| timestamp | DateTime | Время измерения |
| metric_name | String(100) | Имя метрики |
| value | Float | Числовое значение |
| unit | String(20) | Единица измерения |

**Индексы:**
- `idx_telemetry_device_time` (device_id, timestamp)
- `idx_telemetry_metric` (metric_name)
- `idx_telemetry_timestamp` (timestamp)

### Trigger (триггеры)

| Поле | Тип | Описание |
|------|-----|----------|
| id | Integer PK | Auto-increment ID |
| name | String(100) | Имя триггера |
| device_id | String(36) FK | Устройство (опционально) |
| metric_name | String(100) | Метрика для проверки |
| condition | String(200) | Условие (> 30, 10..50, etc.) |
| webhook_url | String(500) | URL для вызова |
| cooldown_sec | Integer | Период ожидания (default: 60) |
| is_active | Boolean | Активен ли триггер |
| last_triggered_at | DateTime | Последнее срабатывание |
| firebase_notification | Text (JSON) | Настройки Firebase push |

### WebhookLog (логи webhook)

| Поле | Тип | Описание |
|------|-----|----------|
| id | Integer PK | Auto-increment ID |
| trigger_id | Integer FK | Ссылка на Trigger |
| timestamp | DateTime | Время вызова |
| success | Boolean | Успешность |
| status_code | Integer | HTTP код ответа |
| error | Text | Текст ошибки |

### InternalQueue (внутренняя очередь)

| Поле | Тип | Описание |
|------|-----|----------|
| id | Integer PK | Auto-increment ID |
| event_type | String(50) | Тип события |
| payload | Text (JSON) | Данные события |
| is_processed | Boolean | Обработано ли |
| created_at | DateTime | Дата создания |

---

## Политики хранения

- **Телеметрия:** TTL = 30 дней (настраивается через DATA_TTL_DAYS)
- **Очередь:** TTL = 7 дней для обработанных записей
- **Cleanup:** Автоматический запуск каждый час

<!-- @TODO: Добавить политики агрегации (min/max/avg) при миграции на PostgreSQL -->

---

## Миграции

Текущая реализация использует SQLAlchemy `create_all()` для создания схемы.

<!-- @TODO: Перейти на Alembic для версионных миграций -->

---
**См. также:** [Storage модуль](../modules/storage.md) | [Ядро](../architecture/core_engine.md) | [← Навигация](../index.md)
