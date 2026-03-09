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
