# API Documentation

## Аутентификация

Все API запросы (кроме `/health` и `/docs`) требуют заголовок с API ключом:

```
X-API-Key: your-api-key-here
```

API ключ задается в переменной окружения `API_KEY` (см. `.env` файл).

## Endpoints

### Ingestion

#### POST /api/v1/ingest/http

Прием телеметрических данных через HTTP.

**Запрос:**
```json
{
  "device_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-03-08T10:00:00Z",
  "metrics": {
    "temperature": 25.5,
    "humidity": 60.0
  }
}
```

**Ответ (200):**
```json
{
  "success": true,
  "message": "Data ingested successfully",
  "metrics_count": 2
}
```

**Ошибки:**
- `404`: Устройство не найдено
- `403`: Устройство неактивно
- `400`: Некорректный формат данных
- `413`: Payload слишком большой

---

### Devices

#### GET /api/v1/devices

Получить список всех устройств.

**Параметры:**
- `status` (optional): Фильтр по статусу (`active`, `inactive`, `error`)

**Ответ:**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Temperature Sensor #1",
    "driver_type": "generic_json",
    "config": null,
    "status": "active",
    "last_seen": "2026-03-08T10:00:00Z",
    "created_at": "2026-03-01T12:00:00Z"
  }
]
```

#### POST /api/v1/devices

Создать новое устройство.

**Запрос:**
```json
{
  "name": "My Temperature Sensor",
  "driver_type": "generic_json",
  "config": {}
}
```

**Ответ (201):**
```json
{
  "id": "generated-uuid",
  "name": "My Temperature Sensor",
  "driver_type": "generic_json",
  "config": {},
  "status": "active",
  "last_seen": null,
  "created_at": "2026-03-08T10:00:00Z"
}
```

#### GET /api/v1/devices/{device_id}

Получить информацию об устройстве.

#### PUT /api/v1/devices/{device_id}

Обновить устройство.

#### DELETE /api/v1/devices/{device_id}

Удалить устройство.

---

### Telemetry

#### GET /api/v1/telemetry/{device_id}

Получить историю телеметрии для устройства.

**Параметры:**
- `start_time` (optional): Начало временного диапазона (ISO 8601)
- `end_time` (optional): Конец временного диапазона (ISO 8601)
- `metric_name` (optional): Фильтр по имени метрики
- `limit` (optional): Максимальное количество записей (по умолчанию 1000)

**Ответ:**
```json
[
  {
    "id": 123,
    "device_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2026-03-08T10:00:00Z",
    "metric_name": "temperature",
    "value": 25.5,
    "unit": "C"
  }
]
```

---

### Triggers

#### GET /api/v1/triggers

Получить список триггеров.

**Параметры:**
- `device_id` (optional): Фильтр по устройству
- `is_active` (optional): Фильтр по статусу

**Ответ:**
```json
[
  {
    "id": 1,
    "name": "High Temperature Alert",
    "device_id": "550e8400-e29b-41d4-a716-446655440000",
    "metric_name": "temperature",
    "condition": "> 30",
    "webhook_url": "https://example.com/webhook",
    "cooldown_sec": 60,
    "is_active": true,
    "last_triggered_at": null,
    "created_at": "2026-03-01T12:00:00Z"
  }
]
```

#### POST /api/v1/triggers

Создать новый триггер.

**Запрос:**
```json
{
  "name": "High Temperature Alert",
  "device_id": "550e8400-e29b-41d4-a716-446655440000",
  "metric_name": "temperature",
  "condition": "> 30",
  "webhook_url": "https://example.com/webhook",
  "cooldown_sec": 60,
  "is_active": true
}
```

**Условия:**
- `> 30` - больше 30
- `< 20` - меньше 20
- `>= 25` - больше или равно 25
- `<= 15` - меньше или равно 15
- `== 10` или `= 10` - равно 10
- `!= 5` - не равно 5
- `10..30` - в диапазоне от 10 до 30

#### PUT /api/v1/triggers/{trigger_id}

Обновить триггер.

#### DELETE /api/v1/triggers/{trigger_id}

Удалить триггер.

---

### Webhooks

#### POST /api/v1/webhooks/test

Тестовая отправка вебхука.

**Запрос:**
```json
{
  "url": "https://example.com/webhook",
  "payload": {
    "test": "data"
  }
}
```

**Ответ:**
```json
{
  "success": true,
  "status_code": 200,
  "error_message": null
}
```

#### GET /api/v1/webhooks/logs

Получить журнал отправленных вебхуков.

**Параметры:**
- `trigger_id` (optional): Фильтр по триггеру
- `limit` (optional): Максимальное количество записей (по умолчанию 100)

---

### System

#### GET /api/v1/drivers

Получить список доступных драйверов устройств.

**Ответ:**
```json
{
  "drivers": {
    "generic_json": {
      "name": "generic_json",
      "description": "Universal JSON driver for simple key-value metrics"
    }
  }
}
```

#### GET /api/v1/stats

Получить статистику системы.

**Ответ:**
```json
{
  "devices_total": 5,
  "devices_active": 3,
  "triggers_total": 10,
  "telemetry_24h": 1523
}
```

#### GET /health

Health check endpoint (без аутентификации).

**Ответ:**
```json
{
  "status": "healthy",
  "service": "IoT-Core",
  "version": "1.0.0",
  "database": "connected",
  "mqtt": "running",
  "rule_engine": "running"
}
```

---

## MQTT Interface

### Топик для отправки данных

```
iot/{device_id}/data
```

### Формат сообщения

```json
{
  "timestamp": "2026-03-08T10:00:00Z",
  "metrics": {
    "temperature": 25.5,
    "humidity": 60.0
  }
}
```

### Пример публикации (mosquitto_pub)

```bash
mosquitto_pub -h localhost -p 1883 \
  -t "iot/550e8400-e29b-41d4-a716-446655440000/data" \
  -m '{"metrics": {"temperature": 25.5, "humidity": 60.0}}'
```

---

## Webhook Payload

При срабатывании триггера на указанный URL отправляется POST запрос:

```json
{
  "trigger_id": 1,
  "trigger_name": "High Temperature Alert",
  "device_id": "550e8400-e29b-41d4-a716-446655440000",
  "metric": "temperature",
  "value": 35.5,
  "condition": "> 30",
  "timestamp": "2026-03-08T10:00:00Z",
  "message": "Trigger 'High Temperature Alert' fired: temperature > 30 (value: 35.5)"
}
```

**Заголовки:**
- `Content-Type: application/json`
- `User-Agent: IoT-Core/IoT-Core`

---

## Rate Limiting

API защищен от перегрузки:

- Максимум 60 запросов в минуту с одного IP (по умолчанию)
- При превышении возвращается `429 Too Many Requests`
- Информация о лимитах в заголовках:
  - `X-RateLimit-Limit`: Лимит запросов
  - `X-RateLimit-Remaining`: Оставшиеся запросы

---

## Коды ошибок

- `200` - Успешно
- `201` - Создано
- `204` - Успешно, нет содержимого
- `400` - Некорректный запрос
- `401` - Требуется аутентификация
- `403` - Доступ запрещен
- `404` - Не найдено
- `409` - Конфликт (дубликат)
- `413` - Payload слишком большой
- `429` - Превышен лимит запросов
- `500` - Внутренняя ошибка сервера
- `503` - Сервис недоступен
