---
tags: [guide, webhook]
---

# Webhook Receiver - Инструкция по тестированию

## Описание
Webhook Receiver - это отдельный сервис для приема и отображения вебхуков от IoT-Core.
Сервис выводит информацию о срабатывании триггеров в консоль.

## Архитектура
- **Порт**: 8001
- **Эндпоинт**: `http://webhook-receiver:8001/webhook` (внутри Docker сети)
- **Внешний доступ**: `http://localhost:8001`

## Команды для ручной проверки

### 1. Просмотр логов webhook-receiver в реальном времени
```bash
docker-compose logs -f webhook-receiver
```

### 2. Отправка тестовых данных для активации триггера
```bash
# Отправка данных с temperature > 30 (триггер сработает)
curl -X POST http://localhost:8000/api/v1/ingest/http \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-api-key-change-this" \
  -d '{
    "device_id": "d3fe6a60-8102-4fa6-a6c8-ea4bd8e8c019",
    "metrics": {
      "temperature": 35,
      "humidity": 65.0
    }
  }'
```

### 3. Полная проверка (отправка + просмотр логов)
```bash
# В одной команде
echo "📡 Отправка данных..." && \
curl -s -X POST http://localhost:8000/api/v1/ingest/http \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-api-key-change-this" \
  -d '{
    "device_id": "d3fe6a60-8102-4fa6-a6c8-ea4bd8e8c019",
    "metrics": {
      "temperature": 40,
      "humidity": 70.0
    }
  }' && \
echo "" && \
echo "⏳ Ожидание 6 секунд..." && sleep 6 && \
echo "📋 Логи webhook-receiver:" && \
docker-compose logs --tail=20 webhook-receiver
```

### 4. Проверка статуса всех сервисов
```bash
docker-compose ps
```

### 5. Просмотр последних вебхук-логов через API
```bash
curl -s http://localhost:8000/api/v1/webhooks/logs?limit=5 \
  -H "X-API-Key: your-secret-api-key-change-this" | jq .
```

### 6. Проверка health check webhook-receiver
```bash
curl http://localhost:8001/health
```

## Настройка триггера

Текущий триггер настроен следующим образом:
- **Условие**: `temperature > 30`
- **Webhook URL**: `http://webhook-receiver:8001/webhook`
- **Cooldown**: 10 секунд
- **Device ID**: `d3fe6a60-8102-4fa6-a6c8-ea4bd8e8c019`

### Изменение условия триггера
```bash
curl -X PUT http://localhost:8000/api/v1/triggers/1 \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-api-key-change-this" \
  -d '{
    "name": "Тест высокой температуры",
    "device_id": "d3fe6a60-8102-4fa6-a6c8-ea4bd8e8c019",
    "metric_name": "temperature",
    "condition": "> 25",
    "webhook_url": "http://webhook-receiver:8001/webhook",
    "cooldown_sec": 10,
    "is_active": true
  }'
```

## Пример вывода в консоли webhook-receiver

```
================================================================================
🔔 ТРИГГЕР СРАБОТАЛ! [2026-03-09 08:26:55]
================================================================================
📊 Триггер: Тест высокой температуры
🆔 Device ID: d3fe6a60-8102-4fa6-a6c8-ea4bd8e8c019
📈 Метрика: temperature = 35.0
⚙️  Условие: > 30
💬 Сообщение: Trigger 'Тест высокой температуры' fired: temperature > 30 (value: 35.0)
⏰ Timestamp: 2026-03-09T08:26:53.633509
================================================================================
```

## Остановка и перезапуск

```bash
# Остановка webhook-receiver
docker-compose stop webhook-receiver

# Запуск webhook-receiver
docker-compose start webhook-receiver

# Перезапуск с пересборкой
docker-compose up -d --build webhook-receiver

# Удаление
docker-compose down webhook-receiver
```

## Отладка

### Просмотр всех логов
```bash
docker-compose logs webhook-receiver
```

### Просмотр логов за последние 5 минут
```bash
docker-compose logs --since 5m webhook-receiver
```

### Вход в контейнер
```bash
docker exec -it iot-webhook-receiver sh
```

---
**См. также:** [Rule Engine](../modules/rule_engine.md) | [← Навигация](../index.md)
