# WORKSPACE.md — Карта рабочего пространства

> Машиночитаемый индекс проекта Gateway. Обновляется при изменении структуры.

---

## Проект

| Поле | Значение |
|------|----------|
| **Название** | Gateway — Edge-система сбора данных для MES/IIoT |
| **Тип** | IoT платформа (модульный монолит, пилот → продукт) |
| **Стек** | Python 3.11+, FastAPI, SQLAlchemy, SQLite, MQTT (Mosquitto), Docker |
| **Статус** | Пилот завершён. Переход к продуктовому решению |
| **Документация** | [docs/index.md](docs/index.md) |

---

## Структура кодовой базы

```
app/                          # Основное приложение
├── __init__.py               # Версия пакета
├── config.py                 # Конфигурация (env vars)
├── main.py                   # FastAPI точка входа, lifecycle
├── database/
│   ├── connection.py         # SQLAlchemy engine, сессии
│   └── models.py             # ORM модели (Device, Telemetry, Trigger, etc.)
├── drivers/
│   ├── base.py               # Базовый класс драйвера
│   ├── generic_json.py       # Универсальный JSON-драйвер
│   ├── arduino_button_dht11.py  # Драйвер кнопки + DHT11
│   └── arduino_mq2.py       # Драйвер газового датчика MQ2
└── modules/
    ├── api/
    │   ├── middleware.py      # Rate limiting, API key auth
    │   └── routes.py          # REST API endpoints
    ├── engine/
    │   ├── rule_engine.py     # Движок правил, триггеры, webhook dispatch
    │   └── webhook_dispatcher.py  # Отправка webhook
    ├── ingestion/
    │   ├── http_listener.py   # HTTP endpoint для приёма данных
    │   └── mqtt_listener.py   # MQTT subscriber
    └── storage/
        └── storage_service.py # DAL: batch save, query, cleanup
```

## Инфраструктура

```
docker-compose.yml            # Основная конфигурация (app + mosquitto + webhook_receiver)
docker-compose.override.yml   # Локальные переопределения
Dockerfile                    # Образ приложения
mosquitto/                    # Конфигурация MQTT-брокера
webhook_receiver/             # Тестовый webhook-приёмник
arduino/                      # Arduino bridges + firmware
scripts/                      # Скрипты управления bridge'ами
static/admin/                 # SPA админка (заготовка)
```

## Документация

```
docs/
├── index.md                  # Навигационный хаб
├── MIGRATION_PLAN.md         # План перехода на продуктовую версию
├── business/                 # Бизнес: требования, закупки, roadmap
├── architecture/             # Архитектура: концепция, ядро, интеграция
├── backlog/                  # Бэклог: user stories, эпики, спринты
├── specs/                    # Спецификации: API, модель данных, MQTT
├── modules/                  # Документация модулей
├── guides/                   # Руководства: dev, deploy, arduino
├── tasks/                    # Трекинг задач: active, completed, backlog
├── decisions/                # ADR (Architecture Decision Records)
├── reports/                  # Отчёты: completion, reliability
└── _templates/               # Шаблоны: ADR, bug, feature, meeting
```

## Ключевые точки входа

| Роль | Документ |
|------|----------|
| **Владелец продукта** | [docs/business/requirements.md](docs/business/requirements.md) |
| **Архитектор** | [docs/architecture/concept.md](docs/architecture/concept.md) |
| **Разработчик** | [docs/guides/development.md](docs/guides/development.md) |
| **DevOps** | [docs/guides/deployment.md](docs/guides/deployment.md) |
| **Агент/AI** | Этот файл (WORKSPACE.md) + [docs/index.md](docs/index.md) |

## Модули приложения

| Модуль | Путь | Описание | Документация |
|--------|------|----------|--------------|
| **Ingestion** | `app/modules/ingestion/` | Приём данных по HTTP и MQTT | [docs/modules/ingestion.md](docs/modules/ingestion.md) |
| **Storage** | `app/modules/storage/` | Хранение, batch write, cleanup | [docs/modules/storage.md](docs/modules/storage.md) |
| **Rule Engine** | `app/modules/engine/` | Триггеры, условия, webhook | [docs/modules/rule_engine.md](docs/modules/rule_engine.md) |
| **API** | `app/modules/api/` | REST API, auth, rate limit | [docs/modules/api_module.md](docs/modules/api_module.md) |
| **Drivers** | `app/drivers/` | Парсинг данных устройств | [docs/modules/drivers.md](docs/modules/drivers.md) |

## Данные

| Модель | Таблица | Назначение |
|--------|---------|------------|
| `Device` | devices | Реестр IoT-устройств |
| `Telemetry` | telemetry | Временные ряды метрик |
| `Trigger` | triggers | Правила срабатывания |
| `WebhookLog` | webhook_logs | Логи доставки webhook |
| `InternalQueue` | internal_queue | Буфер событий для Rule Engine |

## Конфигурация (env vars)

| Переменная | Умолчание | Описание |
|------------|-----------|----------|
| `APP_ENV` | development | Окружение |
| `DATABASE_URL` | sqlite:///data/iot_core.db | Путь к БД |
| `MQTT_BROKER` | mosquitto | Хост MQTT |
| `MQTT_PORT` | 1883 | Порт MQTT |
| `API_KEY` | — | Ключ аутентификации |
| `RATE_LIMIT` | 60 | Запросов/мин |
| `WEBHOOK_TIMEOUT` | 10 | Таймаут webhook (сек) |
| `RULE_ENGINE_POLL_INTERVAL` | 5 | Интервал проверки триггеров (сек) |
| `DATA_TTL_DAYS` | 30 | Хранение телеметрии (дней) |
