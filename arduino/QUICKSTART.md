# Быстрый старт - Arduino MQ2

Минимальная инструкция для начала работы.

## За 5 минут

### 1. Подключите датчик

```
MQ2          Arduino Mega
VCC    →     5V
GND    →     GND
A0     →     A0
D0     →     Pin 2
```

### 2. Загрузите прошивку

1. Откройте `mq2_sensor/mq2_sensor.ino` в Arduino IDE
2. Выберите плату: Tools → Board → Arduino Mega 2560
3. Выберите порт: Tools → Port → (ваш порт)
4. Нажмите Upload

### 3. Создайте устройство

```bash
curl -X POST http://localhost:8000/api/v1/devices \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-api-key-change-this" \
  -d '{
    "name": "Gas Sensor",
    "driver_type": "arduino_mq2",
    "config": {"location": "Lab"}
  }'
```

Сохраните `device_id` из ответа!

### 4. Установите зависимости

```bash
pip install pyserial requests
```

### 5. Запустите мост

```bash
python bridge.py --device-id ВАШ-DEVICE-ID
```

## Готово! 🎉

Данные теперь автоматически отправляются в GatewayDemo.

Проверьте:
```bash
curl http://localhost:8000/api/v1/stats \
  -H "X-API-Key: your-secret-api-key-change-this" | jq
```

## Что дальше?

- [Полное руководство](../docs/ARDUINO_MQ2.md)
- [Создание триггеров](../docs/EXAMPLES.md)
- [Схема подключения](WIRING.md)
