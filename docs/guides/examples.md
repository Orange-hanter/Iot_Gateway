---
tags: [guide, examples]
---

# Примеры использования IoT-Core API

## Пример 1: Добавление устройства и отправка данных

### 1. Создать устройство

```bash
curl -X POST http://localhost:8000/api/v1/devices \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-api-key-change-this" \
  -d '{
    "name": "Температурный датчик #1",
    "driver_type": "generic_json"
  }'
```

**Ответ:**
```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "name": "Температурный датчик #1",
  "driver_type": "generic_json",
  "config": null,
  "status": "active",
  "last_seen": null,
  "created_at": "2026-03-08T10:00:00Z"
}
```

Сохраните `id` устройства!

### 2. Отправить данные (HTTP)

```bash
# Замените DEVICE_ID на полученный UUID
curl -X POST http://localhost:8000/api/v1/ingest/http \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "metrics": {
      "temperature": 22.5,
      "humidity": 65.0
    }
  }'
```

### 3. Отправить данные (MQTT)

```bash
# Установите mosquitto-clients если нужно
# brew install mosquitto  # macOS
# sudo apt-get install mosquitto-clients  # Linux

mosquitto_pub -h localhost -p 1883 \
  -t "iot/a1b2c3d4-e5f6-7890-abcd-ef1234567890/data" \
  -m '{"metrics": {"temperature": 23.0, "humidity": 64.5}}'
```

### 4. Получить историю данных

```bash
curl "http://localhost:8000/api/v1/telemetry/a1b2c3d4-e5f6-7890-abcd-ef1234567890?limit=10" \
  -H "X-API-Key: your-secret-api-key-change-this"
```

---

## Пример 2: Создание триггера с webhook

### 1. Получить test webhook URL

Откройте https://webhook.site и скопируйте ваш уникальный URL.

### 2. Создать триггер

```bash
curl -X POST http://localhost:8000/api/v1/triggers \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-api-key-change-this" \
  -d '{
    "name": "Высокая температура",
    "device_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "metric_name": "temperature",
    "condition": "> 25",
    "webhook_url": "https://webhook.site/YOUR-UNIQUE-ID",
    "cooldown_sec": 60
  }'
```

### 3. Отправить данные для срабатывания триггера

```bash
curl -X POST http://localhost:8000/api/v1/ingest/http \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "metrics": {
      "temperature": 30.0
    }
  }'
```

Проверьте webhook.site - должен прийти POST запрос!

### 4. Просмотр логов вебхуков

```bash
curl "http://localhost:8000/api/v1/webhooks/logs?limit=10" \
  -H "X-API-Key: your-secret-api-key-change-this"
```

---

## Пример 3: Python клиент для отправки данных

```python
import requests
import time
import random
from datetime import datetime

DEVICE_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
API_URL = "http://localhost:8000/api/v1/ingest/http"

def send_telemetry(temperature, humidity):
    payload = {
        "device_id": DEVICE_ID,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "metrics": {
            "temperature": temperature,
            "humidity": humidity
        }
    }
    
    response = requests.post(API_URL, json=payload)
    print(f"Sent: temp={temperature}, hum={humidity} -> {response.status_code}")
    return response.json()

# Отправка данных каждые 5 секунд
while True:
    temp = 20 + random.uniform(-5, 10)
    hum = 60 + random.uniform(-10, 10)
    
    send_telemetry(round(temp, 1), round(hum, 1))
    time.sleep(5)
```

---

## Пример 4: MQTT клиент на Python

```python
import paho.mqtt.client as mqtt
import json
import time
import random
from datetime import datetime

MQTT_BROKER = "localhost"
MQTT_PORT = 1883
DEVICE_ID = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
TOPIC = f"iot/{DEVICE_ID}/data"

def on_connect(client, userdata, flags, rc):
    print(f"Connected to MQTT broker: {rc}")

def send_telemetry(client):
    payload = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "metrics": {
            "temperature": round(20 + random.uniform(-5, 10), 1),
            "humidity": round(60 + random.uniform(-10, 10), 1)
        }
    }
    
    client.publish(TOPIC, json.dumps(payload), qos=1)
    print(f"Published: {payload}")

# Создание клиента
client = mqtt.Client()
client.on_connect = on_connect
client.connect(MQTT_BROKER, MQTT_PORT, 60)

# Запуск loop в отдельном потоке
client.loop_start()

# Отправка данных
try:
    while True:
        send_telemetry(client)
        time.sleep(5)
except KeyboardInterrupt:
    client.loop_stop()
    client.disconnect()
```

