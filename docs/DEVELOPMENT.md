# Development Guide

## Локальная разработка

### Установка зависимостей

```bash
# Создать виртуальное окружение
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# или
.\venv\Scripts\activate  # Windows

# Установить зависимости
pip install -r requirements.txt
```

### Запуск без Docker

```bash
# Копировать конфигурацию
cp .env.example .env

# Отредактировать .env
# Установить MQTT_BROKER_HOST=localhost если используете локальный MQTT брокер

# Запустить приложение
python -m app.main

# Или через uvicorn с hot reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Запуск MQTT брокера (Mosquitto)

```bash
# macOS
brew install mosquitto
mosquitto -c mosquitto/config/mosquitto.conf

# Linux
sudo apt-get install mosquitto
mosquitto -c mosquitto/config/mosquitto.conf

# Docker
docker run -p 1883:1883 -v $(pwd)/mosquitto/config:/mosquitto/config eclipse-mosquitto:2.0
```

## Docker разработка

### Сборка и запуск

```bash
# Сборка образа
docker-compose build

# Запуск
docker-compose up -d

# Просмотр логов
docker-compose logs -f

# Остановка
docker-compose down
```

### Пересборка после изменений

```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## Структура проекта

```
app/
├── __init__.py
├── main.py                 # Точка входа FastAPI
├── config.py              # Настройки приложения
├── database/              # Модели и подключение к БД
│   ├── __init__.py
│   ├── models.py         # SQLAlchemy модели
│   └── connection.py     # Управление подключением
├── drivers/               # Драйверы устройств
│   ├── __init__.py       # Реестр драйверов
│   ├── base.py           # Базовый интерфейс
│   ├── generic_json.py   # Generic JSON драйвер
│   ├── arduino_mq2.py    # Arduino MQ2 драйвер
│   └── arduino_button_dht11.py  # Arduino Button+DHT11 драйвер
└── modules/               # Функциональные модули
    ├── ingestion/         # Прием данных
    │   ├── http_listener.py
    │   └── mqtt_listener.py
    ├── storage/           # Хранение
    │   └── storage_service.py
    ├── engine/            # Rule Engine
    │   ├── rule_engine.py
    │   └── webhook_dispatcher.py
    └── api/               # REST API
        ├── routes.py
        └── middleware.py
```

## Добавление нового драйвера

### 1. Создать файл драйвера

```python
# app/drivers/my_custom_driver.py

from typing import Dict, List, Any
from app.drivers.base import BaseDriver

class MyCustomDriver(BaseDriver):
    driver_name = "my_custom"
    description = "My custom device driver"
    
    def validate(self, payload: Dict[str, Any]) -> bool:
        # Валидация формата данных
        return "data" in payload
    
    def parse(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        # Парсинг в нормализованный формат
        return [
            {"name": "metric1", "value": payload["data"]["value1"], "unit": None}
        ]
    
    def get_config_schema(self) -> Dict[str, Any]:
        # JSON Schema для конфигурации
        return {
            "type": "object",
            "properties": {
                "custom_param": {"type": "string"}
            }
        }
```

### 2. Зарегистрировать драйвер

```python
# app/drivers/__init__.py

from app.drivers.my_custom_driver import MyCustomDriver

# В классе DriverRegistry, метод _register_builtin_drivers
def _register_builtin_drivers(self):
    self.register(GenericJsonDriver)
    self.register(MyCustomDriver)  # Добавить
```

### 3. Использовать

При создании устройства указать `driver_type: "my_custom"`.

## Тестирование

### Создание тестового устройства через API

```bash
curl -X POST http://localhost:8000/api/v1/devices \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-api-key-change-this" \
  -d '{
    "name": "Test Sensor",
    "driver_type": "generic_json"
  }'
```

### Отправка тестовых данных (HTTP)

```bash
curl -X POST http://localhost:8000/api/v1/ingest/http \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "YOUR-DEVICE-UUID",
    "metrics": {
      "temperature": 25.5,
      "humidity": 60.0
    }
  }'
```

### Отправка тестовых данных (MQTT)

```bash
mosquitto_pub -h localhost -p 1883 \
  -t "iot/YOUR-DEVICE-UUID/data" \
  -m '{"metrics": {"temperature": 25.5}}'
```

### Создание триггера

```bash
curl -X POST http://localhost:8000/api/v1/triggers \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-api-key-change-this" \
  -d '{
    "name": "High Temp Alert",
    "device_id": "YOUR-DEVICE-UUID",
    "metric_name": "temperature",
    "condition": "> 30",
    "webhook_url": "https://webhook.site/YOUR-UNIQUE-URL"
  }'
```

## Отладка

### Просмотр логов

```bash
# Docker
docker-compose logs -f iot-core

# Локально
# Логи выводятся в stdout
```

### Проверка БД

```bash
# Войти в контейнер
docker-compose exec iot-core sh

# Открыть БД
sqlite3 /app/data/iot_core.db

# Посмотреть таблицы
.tables

# Примеры запросов
SELECT * FROM devices;
SELECT * FROM telemetry LIMIT 10;
SELECT * FROM triggers;
SELECT * FROM webhook_logs;
```

### Health Check

```bash
curl http://localhost:8000/health
```

## Мониторинг производительности

### Время обработки запросов

Каждый ответ содержит заголовок `X-Process-Time` с временем обработки в секундах.

### Очистка старых данных

Модуль Storage автоматически удаляет телеметрию старше TTL (по умолчанию 30 дней).

Для ручной очистки:

```python
from app.database import db
from app.modules.storage import StorageService

async with db.get_session() as session:
    storage = StorageService(session)
    deleted = await storage.cleanup_old_telemetry()
    print(f"Deleted {deleted} old records")
```

## Производственное развертывание

### Безопасность

1. **Изменить API ключ** в `.env`:
   ```
   API_KEY=your-strong-random-key
   ```

2. **Использовать SSL/TLS**:
   - Настроить reverse proxy (nginx) с SSL терминацией
   - Или настроить SSL в uvicorn

3. **Изменить пароли**:
   ```
   ADMIN_PASSWORD=strong-password
   WEBHOOK_SECRET=strong-secret
   ```

### Рекомендации

- Использовать PostgreSQL вместо SQLite для продакшена
- Настроить резервное копирование БД
- Использовать внешний MQTT брокер с аутентификацией
- Настроить мониторинг (Prometheus, Grafana)
- Логирование в файлы с ротацией

### Environment Variables для Production

```bash
APP_ENV=production
DEBUG=false
LOG_LEVEL=WARNING
DATABASE_PATH=/app/data/iot_core.db
API_KEY=<strong-random-key>
WEBHOOK_SECRET=<strong-secret>
```
