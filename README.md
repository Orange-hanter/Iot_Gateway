# IoT-Core MVP

Платформа для сбора телеметрических данных с IoT-устройств, централизованного хранения и автоматической реакции на события.

## Архитектура

Система построена по принципу **модульного монолита** с контейнеризацией (Docker).

### Модули

1. **Ingestion Module** - прием данных от устройств (HTTP, MQTT)
2. **Storage Module** - управление персистентным слоем (SQLite)
3. **Rule Engine Module** - анализ данных и управление триггерами
4. **API Gateway Module** - REST API для внешних интеграций
5. **Admin UI Module** - веб-интерфейс администрирования

## Быстрый старт

### Требования

- Docker Engine 20+
- Docker Compose v2+

### Запуск

```bash
# Копировать пример конфигурации
cp .env.example .env

# Запустить систему
docker-compose up -d

# Просмотр логов
docker-compose logs -f
```

### Доступ

- **API**: http://localhost:8000
- **Admin UI**: http://localhost:8000/admin
- **Health Check**: http://localhost:8000/health
- **MQTT Broker**: mqtt://localhost:1883

## API Endpoints

### Ingestion
- `POST /api/v1/ingest/http` - прием данных через HTTP

### Devices
- `GET /api/v1/devices` - список устройств
- `POST /api/v1/devices` - создание устройства
- `GET /api/v1/devices/{id}` - информация об устройстве
- `PUT /api/v1/devices/{id}` - обновление устройства
- `DELETE /api/v1/devices/{id}` - удаление устройства

### Telemetry
- `GET /api/v1/telemetry/{device_id}` - история показаний

### Triggers
- `GET /api/v1/triggers` - список правил
- `POST /api/v1/triggers` - создание правила
- `PUT /api/v1/triggers/{id}` - обновление правила
- `DELETE /api/v1/triggers/{id}` - удаление правила

### Webhooks
- `POST /api/v1/webhooks/test` - тестовая отправка вебхука

## Формат данных

### HTTP Ingestion

```json
{
  "device_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-03-08T10:00:00Z",
  "metrics": {
    "temperature": 25.5,
    "humidity": 60.0
  }
}
```

### MQTT Ingestion

Topic: `iot/{device_id}/data`

```json
{
  "timestamp": "2026-03-08T10:00:00Z",
  "metrics": {
    "temperature": 25.5,
    "humidity": 60.0
  }
}
```

## Безопасность

API защищен ключами. Передавайте ключ в заголовке:

```
X-API-Key: your-api-key-here
```

## Разработка

### Структура проекта

```
app/
├── main.py              # Точка входа
├── config.py            # Конфигурация
├── database/            # Модели и подключение к БД
├── modules/             # Функциональные модули
│   ├── ingestion/       # Прием данных
│   ├── storage/         # Хранение
│   ├── engine/          # Обработка правил
│   ├── api/             # REST API
│   └── admin/           # Админ-панель
└── drivers/             # Драйверы устройств
```

### Добавление нового драйвера

1. Создайте файл в `app/drivers/`
2. Наследуйтесь от `BaseDriver`
3. Реализуйте методы: `validate()`, `parse()`, `get_config_schema()`
4. Зарегистрируйте драйвер в `app/drivers/__init__.py`

## Лицензия

Proprietary