---

## Пример 5: Использование Admin UI

1. Откройте http://localhost:8000/admin в браузере
2. **ВАЖНО:** Измените API_KEY в файле `static/admin/index.html` на ваш ключ из `.env`
3. В интерфейсе:
   - Добавьте устройства
   - Создайте триггеры
   - Просматривайте логи

---

## Пример 6: Тестирование webhook

```bash
curl -X POST http://localhost:8000/api/v1/webhooks/test \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-api-key-change-this" \
  -d '{
    "url": "https://webhook.site/YOUR-UNIQUE-ID",
    "payload": {
      "test": "Hello from IoT-Core!"
    }
  }'
```

---

## Пример 7: Фильтрация телеметрии

### Получить данные за последний час

```bash
START_TIME=$(date -u -v-1H +"%Y-%m-%dT%H:%M:%SZ")  # macOS
# START_TIME=$(date -u -d '1 hour ago' +"%Y-%m-%dT%H:%M:%SZ")  # Linux

curl "http://localhost:8000/api/v1/telemetry/${DEVICE_ID}?start_time=${START_TIME}" \
  -H "X-API-Key: your-secret-api-key-change-this"
```

### Получить только температуру

```bash
curl "http://localhost:8000/api/v1/telemetry/${DEVICE_ID}?metric_name=temperature&limit=50" \
  -H "X-API-Key: your-secret-api-key-change-this"
```

---

## Пример 8: Условия триггеров

```bash
# Больше чем
{"condition": "> 30"}

# Меньше чем
{"condition": "< 10"}

# Равно (с погрешностью)
{"condition": "== 25"}

# Не равно
{"condition": "!= 0"}

# Диапазон
{"condition": "20..25"}

# Больше или равно
{"condition": ">= 30"}

# Меньше или равно
{"condition": "<= 10"}
```

---

## Пример 9: Статистика системы

```bash
curl http://localhost:8000/api/v1/stats \
  -H "X-API-Key: your-secret-api-key-change-this"
```

---

## Пример 10: Создание Arduino Button+DHT11 устройства

```bash
curl -X POST http://localhost:8000/api/v1/devices \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-api-key-change-this" \
  -d '{
    "name": "Button + DHT11 #1",
    "driver_type": "arduino_button_dht11",
    "config": {
      "location": "Test Bench",
      "humidity_sensor_type": "dht11",
      "temperature_sensor_class": "generic"
    }
  }'
```

Триггер на каждое нажатие кнопки:

```bash
curl -X POST http://localhost:8000/api/v1/triggers \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-api-key-change-this" \
  -d '{
    "name": "Button press event",
    "device_id": "YOUR-DEVICE-UUID",
    "metric_name": "button_event",
    "condition": "== 1",
    "cooldown_sec": 0,
    "firebase_notification": {
      "url": "https://back.processnavigation.com/ci2e4kezb7/firebase-notifications/push-message",
      "title": "Кнопка нажата",
      "text": "Нажатие кнопки зафиксировано",
      "ids": [1]
    }
  }'
```

Отправка тестового payload через HTTP:

```bash
curl -X POST http://localhost:8000/api/v1/ingest/http \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "YOUR-DEVICE-UUID",
    "type": "data",
    "sensor": "BUTTON_DHT11",
    "button": 1,
    "button_changed": true,
    "temperature": 23.8,
    "humidity": 46.1
  }'
```

**Ответ:**
```json
{
  "devices_total": 5,
  "devices_active": 3,
  "triggers_total": 8,
  "telemetry_24h": 1523
}
```

---

## Пример 10: Получение списка драйверов

```bash
curl http://localhost:8000/api/v1/drivers \
  -H "X-API-Key: your-secret-api-key-change-this"
```

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

---
**См. также:** [API](../specs/api.md) | [← Навигация](../index.md)
