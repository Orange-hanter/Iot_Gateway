# Arduino Button + BPM280 - Руководство

Интеграция Arduino-устройства с кнопкой, влажностью (BPM280) и температурой через абстрактную обертку.

## Что реализовано

- Новый драйвер: `arduino_button_bpm280`
- Метрики:
- `button_state` (0/1)
- `button_changed` (0/1)
- `humidity` (%)
- `temperature` (C, если доступна)
- `button_event` (1 на каждое отдельное нажатие)
- Прошивка: `arduino/button_bpm280/button_bpm280.ino`
- Мост для отправки в API: `arduino/bridge_button_bpm280.py`

## Важно про датчик температуры

Температурный сенсор сделан через обертку `TemperatureSensorAdapter` в драйвере и класс `TemperatureSensor` в Arduino-скетче.
Сейчас используется placeholder-реализация, чтобы позже можно было добавить конкретный сенсор без изменения контракта драйвера.

## Создание устройства

```bash
curl -X POST http://localhost:8000/api/v1/devices \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-api-key-change-this" \
  -d '{
    "name": "Button + BPM280",
    "driver_type": "arduino_button_bpm280",
    "config": {
      "location": "Lab #2",
      "humidity_sensor_type": "bpm280",
      "temperature_sensor_class": "generic"
    }
  }'
```

## Формат данных от Arduino

```json
{
  "type": "data",
  "sensor": "BUTTON_BPM280",
  "button": 1,
  "button_changed": true,
  "humidity": 45.2,
  "temperature": 24.6,
  "timestamp": 123456
}
```

## Запуск моста

```bash
python arduino/bridge_button_bpm280.py --device-id YOUR-DEVICE-UUID
```

С ручным портом:

```bash
python arduino/bridge_button_bpm280.py --device-id YOUR-DEVICE-UUID --port /dev/tty.usbmodem123
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
python arduino/test_button_bpm280_driver.py
```

Или с подключенным serial-портом:

```bash
python arduino/test_button_bpm280_driver.py --port /dev/tty.usbmodem123
```
