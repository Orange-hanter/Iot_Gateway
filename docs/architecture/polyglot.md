---
tags: [architecture, go, python, polyglot]
related:
  - "[Обзор архитектуры](overview.md)"
  - "[Ядро системы](core_engine.md)"
  - "[Интеграционный слой](integration_layer.md)"
  - "[ADR-008: Go как язык продуктового ядра](../decisions/index.md)"
---

# Polyglot-архитектура: Go + Python

> Принятое решение (2026-04-08): **Go** — высокопроизводительное ядро; **Python** — гибкий runtime для адаптеров и конфигурации.

---

## Принцип разделения

Единственный критерий распределения кода между Go и Python:

| Свойство | Go | Python |
|----------|----|--------|
| Производительность (1000+ msg/sec) | ✅ Goroutines, минимальный GC | ❌ GIL, медленнее |
| Горячая загрузка кода без рестарта | ❌ Статическая компиляция | ✅ importlib, eval |
| Богатая экосистема IoT-протоколов | ❌ Меньше библиотек | ✅ pymodbus, opcua, etc. |
| Статическая типизация / надёжность | ✅ Встроена | ❌ Опциональная |
| Визуальное конфигурирование (Node-RED) | — | ✅ Нативный JS, но Python sidecar |

**Вывод:** Go берёт критичные по производительности пути (`ingest → normalize → store → dispatch`). Python держит runtime-гибкость (`adapter loading → Node-RED sidecar`).

---

## Сервисная карта

```
┌─────────────────────────────────────────────────────────────┐
│                        Go Services                          │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │ gateway-core │  │ rule-engine  │  │   api-gateway     │  │
│  │              │  │              │  │                   │  │
│  │ - MQTT sub   │  │ - trigger    │  │ - REST API        │  │
│  │ - HTTP ingest│  │   eval       │  │ - WebSocket       │  │
│  │ - normalize  │  │ - state mgmt │  │ - Auth/RBAC       │  │
│  │ - dispatch   │  │ - cooldown   │  │ - Rate limiting   │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬──────────┘  │
│         │                 │                   │             │
│         └────────┬────────┘                   │             │
│                  ↓                            │             │
│           ┌─────────┐                         │             │
│           │   DB    │◄────────────────────────┘             │
│           │ (ADR-005)│                                      │
│           └────┬────┘                                      │
└────────────────┼───────────────────────────────────────────┘
                 │ gRPC
┌────────────────▼───────────────────────────────────────────┐
│                    Python Services                          │
│                                                             │
│  ┌─────────────────────────────┐  ┌──────────────────────┐  │
│  │     adapter-runtime          │  │   export-worker      │  │
│  │                             │  │                      │  │
│  │ - Hot-reload Python adapters│  │ - CSV / Parquet      │  │
│  │ - Modbus TCP/RTU adapter    │  │ - Scheduled jobs     │  │
│  │ - Node-RED sidecar (JS)     │  │ - Data retention     │  │
│  │ - OPC UA adapter (future)   │  │                      │  │
│  └─────────────────────────────┘  └──────────────────────┘  │
└────────────────────────────────────────────────────────────┘
```

---

## Go-сервисы (детальное описание)

### gateway-core

**Задача:** Принять данные из любого источника, нормализовать в единый формат, сохранить, отдать rule-engine и api-gateway.

**Входящие данные:**
- MQTT (Mosquitto broker) — основной канал от устройств
- HTTP POST `/ingest/` — fallback для устройств без MQTT

**Нормализация:**
- Применение маппинга полей (из профиля устройства)
- Приведение типов (string → float, timestamp normalization)
- Тегирование (`device_id`, `sensor_type`, `unit`)

**Производительность:**
- Goroutine pool: 1 goroutine на MQTT topic или HTTP handler
- Цель: **1000 msg/sec** при 100 устройствах (10 msg/sec/device средний)
- Buffer: кольцевой буфер в памяти 10K событий для сглаживания пиков

### rule-engine

**Задача:** Оценка условий триггеров, управление состоянием, диспатч webhook/action.

**Компоненты:**
- `ConditionEvaluator` — поддержка: `>`, `<`, `==`, `!=`, `contains`, `range`
- `StateManager` — состояние устройств (последнее значение, онлайн/офлайн)
- `CooldownTracker` — не спамить webhook (per-trigger configurable)
- `WebhookDispatcher` — HTTP POST с retry и backoff

### api-gateway

**Задача:** REST API для внешних клиентов, dashboard platform, WebSocket для live data.

**Эндпоинты:**
- `GET /api/v1/devices` — список устройств
- `GET /api/v1/devices/{id}/telemetry` — история
- `GET /api/v1/triggers` — список триггеров
- `POST /api/v1/triggers` — создание
- `WS /ws/live` — WebSocket-стрим для дашбордов

**Auth:** JWT Bearer token. RBAC: роли `admin`, `operator`, `viewer`.

---

## Python-сервисы (детальное описание)

### adapter-runtime

**Задача:** Загружать и выполнять Python-адаптеры без рестарта ядра.

