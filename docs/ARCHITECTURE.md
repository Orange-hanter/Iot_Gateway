# Архитектура IoT-Core MVP

## Обзор системы

IoT-Core — это модульная монолитная платформа для сбора, хранения и обработки телеметрии IoT-устройств.

```
┌─────────────────────────────────────────────────────────────────┐
│                         IoT DEVICES                              │
│  (Датчики, контроллеры, микрокомпьютеры)                        │
└────────┬────────────────────────────────────────────┬────────────┘
         │ HTTP POST                                  │ MQTT Publish
         │ /api/v1/ingest/http                       │ iot/{id}/data
         ▼                                            ▼
┌────────────────────────────────────────────────────────────────┐
│                    INGESTION MODULE                             │
│  ┌──────────────────┐          ┌──────────────────┐           │
│  │  HTTP Listener   │          │  MQTT Listener   │           │
│  │  (FastAPI)       │          │  (Paho MQTT)     │           │
│  └────────┬─────────┘          └────────┬─────────┘           │
│           │                              │                      │
│           └──────────┬───────────────────┘                      │
│                      │                                          │
│                      ▼                                          │
│           ┌──────────────────────┐                             │
│           │  Driver Dispatcher   │                             │
│           │  - Generic JSON      │                             │
│           │  - Custom Drivers    │                             │
│           └──────────┬───────────┘                             │
└──────────────────────┼──────────────────────────────────────────┘
                       │ Normalized Events
                       ▼
┌────────────────────────────────────────────────────────────────┐
│                   INTERNAL QUEUE                                │
│  (SQLite table: internal_queue)                                 │
│  - Event buffering                                              │
│  - Async processing                                             │
└────────┬───────────────────────────────────────────────────────┘
         │
         │ Read Events
         ▼
┌────────────────────────────────────────────────────────────────┐
│                   STORAGE MODULE                                │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │              SQLite Database (WAL mode)                  │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │  │
│  │  │ devices  │ │telemetry │ │ triggers │ │  logs    │  │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │  │
│  └─────────────────────────────────────────────────────────┘  │
│  - Batch inserts                                               │
│  - TTL cleanup                                                 │
│  - Indexing                                                    │
└────────┬───────────────────────────────────────────────────────┘
         │
         │ Poll new data
         ▼
┌────────────────────────────────────────────────────────────────┐
│                   RULE ENGINE MODULE                            │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  Trigger Evaluation                                       │ │
│  │  - Condition matching (>, <, ==, range)                  │ │
│  │  - Cooldown management                                    │ │
│  │  - State tracking                                         │ │
│  └────────┬─────────────────────────────────────────────────┘ │
│           │ Trigger fired                                      │
│           ▼                                                    │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  Webhook Dispatcher                                       │ │
│  │  - HTTP POST to external URLs                            │ │
│  │  - Retry with exponential backoff                        │ │
│  │  - Result logging                                         │ │
│  └────────┬─────────────────────────────────────────────────┘ │
└───────────┼────────────────────────────────────────────────────┘
            │ HTTP POST
            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    EXTERNAL WEBHOOKS                             │
│  (Уведомления, интеграции, внешние сервисы)                    │
└─────────────────────────────────────────────────────────────────┘

         ┌──────────────────────┐
         │   API CLIENTS        │
         │   (Apps, Scripts)    │
         └──────────┬───────────┘
                    │ HTTP REST
                    ▼
┌────────────────────────────────────────────────────────────────┐
│                    API GATEWAY MODULE                           │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  REST API (FastAPI)                                       │ │
│  │  - /devices     (CRUD)                                    │ │
│  │  - /telemetry   (Read)                                    │ │
│  │  - /triggers    (CRUD)                                    │ │
│  │  - /webhooks    (Test, Logs)                             │ │
│  │  - /stats       (System stats)                           │ │
│  └──────────────────────────────────────────────────────────┘ │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │  Middleware                                               │ │
│  │  - Authentication (API Key)                              │ │
│  │  - Rate Limiting                                          │ │
│  │  - Logging                                                │ │
│  └──────────────────────────────────────────────────────────┘ │
└────────┬───────────────────────────────────────────────────────┘
         │
         │ Static Files
         ▼
┌────────────────────────────────────────────────────────────────┐
│                    ADMIN UI MODULE                              │
│  - Single Page Application (HTML/CSS/JS)                       │
│  - Device management                                            │
│  - Trigger configuration                                        │
│  - Logs viewer                                                  │
│  - System dashboard                                             │
└─────────────────────────────────────────────────────────────────┘
```

## Потоки данных

