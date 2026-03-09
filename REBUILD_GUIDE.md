# 🔄 Обновление Docker контейнера

После добавления нового драйвера Arduino MQ2 выполнено:

## ✅ Что изменено

### 1. Обновлен requirements.txt
- ✅ Добавлен `pyserial==3.5` для работы с Serial портами

### 2. Зарегистрирован драйвер
- ✅ `arduino_mq2` добавлен в [app/drivers/__init__.py](app/drivers/__init__.py)
- ✅ Автоматически загружается при старте контейнера

### 3. Обновлен docker-compose.yml
- ✅ Добавлены комментарии про USB устройства
- ✅ Инструкции по настройке для Linux/macOS/Windows

### 4. Создана документация
- ✅ [arduino/DOCKER.md](arduino/DOCKER.md) - Docker интеграция
- ✅ [docker-compose.override.yml.example](docker-compose.override.yml.example) - примеры настройки

### 5. Добавлены скрипты
- ✅ [rebuild.sh](rebuild.sh) - автоматическая пересборка
- ✅ [arduino/Dockerfile.bridge](arduino/Dockerfile.bridge) - контейнер для bridge

## 🚀 Как пересобрать контейнер

### Метод 1: Автоматический (рекомендуется)

```bash
./rebuild.sh
```

Скрипт автоматически:
1. Остановит контейнеры
2. Пересоберет с новыми зависимостями
3. Запустит контейнеры
4. Проверит health
5. Проверит регистрацию драйвера `arduino_mq2`

### Метод 2: Вручную

```bash
# Остановить
docker-compose down

# Пересобрать (без кеша для гарантии)
docker-compose build --no-cache iot-core

# Запустить
docker-compose up -d

# Проверить логи
docker-compose logs -f iot-core
```

## ✅ Проверка

### 1. Проверить что контейнер запущен

```bash
docker-compose ps
```

Должно быть:
```
NAME                    STATUS
iot-core-server        Up (healthy)
iot-mqtt-broker        Up
iot-webhook-receiver   Up
```

### 2. Проверить драйверы

```bash
curl http://localhost:8000/api/v1/drivers \
  -H "X-API-Key: your-secret-api-key-change-this" | jq
```

В ответе должен быть `arduino_mq2`:

```json
{
  "drivers": {
    "generic_json": {
      "name": "generic_json",
      "description": "Universal JSON driver for simple key-value metrics"
    },
    "arduino_mq2": {
      "name": "arduino_mq2",
      "description": "Arduino Mega with MQ2 Gas Sensor (auto-discovery via Serial)"
    }
  }
}
```

### 3. Проверить pyserial в контейнере

```bash
docker exec iot-core-server pip list | grep pyserial
```

Должно вывести: `pyserial    3.5`

## 📖 Режимы работы с Arduino

### Режим 1: Bridge на хосте (рекомендуется) ⭐

Arduino подключен к хост-машине, bridge.py работает локально:

```bash
# На хост-машине (не в контейнере)
pip install pyserial requests
python arduino/bridge.py --device-id YOUR-DEVICE-UUID
```

**Преимущества:**
- ✅ Проще в настройке
- ✅ Прямой доступ к USB
- ✅ Работает на любой ОС

### Режим 2: Контейнер с USB доступом

Для Linux можно дать контейнеру доступ к USB:

1. Раскомментируйте в `docker-compose.yml`:

```yaml
devices:
  - /dev/ttyUSB0:/dev/ttyUSB0
```

2. Пересоберите:

```bash
docker-compose down
docker-compose up -d
```

Подробнее: [arduino/DOCKER.md](arduino/DOCKER.md)

## 🔍 Устранение проблем

### Драйвер не отображается

```bash
# Проверьте импорт
docker-compose logs iot-core | grep -i arduino

# Перезапустите с полной пересборкой
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### pyserial не установлен

```bash
# Проверьте requirements.txt
cat requirements.txt | grep pyserial

# Должно быть: pyserial==3.5

# Пересоберите если отсутствует
./rebuild.sh
```

### Контейнер не запускается

```bash
# Смотрите логи
docker-compose logs iot-core

# Проверьте health
curl http://localhost:8000/health
```

## 📚 Следующие шаги

1. ✅ Контейнер пересобран
2. → Загрузите прошивку в Arduino: [arduino/mq2_sensor/mq2_sensor.ino](arduino/mq2_sensor/mq2_sensor.ino)
3. → Создайте устройство через API
4. → Запустите bridge: `python arduino/bridge.py --device-id YOUR-ID`
5. → Настройте триггеры

Полная инструкция: [docs/ARDUINO_MQ2.md](docs/ARDUINO_MQ2.md)  
Быстрый старт: [arduino/QUICKSTART.md](arduino/QUICKSTART.md)
