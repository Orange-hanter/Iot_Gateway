---
tags: [moc, project]
project: Gateway
status: active
---

# Gateway — Навигация по документации

> Единый источник знаний проекта Edge-системы сбора данных для MES/IIoT

---

## Быстрый старт

| Документ | Описание |
|----------|----------|
| [Бизнес-требования](business/requirements.md) | Точка входа для владельца продукта |
| [Дорожная карта](business/roadmap.md) | Планирование и фазы |
| [Общая архитектура](architecture/overview.md) | Высокоуровневая структура системы |
| [WORKSPACE.md](../WORKSPACE.md) | Карта рабочего пространства |

---

## Бизнес-уровень

- [Бизнес-требования](business/requirements.md) — функциональные и нефункциональные требования, метрики успеха, реестр открытых пунктов
- [Проблемное заявление](business/problem_statement.md) — какую боль решает Gateway, ценностное предложение
- [Персоны и участники сделки](business/personas.md) — покупательские и операционные роли, путь лида
- [Модель ценообразования](business/pricing_model.md) — тарифы, структура КП, сценарии по масштабу
- [Модель поддержки](business/support_model.md) — SLA, уровни L1/L2/L3, релизный цикл
- [Закупочный документ](business/procurement_guide.md) — варианты оборудования, BoM
- [Дорожная карта](business/roadmap.md) — фазы, спринты, приоритеты

## Архитектура

- [Общая архитектура](architecture/overview.md) — модули и потоки данных
- [Архитектурная концепция](architecture/concept.md) — фундаментальные решения
- [Ядро системы](architecture/core_engine.md) — нормализация, конвейер, правила
- [Интеграционный слой](architecture/integration_layer.md) — адаптеры, протоколы, маппинг
- [ТЗ IoT-Core](architecture/iot_core_spec.md) — микросервисная спецификация

## Бэклог

- [Пользовательские истории](backlog/user_stories.md) — 30+ US по 7 эпикам
- [Эпики](backlog/epics.md) — структура и приоритеты
- [План спринтов](backlog/sprint_plan.md) — распределение по спринтам

## Технические спецификации

- [REST API](specs/api.md) — эндпоинты, форматы, аутентификация
- [Модель данных](specs/data_model.md) — SQLAlchemy модели, индексы
- [MQTT протокол](specs/mqtt.md) — топики, QoS, тестирование
- [Технические требования](specs/requirements.md) — производительность, инфраструктура

## Модули

- [Приём данных (Ingestion)](modules/ingestion.md) — HTTP + MQTT listeners
- [Хранение (Storage)](modules/storage.md) — SQLite, WAL, TTL, batch writes
- [Движок правил (Rule Engine)](modules/rule_engine.md) — триггеры, условия, webhook
- [API модуль](modules/api_module.md) — FastAPI роуты, middleware
- [Драйверы](modules/drivers.md) — generic_json, arduino_mq2, arduino_button_dht11

## Руководства

- [Разработка](guides/development.md) — локальная настройка, Docker, тесты
- [Развёртывание](guides/deployment.md) — production checklist
- [Arduino Button+DHT11](guides/arduino_button_dht11.md) — подключение, wiring, firmware
- [Arduino MQ2](guides/arduino_mq2.md) — газовый датчик
- [Webhook-приёмник](guides/webhook_receiver.md) — тестовый сервис
- [Пересборка](guides/rebuild.md) — Docker rebuild

## Задачи

- [Активные задачи](tasks/active.md) — текущий спринт
- [Завершённые задачи](tasks/completed.md) — история
- [Бэклог задач](tasks/backlog_tasks.md) — очередь

## Решения

- [Архитектурные решения (ADR)](decisions/) — журнал решений

## Отчёты

- [Отчёт о завершении пилота](reports/completion_report.md)
- [Сводка по надёжности](reports/reliability_summary.md)

---

## Теги

- `#architecture` — архитектурные документы
- `#requirements` — требования
- `#iot` — IoT-специфика
- `#integration` — интеграция
- `#task` — задачи
- `#completed` — завершённые элементы
- `#todo` — требует проработки

## Условные маркеры

- `<!-- @TODO -->` — требует проработки позже (поиск: `grep -r "@TODO" docs/`)
- `<!-- @REVIEW -->` — требует ревью
- `<!-- @DECISION -->` — требуется принятие решения
