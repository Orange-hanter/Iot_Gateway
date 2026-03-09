# Arduino MQ2 Gas Sensor - Руководство по установке и использованию

Полное решение для интеграции датчика газа MQ2 на базе Arduino Mega с GatewayDemo.

## Содержание

1. [Требования](#требования)
2. [Подключение датчика](#подключение-датчика)
3. [Прошивка Arduino](#прошивка-arduino)
4. [Установка драйвера](#установка-драйвера)
5. [Настройка устройства](#настройка-устройства)
6. [Использование](#использование)
7. [Тестирование](#тестирование)

---

## Требования

### Аппаратное обеспечение

- Arduino Mega 2560
- Датчик газа MQ2
- USB кабель (Type-A to Type-B для Mega)
- Провода для подключения

### Программное обеспечение

- Arduino IDE (1.8.x или 2.x)
- Python 3.8+
- pyserial (`pip install pyserial`)

---

## Подключение датчика

### Схема подключения MQ2 к Arduino Mega

```
MQ2 Sensor          Arduino Mega
-----------         ------------
VCC        -------> 5V
GND        -------> GND
A0 (Analog)-------> A0
D0 (Digital)------> Pin 2
```

### Описание пинов

- **VCC**: Питание 5V
- **GND**: Земля
- **A0**: Аналоговый выход (0-1023) - пропорционален концентрации газа
- **D0**: Цифровой выход (HIGH при превышении порога)

### Важно!

⚠️ **Датчик MQ2 требует прогрева 24-48 часов для стабильной работы.**  
Первые несколько часов показания могут быть неточными. Прошивка автоматически выполняет 30-секундный прогрев при старте.

---

## Прошивка Arduino

### Шаг 1: Откройте Arduino IDE

Скачайте и установите [Arduino IDE](https://www.arduino.cc/en/software).

### Шаг 2: Загрузите скетч

1. Откройте файл `arduino/mq2_sensor/mq2_sensor.ino`
2. Подключите Arduino Mega к компьютеру через USB
3. Выберите плату: **Tools → Board → Arduino Mega 2560**
4. Выберите порт: **Tools → Port → /dev/ttyUSB0** (Linux/Mac) или **COM3** (Windows)
5. Нажмите **Upload** (стрелка вправо)

### Шаг 3: Проверьте работу

1. Откройте Serial Monitor: **Tools → Serial Monitor**
2. Установите скорость: **115200 baud**
3. Вы должны увидеть JSON-сообщения от Arduino:

```json
{"type":"handshake","device_id":"ARDUINO_MQ2","firmware":"1.0.0","sensor":"MQ2"}
{"status":"warming_up","duration_sec":30}
{"status":"ready"}
{"type":"data","sensor":"MQ2","analog":512,"digital":0,"voltage":2.500,"resistance":10.50,"ratio":1.065,"ppm":95.23,"alert":false,"timestamp":35000}
```

---

## Установка драйвера

### Шаг 1: Установите зависимости

```bash
cd /Users/dakh/Git/GatewayDemo
pip install -r requirements.txt
```

Это установит `pyserial` для работы с Serial портом.

### Шаг 2: Проверьте регистрацию драйвера

Драйвер `arduino_mq2` уже зарегистрирован в системе. Проверьте:

```bash
curl http://localhost:8000/api/v1/drivers \
  -H "X-API-Key: your-secret-api-key-change-this"
```

Ответ должен содержать:

```json
{
  "drivers": {
    "arduino_mq2": {
      "name": "arduino_mq2",
      "description": "Arduino Mega with MQ2 Gas Sensor (auto-discovery via Serial)"
    }
  }
}
```

---

## Настройка устройства

### Автоматическое обнаружение Arduino

Драйвер умеет автоматически находить Arduino в системе. Создайте устройство:

```bash
curl -X POST http://localhost:8000/api/v1/devices \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-api-key-change-this" \
  -d '{
    "name": "Gas Sensor - Office",
    "driver_type": "arduino_mq2",
    "config": {
      "location": "Office Room 204",
      "auto_connect": false,
      "polling_interval": 2.0,
      "gas_threshold_ppm": 300.0
    }
  }'
```

### Ручное указание порта

Если нужно указать конкретный порт:

```bash
curl -X POST http://localhost:8000/api/v1/devices \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-api-key-change-this" \
  -d '{
    "name": "Gas Sensor - Kitchen",
    "driver_type": "arduino_mq2",
    "config": {
      "location": "Kitchen",
      "serial_port": "/dev/ttyUSB0",
      "auto_connect": false,
      "gas_threshold_ppm": 400.0
    }
  }'
```

**Примеры портов:**
- Linux: `/dev/ttyUSB0`, `/dev/ttyACM0`
- macOS: `/dev/tty.usbserial-*`, `/dev/tty.usbmodem*`
- Windows: `COM3`, `COM4`

---

## Использование

### Режим 1: Прямая отправка данных (HTTP)

Arduino отправляет данные через Serial, а вы пересылаете их через HTTP API:

```bash
curl -X POST http://localhost:8000/api/v1/ingest/http \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "YOUR-DEVICE-UUID",
    "type": "data",
    "sensor": "MQ2",
    "analog": 512,
    "digital": 0,
    "voltage": 2.5,
    "resistance": 10.5,
    "ratio": 1.065,
    "ppm": 95.23,
    "alert": false,
    "timestamp": 35000
  }'
```

### Режим 2: Python скрипт-мост

Создайте скрипт для автоматической пересылки данных:

```python
import serial
import requests
import json
import time

DEVICE_ID = "YOUR-DEVICE-UUID"
API_URL = "http://localhost:8000/api/v1/ingest/http"
API_KEY = "your-secret-api-key-change-this"
SERIAL_PORT = "/dev/ttyUSB0"
BAUD_RATE = 115200

# Подключение к Arduino
ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=2)
time.sleep(2)  # Ждем инициализации

print(f"Connected to Arduino on {SERIAL_PORT}")

try:
    while True:
        if ser.in_waiting:
            line = ser.readline().decode().strip()
            
            try:
                data = json.loads(line)
                
                # Отправляем только данные (не handshake)
                if data.get("type") == "data":
                    data["device_id"] = DEVICE_ID
                    
                    response = requests.post(
                        API_URL,
                        json=data,
                        headers={"X-API-Key": API_KEY}
                    )
                    
                    if response.status_code == 200:
                        print(f"✓ Sent: PPM={data['ppm']:.2f}")
                    else:
                        print(f"✗ Error: {response.status_code}")
                        
            except json.JSONDecodeError:
                pass  # Игнорируем некорректный JSON
                
except KeyboardInterrupt:
    print("\nStopping...")
finally:
    ser.close()
```

Сохраните как `bridge.py` и запустите:

```bash
python bridge.py
```

---

## Тестирование

### 1. Проверка Serial-соединения

```python
from app.drivers.arduino_mq2 import ArduinoMQ2Driver

driver = ArduinoMQ2Driver()

# Поиск Arduino
ports = driver.discover_arduino_ports()
print("Found Arduino ports:", ports)

# Подключение
if driver.connect_to_arduino():
    print("Connected!")
    
    # Чтение данных
    data = driver.read_from_arduino(timeout=10)
    if data:
        print("Received data:", data)
        
        # Парсинг
        metrics = driver.parse(data)
        print("Parsed metrics:", metrics)
    
    driver.disconnect_from_arduino()
```

### 2. Создание триггера для высокой концентрации газа

```bash
curl -X POST http://localhost:8000/api/v1/triggers \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-api-key-change-this" \
  -d '{
    "name": "High Gas Alert",
    "device_id": "YOUR-DEVICE-UUID",
    "metric_name": "gas_ppm",
    "condition": "greater_than",
    "threshold": 300.0,
    "webhook_url": "http://localhost:3001/webhook"
  }'
```

### 3. Просмотр статистики

```bash
curl http://localhost:8000/api/v1/stats \
  -H "X-API-Key: your-secret-api-key-change-this" | jq
```

---

## Метрики

Драйвер извлекает следующие метрики:

| Название | Единицы | Описание |
|----------|---------|----------|
| `gas_ppm` | ppm | Концентрация газа (основная метрика) |
| `gas_analog` | - | Сырое значение АЦП (0-1023) |
| `gas_voltage` | V | Напряжение на датчике |
| `gas_resistance` | kOhm | Сопротивление датчика |
| `gas_ratio` | - | Отношение Rs/R0 |
| `gas_alert` | - | Цифровой сигнал тревоги (0 или 1) |

---

## Калибровка

### Калибровка в чистом воздухе

Для точных измерений нужно откалибровать датчик:

1. Разместите датчик в чистом воздухе на 24 часа
2. Запишите среднее значение `gas_resistance`
3. Обновите `RO_CLEAN_AIR` в прошивке:

```cpp
const float RO_CLEAN_AIR = 9.83;  // Замените на ваше значение
```

4. Перепрошейте Arduino

### Определение типа газа

MQ2 чувствителен к разным газам. Коэффициенты для расчета PPM:

- **LPG**: `PPM = 613.9 * ratio^(-2.074)`
- **Метан**: `PPM = 778.9 * ratio^(-2.518)`
- **Дым**: `PPM = 197.2 * ratio^(-1.640)`
- **Водород**: `PPM = 987.9 * ratio^(-2.356)`

Текущая прошивка настроена на **LPG**.

---

## Устранение неполадок

### Arduino не обнаруживается

1. Убедитесь, что драйверы USB установлены (для CH340/CH341 чипов)
2. Проверьте права доступа (Linux):
   ```bash
   sudo usermod -a -G dialout $USER
   # Перезайдите в систему
   ```
3. Вручную укажите порт в конфигурации

### Нестабильные показания

1. Датчик требует прогрева (24-48 часов)
2. Проверьте качество соединений
3. Убедитесь, что питание стабильно (5V)

### Нет данных в Serial Monitor

1. Проверьте скорость: должно быть **115200 baud**
2. Проверьте подключение USB
3. Перезагрузите Arduino (кнопка RESET)

---

## Команды Arduino

Прошивка поддерживает команды через Serial:

- `PING` → `{"response":"PONG"}`
- `INFO` → Информация о устройстве
- `READ` → Запрос данных
- `LED_ON` → Включить встроенный LED
- `LED_OFF` → Выключить LED

Пример:

```bash
echo "PING" > /dev/ttyUSB0
```

---

## Дополнительные ресурсы

- [Datasheet MQ2](https://www.pololu.com/file/0J309/MQ2.pdf)
- [Arduino Mega Pinout](https://www.arduino.cc/en/Hacking/PinMapping2560)
- [GatewayDemo API Documentation](../API.md)

---

## Автор

Создано для проекта GatewayDemo
