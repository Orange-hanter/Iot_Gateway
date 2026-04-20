---
tags: [module, ingestion]
related:
  - "[HTTP Listener](../../app/modules/ingestion/http_listener.py)"
  - "[MQTT Listener](../../app/modules/ingestion/mqtt_listener.py)"
  - "[Драйверы](drivers.md)"
  - "[Интеграционный слой](../architecture/integration_layer.md)"
---

# Модуль приёма данных (Ingestion)

> Отвечает за приём телеметрии по HTTP и MQTT, валидацию, парсинг через драйверы и передачу в хранилище и Rule Engine.

---

## Компоненты

### HTTP Listener

**Путь:** `app/modules/ingestion/http_listener.py`  
**Endpoint:** `POST /api/v1/ingest/http`

Принимает JSON-пакеты телеметрии от устройств:
- Валидация размера payload (max 64KB)
- Определение драйвера по `driver_type` устройства
- Парсинг через драйвер
- Batch save в БД + запись в InternalQueue для Rule Engine

### MQTT Listener

**Путь:** `app/modules/ingestion/mqtt_listener.py`  
**Топики:** `iot/+/data` (шаблон)

Подписывается на MQTT-брокер:
- Username/password аутентификация
- Извлечение `device_id` из топика
- Асинхронная обработка через event loop
- Тот же pipeline парсинга что и HTTP

## Поток данных

```
Устройство → HTTP/MQTT → Listener → Lookup Device → 
→ Get Driver → Parse → Validate → 
→ [Storage (batch save)] + [InternalQueue (для Rule Engine)]
```

## Конфигурация

| Переменная | Умолчание | Описание |
|------------|-----------|----------|
| MQTT_BROKER | mosquitto | Хост брокера |
| MQTT_PORT | 1883 | Порт |
| MQTT_USERNAME | — | Логин |
| MQTT_PASSWORD | — | Пароль |
| MQTT_TOPIC_PATTERN | iot/+/data | Шаблон топика |

## Ограничения текущей реализации

<!-- @TODO: Добавить поддержку CoAP -->
<!-- @TODO: Добавить поддержку OPC UA -->
<!-- @TODO: Добавить валидацию схемы payload по профилю устройства -->

---
**См. также:** [Драйверы](drivers.md) | [Storage](storage.md) | [Rule Engine](rule_engine.md) | [← Навигация](../index.md)
