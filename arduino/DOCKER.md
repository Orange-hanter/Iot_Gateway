# Docker конфигурация для Arduino интеграции

## Контейнеризованный режим

### requirements.txt обновлен
✅ `pyserial==3.5` добавлен автоматически

Драйвер `arduino_mq2` будет доступен в контейнере.

## Режимы работы с Arduino

### Режим 1: Bridge вне контейнера (Рекомендуется)

Arduino Bridge работает на хост-машине и отправляет данные в контейнер через HTTP API.

**Преимущества:**
- ✅ Прямой доступ к USB без сложной настройки Docker
- ✅ Проще отлаживать
- ✅ Работает на любой ОС

**Использование:**

```bash
# На хост-машине
pip install pyserial requests
python arduino/bridge.py --device-id YOUR-DEVICE-UUID --api-url http://localhost:8000/api/v1/ingest/http
```

### Режим 2: Контейнер с доступом к USB

Дать контейнеру доступ к Serial портам.

**Для Linux:**

1. Отредактируйте `docker-compose.yml`, раскомментируйте нужные устройства:

```yaml
devices:
  - /dev/ttyUSB0:/dev/ttyUSB0  # ← Раскомментируйте
  - /dev/ttyACM0:/dev/ttyACM0  # ← Раскомментируйте
```

2. Добавьте пользователя в группу `dialout`:

```bash
sudo usermod -a -G dialout $USER
# Перезайдите в систему
```

3. Пересоберите контейнер:

```bash
docker-compose down
docker-compose up -d --build
```

4. Проверьте доступность устройств в контейнере:

```bash
docker exec -it iot-core-server ls -l /dev/tty*
```

**Для macOS:**

USB проброс в Docker Desktop требует дополнительной настройки:

```bash
# Используйте Boot2Docker или Docker Machine
# Или запускайте bridge.py на хосте (рекомендуется)
```

**Для Windows:**

```yaml
# В docker-compose.yml замените на Windows paths
devices:
  - COM3:COM3
```

### Режим 3: Privileged режим (Не рекомендуется)

⚠️ Дает полный доступ к системе (небезопасно)

```yaml
iot-core:
  privileged: true
```

## Пересборка контейнера

После обновления кода:

```bash
# Остановить контейнеры
docker-compose down

# Пересобрать с новыми зависимостями
docker-compose build --no-cache

# Запустить
docker-compose up -d

# Проверить логи
docker-compose logs -f iot-core
```

## Проверка драйвера в контейнере

```bash
# Список доступных драйверов
curl http://localhost:8000/api/v1/drivers \
  -H "X-API-Key: your-secret-api-key-change-this"

# Должен быть виден arduino_mq2
```

Ответ:
```json
{
  "drivers": {
    "generic_json": {...},
    "arduino_mq2": {
      "name": "arduino_mq2",
      "description": "Arduino Mega with MQ2 Gas Sensor (auto-discovery via Serial)"
    }
  }
}
```

## Troubleshooting

### Драйвер не виден

```bash
# Проверьте что pyserial установлен
docker exec -it iot-core-server pip list | grep pyserial

# Проверьте логи импорта
docker-compose logs iot-core | grep arduino
```

### USB устройство не доступно

```bash
# На хосте
ls -l /dev/ttyUSB* /dev/ttyACM*

# В контейнере
docker exec -it iot-core-server ls -l /dev/tty*

# Если не видно, используйте bridge на хосте
```

### Permission denied

```bash
# Добавьте пользователя в группу dialout
sudo usermod -a -G dialout $USER

# Или измените права на устройство
sudo chmod 666 /dev/ttyUSB0
```

## Рекомендуемая архитектура

```
┌─────────────────────────────────────────────┐
│  Host Machine                                │
│                                              │
│  ┌──────────────┐                            │
│  │   Arduino    │                            │
│  │   (USB)      │                            │
│  └───────┬──────┘                            │
│          │                                   │
│  ┌───────▼────────────────┐                  │
│  │  bridge.py             │                  │
│  │  (Python на хосте)     │                  │
│  └───────┬────────────────┘                  │
│          │ HTTP API                          │
│          │                                   │
│  ┌───────▼────────────────────────────────┐  │
│  │  Docker Container                      │  │
│  │  ┌──────────────────────────────────┐  │  │
│  │  │  GatewayDemo                     │  │  │
│  │  │  - HTTP API                      │  │  │
│  │  │  - MQTT                          │  │  │
│  │  │  - Rule Engine                   │  │  │
│  │  │  - Storage                       │  │  │
│  │  └──────────────────────────────────┘  │  │
│  └────────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

**Вывод:** Используйте `bridge.py` на хосте для максимальной простоты и надежности.

## Единый запуск всех bridge на хосте

Для масштабирования на несколько Arduino-драйверов используйте общий менеджер bridge-процессов:

1. Настройте реестр bridge:

```bash
cp scripts/bridges.conf.example scripts/bridges.conf
# Отредактируйте scripts/bridges.conf и укажите реальные device_id
```

2. Запустите все bridge одним скриптом:

```bash
./scripts/start_bridge_host.sh
```

3. Остановите все bridge одним скриптом:

```bash
./scripts/stop_bridge_host.sh
```

Формат `scripts/bridges.conf`:

```text
name|script_path|device_id|serial_port|baud_rate|api_url|api_key|extra_args
```

Пример двух bridge:

```text
mq2|arduino/bridge.py|<MQ2_DEVICE_ID>|-|115200|http://localhost:8000/api/v1/ingest/http|your-secret-api-key-change-this|-
button_dht11|arduino/bridge_button_dht11.py|<BUTTON_DHT11_DEVICE_ID>|-|115200|http://localhost:8000/api/v1/ingest/http|your-secret-api-key-change-this|-
```

## Схема данных BUTTON_DHT11 (согласованный контракт)

Для `button_dht11` bridge нормализует данные перед отправкой в API, чтобы драйвер получал стабильный формат.

Ключевые поля в `metrics`:
- `type`: `data`
- `sensor`: `BUTTON_DHT11`
- `button`, `button_changed`, `button_presses`, `button_event`, `timestamp`
- `humidity` (основное поле влажности)
- `temperature` (основная температура: приоритет DS18B20, fallback DHT11)
- `ds18b20_temperature` (если доступна)
- `dht11_temperature` (если доступна)
- `ds18b20_ok` (`true/false`)

Пример:

```json
{
  "device_id": "<BUTTON_DHT11_DEVICE_ID>",
  "metrics": {
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
}
```
