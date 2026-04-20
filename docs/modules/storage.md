---
tags: [module, storage]
related:
  - "[Storage Service](../../app/modules/storage/storage_service.py)"
  - "[Модель данных](../specs/data_model.md)"
  - "[Ядро системы](../architecture/core_engine.md)"
---

# Модуль хранения (Storage)

> Отвечает за запись, чтение и cleanup телеметрии.

---

## Компоненты

### Storage Service

**Путь:** `app/modules/storage/storage_service.py`

Функции:
- **Batch save** — пакетная запись телеметрии (снижает I/O нагрузку)
- **Query** — выборка с фильтрацией по device_id, metric_name, time range
- **Device update** — обновление last_seen при получении данных
- **Queue management** — запись/чтение InternalQueue для Rule Engine
- **TTL cleanup** — удаление устаревших данных

## Хранилище

**Текущая реализация:** SQLite + WAL mode
- Оптимизация под параллельное чтение
- Batch writes для минимизации fsync
- Индексы для быстрой выборки по времени

<!-- @TODO: Миграция на PostgreSQL для >1M событий/день -->
<!-- @TODO: Hot/Cold разделение данных -->
<!-- @TODO: Агрегаты (min/max/avg) по расписанию -->

## Cleanup Loop

Запускается каждый час:
- Удаляет телеметрию старше DATA_TTL_DAYS (default: 30)
- Удаляет обработанные записи очереди старше 7 дней

---
**См. также:** [Модель данных](../specs/data_model.md) | [Ingestion](ingestion.md) | [Rule Engine](rule_engine.md) | [← Навигация](../index.md)