### 1. Прием телеметрии (Data Ingestion Flow)

```
Device → HTTP/MQTT → Ingestion → Driver → Validation → 
→ Normalization → Internal Queue → Storage → Database
```

### 2. Обработка триггеров (Trigger Processing Flow)

```
Internal Queue → Rule Engine → Condition Check → 
→ Cooldown Check → Webhook Dispatcher → External URL → 
→ Log Result
```

### 3. API запросы (API Request Flow)

```
Client → API Gateway → Auth Middleware → Rate Limit → 
→ Route Handler → Database → Response
```

## Компоненты

### Модуль Приема (Ingestion Module)

**Ответственность:**
- Прием данных от устройств через HTTP и MQTT
- Валидация формата данных
- Применение драйверов для парсинга
- Нормализация в единый формат
- Отправка в очередь

**Технологии:**
- FastAPI (HTTP)
- Paho MQTT (MQTT)
- Драйверная система (расширяемая)

### Модуль Хранения (Storage Module)

**Ответственность:**
- Управление подключением к БД
- Пакетная запись телеметрии
- Чтение исторических данных
- TTL cleanup (автоматическое удаление старых данных)
- Управление очередью событий

**Технологии:**
- SQLAlchemy (ORM)
- aiosqlite (async SQLite)
- SQLite WAL mode

### Модуль Обработки Правил (Rule Engine Module)

**Ответственность:**
- Мониторинг новых данных
- Оценка условий триггеров
- Управление состоянием (cooldown)
- Диспетчеризация вебхуков
- Retry логика

**Технологии:**
- asyncio (event loop)
- httpx (async HTTP client)

### Модуль API (API Gateway Module)

**Ответственность:**
- REST API для внешних клиентов
- CRUD операции над устройствами и триггерами
- Чтение телеметрии
- Тестирование вебхуков
- Статистика системы

**Технологии:**
- FastAPI
- Pydantic (validation)
- Middleware (auth, rate limit, logging)

### Модуль Админ-панели (Admin UI Module)

**Ответственность:**
- Визуальное управление устройствами
- Конструктор триггеров
- Дашборд с метриками
- Просмотр логов

**Технологии:**
- HTML/CSS/JavaScript (Vanilla JS)
- Fetch API для взаимодействия с backend

## Модель данных

### Основные таблицы

1. **devices** - Устройства
   - id, name, driver_type, config, status, last_seen

2. **telemetry** - Телеметрия
   - id, device_id, timestamp, metric_name, value, unit

3. **triggers** - Триггеры
   - id, name, device_id, metric_name, condition, webhook_url, cooldown_sec

4. **webhook_logs** - Логи вебхуков
   - id, trigger_id, device_id, metric_name, metric_value, sent_at, status_code, success

5. **internal_queue** - Внутренняя очередь
   - id, event_type, payload, created_at, is_processed

### Индексы

- `idx_device_status` - для фильтрации по статусу
- `idx_telemetry_device_time` - для запросов истории
- `idx_telemetry_metric` - для фильтрации по метрике
- `idx_trigger_active` - для выборки активных триггеров
- `idx_queue_processed` - для обработки очереди

## Масштабирование

### Текущие ограничения (MVP)

- Один хост (Docker Compose)
- SQLite (без кластеризации)
- Один экземпляр каждого модуля
- In-memory rate limiting

### Пути масштабирования

1. **База данных:**
   - Миграция на PostgreSQL/MySQL
   - Репликация read replicas
   - Партиционирование таблицы telemetry

2. **Очередь:**
   - Замена internal_queue на RabbitMQ/Redis
   - Отдельные очереди для приоритетов

3. **Модули:**
   - Разделение на микросервисы
   - Горизонтальное масштабирование (Kubernetes)
   - Load balancing

4. **Кеширование:**
   - Redis для кеша метаданных устройств
   - Кеш последних значений метрик

## Безопасность

### Реализованные меры

- API Key аутентификация
- Rate Limiting
- Валидация размера payload
- Логирование всех операций

### Рекомендации для продакшена

- SSL/TLS для всех соединений
- Шифрование чувствительных данных в БД
- OAuth2/JWT вместо статических ключей
- Аудит логи
- Network policies

## Мониторинг

### Health Checks

- `/health` endpoint
- Docker health check
- Проверка подключения к БД
- Проверка статуса фоновых сервисов

### Метрики

- Статистика через `/api/v1/stats`
- X-Process-Time заголовки
- Логи вебхуков

### Будущие улучшения

- Prometheus metrics
- Grafana dashboards
- Alerting (PagerDuty, etc.)
