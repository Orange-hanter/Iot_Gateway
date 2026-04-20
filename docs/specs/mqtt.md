---
tags: [specs, mqtt]
related:
  - "[Ingestion модуль](../modules/ingestion.md)"
  - "[MQTT Listener](../../app/modules/ingestion/mqtt_listener.py)"
---

# Тестирование MQTT (Mosquitto)

## Проверка статуса

```bash
# Проверка статуса всех сервисов
docker-compose ps

# Проверка логов MQTT брокера
docker-compose logs mqtt-broker

# Проверка подключения MQTT listener
docker-compose logs iot-core | grep -i mqtt
```

## Команды для ручной проверки

### 1. Просмотр логов webhook-receiver в реальном времени (для наблюдения триггеров)

```bash
docker-compose logs -f webhook-receiver
```

### 2. Отправка MQTT сообщения (в отдельном терминале)

```bash
# Отправка данных через MQTT
mosquitto_pub -h localhost -p 1883 \
  -t "iot/d3fe6a60-8102-4fa6-a6c8-ea4bd8e8c019/data" \
  -m '{"metrics": {"temperature": 45, "humidity": 75.0}}'
```

### 3. Проверка обработанных данных

```bash
# Проверка последней телеметрии через API
curl -s "http://localhost:8000/api/v1/telemetry/d3fe6a60-8102-4fa6-a6c8-ea4bd8e8c019?limit=5" \
  -H "X-API-Key: your-secret-api-key-change-this" | jq '.[] | {timestamp, metric_name, value}'

# Общая статистика системы
curl -s http://localhost:8000/api/v1/stats \
  -H "X-API-Key: your-secret-api-key-change-this" | jq .
```

## Полный сценарий тестирования

### Терминал 1: Мониторинг webhook-receiver

```bash
docker-compose logs -f webhook-receiver
```

### Терминал 2: Отправка MQTT данных

```bash
# Отправка данных с температурой > 30 (триггер должен сработать)
mosquitto_pub -h localhost -p 1883 \
  -t "iot/d3fe6a60-8102-4fa6-a6c8-ea4bd8e8c019/data" \
  -m '{"metrics": {"temperature": 42, "humidity": 80.5}}'

# Ожидание 5-10 секунд для обработки Rule Engine

# Проверка результата
curl -s "http://localhost:8000/api/v1/telemetry/d3fe6a60-8102-4fa6-a6c8-ea4bd8e8c019?limit=2" \
  -H "X-API-Key: your-secret-api-key-change-this" | jq .
```

## Формат MQTT топика

```
iot/{device_id}/data
```

- **device_id**: UUID устройства из таблицы devices
- Пример: `iot/d3fe6a60-8102-4fa6-a6c8-ea4bd8e8c019/data`

## Формат payload

```json
{
  "metrics": {
    "metric_name_1": value1,
    "metric_name_2": value2
  }
}
```

Примеры:

```json
{
  "metrics": {
    "temperature": 25.5,
    "humidity": 60.0
  }
}
```

```json
{
  "metrics": {
    "temperature": 42,
    "humidity": 80.5,
    "pressure": 1013.25
  }
}
```

## Проверка работы триггера

Текущий триггер: `temperature > 30`

```bash
# Отправка данных НИЖЕ порога (триггер НЕ сработает)
mosquitto_pub -h localhost -p 1883 \
  -t "iot/d3fe6a60-8102-4fa6-a6c8-ea4bd8e8c019/data" \
  -m '{"metrics": {"temperature": 25, "humidity": 60.0}}'

# Отправка данных ВЫШЕ порога (триггер сработает)
mosquitto_pub -h localhost -p 1883 \
  -t "iot/d3fe6a60-8102-4fa6-a6c8-ea4bd8e8c019/data" \
  -m '{"metrics": {"temperature": 35, "humidity": 70.0}}'
```

## Проверка логов вебхуков

```bash
# Последние 5 вебхуков
curl -s http://localhost:8000/api/v1/webhooks/logs?limit=5 \
  -H "X-API-Key: your-secret-api-key-change-this" | jq .

# Вебхуки для конкретного триггера
curl -s "http://localhost:8000/api/v1/webhooks/logs?trigger_id=1&limit=10" \
  -H "X-API-Key: your-secret-api-key-change-this" | jq .
```

## Информация о подключении

- **MQTT брокер (внешний)**: `localhost:1883`
- **MQTT брокер (Docker)**: `mqtt-broker:1883`
- **WebSocket порт**: `9001` (не используется в текущей конфигурации)
- **Качество сервиса (QoS)**: 1
- **Топик подписки**: `iot/+/data`

## Устранение неполадок

### MQTT сообщения не обрабатываются

```bash
# Проверьте логи IoT-Core на ошибки
docker-compose logs iot-core | grep -i error

# Проверьте подключение MQTT listener
docker-compose logs iot-core | grep "Connected to MQTT broker"

# Проверьте, что device_id существует в базе
curl -s http://localhost:8000/api/v1/devices \
  -H "X-API-Key: your-secret-api-key-change-this" | jq '.[] | .id'
```

### Триггеры не срабатывают

```bash
# Проверьте Rule Engine работает
curl -s http://localhost:8000/health | jq .

# Проверьте логи Rule Engine
docker-compose logs iot-core | grep -i "rule_engine"

# Проверьте настройки триггера
curl -s http://localhost:8000/api/v1/triggers \
  -H "X-API-Key: your-secret-api-key-change-this" | jq .
```

### Перезапуск MQTT брокера

```bash
# Перезапуск только MQTT брокера
docker-compose restart mqtt-broker

# Полный перезапуск всех сервисов
docker-compose restart
```

## Проверка исправления (после бага с event loop)

До исправления была ошибка:
```
RuntimeError: no running event loop
```

После исправления в `mqtt_listener.py`:
- Добавлена ссылка на event loop в `__init__`
- Используется `asyncio.run_coroutine_threadsafe()` вместо `create_task()`
- Event loop сохраняется при старте в методе `start()`

Проверка:
```bash
# Логи НЕ должны содержать "no running event loop"
docker-compose logs iot-core | grep "running event loop"
```

---
**См. также:** [Ingestion модуль](../modules/ingestion.md) | [← Навигация](../index.md)
