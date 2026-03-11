# Arduino Button + DHT11 - Руководство

Интеграция Arduino-устройства с кнопкой, влажностью (DHT11) и температурой через абстрактную обертку.

## Что реализовано

- Новый драйвер: `arduino_button_dht11`
- Метрики:
- `button_state` (0/1)
- `button_changed` (0/1)
- `humidity` (%)
- `temperature` (C, если доступна)
- `button_event` (1 на каждое отдельное нажатие)
- Прошивка: `arduino/button_dht11/button_dht11.ino`
- Мост для отправки в API: `arduino/bridge_button_dht11.py`

## Важно про датчик температуры

Температурный сенсор сделан через обертку `TemperatureSensorAdapter` в драйвере и класс `TemperatureSensor` в Arduino-скетче.
Сейчас используется placeholder-реализация, чтобы позже можно было добавить конкретный сенсор без изменения контракта драйвера.

## Создание устройства

```bash
curl -X POST http://localhost:8000/api/v1/devices \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-api-key-change-this" \
  -d '{
    "name": "Button + DHT11",
    "driver_type": "arduino_button_dht11",
    "config": {
      "location": "Lab #2",
      "humidity_sensor_type": "dht11",
      "temperature_sensor_class": "generic"
    }
  }'
```

## Формат данных от Arduino

```json
{
  "type": "data",
  "sensor": "BUTTON_DHT11",
  "button": 1,
  "button_changed": true,
  "humidity": 45.2,
  "temperature": 24.6,
  "timestamp": 123456
}
```

## Согласованная схема передачи (Firmware -> Bridge -> API)

Bridge в [arduino/bridge_button_dht11.py](arduino/bridge_button_dht11.py) нормализует payload перед отправкой в API, чтобы драйвер получал стабильный контракт.

Нормализованные поля:
- `type`: всегда `data`
- `sensor`: всегда `BUTTON_DHT11`
- `humidity`: основное поле влажности (`dht11_humidity` маппится в `humidity`)
- `temperature`: основная температура (приоритет `ds18b20_temperature`, fallback `dht11_temperature`)
- `ds18b20_temperature`: температура DS18B20 (если доступна)
- `dht11_temperature`: температура DHT11 (если доступна)
- `ds18b20_ok`: флаг корректности DS18B20 (`true/false`)
- `button`, `button_changed`, `button_presses`, `button_event`, `timestamp`

Пример нормализованного payload в `metrics`:

```json
{
  "type": "data",
  "sensor": "BUTTON_DHT11",
  "button": 1,
  "button_changed": true,
  "button_presses": 1,
  "button_event": 1,
  "humidity": 45.2,
  "temperature": 24.6,
  "ds18b20_temperature": 24.6,
  "dht11_temperature": 24.1,
  "ds18b20_ok": true,
  "timestamp": 123456
}
```

Драйвер сохраняет метрики:
- `button_state`
- `button_changed`
- `button_presses`
- `button_event`
- `humidity`
- `temperature`
- `ds18b20_temperature`
- `dht11_temperature`
- `ds18b20_ok`

## Запуск моста

```bash
python arduino/bridge_button_dht11.py --device-id YOUR-DEVICE-UUID
```

С ручным портом:

```bash
python arduino/bridge_button_dht11.py --device-id YOUR-DEVICE-UUID --port /dev/tty.usbmodem123
```

## Триггер на каждое нажатие кнопки

Для сценария "сработать каждый раз при нажатии" используйте метрику `button_event`.

Параметры триггера:
- `metric_name`: `button_event`
- `condition`: `== 1`
- `cooldown_sec`: `0`

Пример создания:

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
      "text": "Зафиксировано новое нажатие",
      "ids": [1]
    }
  }'
```

## Быстрый тест драйвера

```bash
python arduino/test_button_dht11_driver.py
```

Или с подключенным serial-портом:

```bash
python arduino/test_button_dht11_driver.py --port /dev/tty.usbmodem123
```
