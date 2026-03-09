# Arduino Integration

Интеграция датчиков на базе Arduino с GatewayDemo.

## Содержание

- **mq2_sensor/** - Прошивка для датчика газа MQ2 на Arduino Mega
- **bridge.py** - Python скрипт для автоматической пересылки данных

## Быстрый старт

### 1. Прошивка Arduino

```bash
# Откройте mq2_sensor/mq2_sensor.ino в Arduino IDE
# Подключите Arduino Mega через USB
# Загрузите прошивку (Tools → Upload)
```

### 2. Создайте устройство в GatewayDemo

```bash
curl -X POST http://localhost:8000/api/v1/devices \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-api-key-change-this" \
  -d '{
    "name": "Gas Sensor MQ2",
    "driver_type": "arduino_mq2",
    "config": {
      "location": "Lab"
    }
  }'
```

Сохраните полученный `device_id`.

### 3. Запустите мост

```bash
# Установите зависимости
pip install pyserial requests

# Запустите мост (автопоиск Arduino)
python bridge.py --device-id YOUR-DEVICE-UUID

# Или укажите порт вручную
python bridge.py --device-id YOUR-DEVICE-UUID --port /dev/ttyUSB0
```

## Документация

Полная документация: [docs/ARDUINO_MQ2.md](../docs/ARDUINO_MQ2.md)

## Поддерживаемые датчики

- ✅ **MQ2** - Газы (LPG, пропан, метан, водород, дым)
- 🔄 MQ135 - Качество воздуха (в разработке)
- 🔄 DHT22 - Температура и влажность (в разработке)

## Требования

- Arduino Mega 2560 или совместимая
- USB кабель
- Python 3.8+
- pyserial, requests