**Механизм hot-reload:**
```python
# Публичный интерфейс адаптера
class ModbusAdapter(BaseAdapter):
    def connect(self, config: dict) -> None: ...
    def read(self) -> list[DataPoint]: ...
    def disconnect(self) -> None: ...
```

- `importlib.reload()` при обнаружении изменения файла адаптера
- Каждый адаптер запускается в отдельном `asyncio.Task`
- Падение одного адаптера **не влияет** на другие

**gRPC интерфейс с Go:**
```proto
service AdapterRuntime {
  rpc PushData (DataBatch) returns (Ack);
  rpc LoadAdapter (AdapterConfig) returns (LoadResult);
  rpc UnloadAdapter (AdapterId) returns (Ack);
  rpc GetStatus (Empty) returns (RuntimeStatus);
}
```

**Node-RED sidecar:**
- Node-RED запускается как subprocess внутри adapter-runtime контейнера
- Custom nodes (npm package `node-red-contrib-gateway`) — публикуют/читают MQTT
- Конфигурация потока = JSON файл, версионируется в БД

### Адаптеры (первая очередь)

| Адаптер | Протокол | Приоритет | Статус |
|---------|----------|-----------|--------|
| `modbus_tcp.py` | Modbus TCP | 🔴 Первый клиент | <!-- @TODO: разработать --> |
| `modbus_rtu.py` | Modbus RTU | 🔴 Первый клиент | <!-- @TODO --> |
| `arduino_button_dht11.py` | Serial/USB | ✅ Пилот | Готов |
| `arduino_mq2.py` | Serial/USB | ✅ Пилот | Готов |
| `generic_json.py` | HTTP JSON | ✅ Пилот | Готов |
| `opcua.py` | OPC UA | 🟡 Будущее | <!-- @TODO --> |

---

## Коммуникация между сервисами

| Канал | Участники | Формат | Причина |
|-------|-----------|--------|---------|
| MQTT | Устройства → gateway-core | JSON payload | Лёгкий, low-latency, IoT-стандарт |
| gRPC | gateway-core → adapter-runtime | Protobuf | Типизированный, эффективный межсервисный |
| SQL | Все Go-сервисы → DB | SQL (ORM) | Reliability, transactions |
| HTTP/REST | Внешние клиенты → api-gateway | JSON | Универсальный |
| WebSocket | api-gateway → Дашборды | JSON stream | Live данные без polling |

---

## Стратегия миграции с Python-пилота

### Текущий стек (пилот)

```
Python FastAPI monolith (all-in-one)
├── HTTP listener
├── MQTT listener  
├── Rule Engine
├── Storage Service
└── REST API
```

### Целевой стек (продукт)

```
Go: gateway-core | rule-engine | api-gateway
Python: adapter-runtime (с Node-RED sidecar)
Shared: DB (ADR-005), Mosquitto MQTT broker
```

### Порядок миграции (по фазам roadmap)

```
Шаг 1 (S1–S2): Go gateway-core запускается ПАРАЛЛЕЛЬНО с Python
  - Go слушает те же MQTT топики
  - Go пишет в ту же БД (SQLite временно → целевая СУБД по ADR-005)
  - Python работает, трафик постепенно переключается на Go

Шаг 2 (S3): Go rule-engine заменяет Python rule_engine.py
  - Python rule_engine.py выключается
  - Go читает триггеры из той же таблицы БД

Шаг 3 (S4): Go api-gateway заменяет Python FastAPI
  - Маршруты, схемы ответов — совместимы с текущим API
  - Клиенты не замечают смены бэкенда

Шаг 4 (S8): Python adapter-runtime запускается как отдельный сервис
  - Адаптеры переезжают из Python-монолита в adapter-runtime
  - Связь через gRPC

Шаг 5: Python-монолит выводится из эксплуатации
```

> <!-- @REVIEW --> Обсудить: стоит ли добавить API compatibility tests перед шагом 3, чтобы убедиться в полной совместимости схем.

---

## NFR-поведение при целевом стеке

| NFR | Требование | Как обеспечивается |
|-----|------------|-------------------|
| NFR-1.1 | 100 устройств | Go goroutine pool — масштабируется легко |
| NFR-2.1 | 1000 msg/sec | Go + кольцевой буфер; Python adapter-runtime не на критическом пути |
| NFR-3.1 | Uptime 99.5% | Сервисы независимы; падение adapter-runtime не роняет ядро |
| NFR-3.2 | Restart < 5 сек | Stateless Go-сервисы; adapter-runtime — pid-файлы |
| NFR-5.1 | JWT auth | api-gateway (Go): middleware |
| NFR-5.2 | RBAC | api-gateway: roles table в БД |

---

## Открытые вопросы

<!-- @DECISION: ADR-005 — конкретная СУБД; от неё зависит ORM в Go (pgx? sqlc? ent?) -->
<!-- @TODO: определить gRPC proto файлы и поместить в /proto/ директорию -->
<!-- @TODO: создать Dockerfile для adapter-runtime (python + node-red) -->
<!-- @REVIEW: нужен ли export-worker в фазе 2 или можно отложить до фазы 4? -->

---
**См. также:** [Обзор архитектуры](overview.md) | [Решения ADR](../decisions/index.md) | [Roadmap](../business/roadmap.md) | [← Навигация](../index.md)
