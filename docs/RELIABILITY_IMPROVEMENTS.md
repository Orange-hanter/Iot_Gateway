# Улучшения надежности и отказоустойчивости системы

Дата: 10 марта 2026 г.

## Обзор изменений

Система была переработана для работы на отдельном сервере с повышенной отказоустойчивостью и способностью к самовосстановлению.

## 1. Улучшенный Startup и Service Recovery

### Изменения в `app/main.py`

- **Retry-логика при старте**: Критичные модули (MQTT Listener, Rule Engine) теперь стартуют с автоматическими повторными попытками (3 попытки с экспоненциальной задержкой).
- **Фоновый Watchdog**: Добавлен `_watchdog_task()` который каждые 30 секунд проверяет, живы ли критичные сервисы, и восстанавливает их при необходимости.
- **Статусная отслеживание**: Каждый сервис отслеживается через флаги в `ServiceStatus` классе.

**Файлы:**
- `app/main.py:70-100` - `_retry_async_operation()` функция
- `app/main.py:104-155` - `_watchdog_task()` функция
- `app/main.py:157-218` - Обновленный `lifespan()` с retry-логикой

## 2. Строгая health-проверка

### Изменения в `app/main.py`

- **503 при недоступности критичных сервисов**: Endpoint `/health` теперь возвращает HTTP `503` (Service Unavailable) если MQTT, Rule Engine или База данных недоступны.
- **Детальная информация о статусе**: Health response содержит информацию о готовности каждого компонента.

**Файлы:**
- `app/main.py:220-265` - Обновленный `health_check()` endpoint

**Использование:**
```bash
curl http://localhost:8000/health
```

## 3. Правильный Cooldown для триггеров

### Изменения в `app/modules/engine/rule_engine.py`

- **Обновление `last_triggered_at` только при успехе**: Ранее cooldown начинался даже при неудачной доставке вебхука. Теперь cooldown начнется только если webhook успешно отправлен.
- **Логирование попыток**: Добавлены детальные логи о статусе попыток отправки.

**Файлы:**
- `app/modules/engine/rule_engine.py:408-431` - Обновленная логика `_fire_webhook()`

**Эффект:** Если webhook временно недоступен (но будет доступен через 10 сек), триггер сможет переотправить сообщение без ожидания полного cooldown-периода.

## 4. Регулярный Cleanup старых данных

### Изменения в `app/modules/engine/rule_engine.py`

- **Фоновый cleanup-цикл**: Добавлен `_cleanup_loop()` который каждый час очищает:
  - Старую телеметрию (старше `telemetry_ttl_days` дней, по умолчанию 30 дней)
  - Обработанные очереди событий (старше 7 дней)
  
**Файлы:**
- `app/modules/engine/rule_engine.py:25-28` - Инициализация cleanup_task
- `app/modules/engine/rule_engine.py:40-58` - Обновленный `stop()` метод
- `app/modules/engine/rule_engine.py:60-90` - Новый `_cleanup_loop()` метод

**Эффект:** Предотвращает неконтролируемый рост БД и деградацию производительности на долгом аптайме.

## 5. MQTT с аутентификацией

### Изменения в конфигурации

- **Закрытый MQTT broker**: Mosquitto теперь требует аутентификацию (отключен `allow_anonymous`).
- **Автоинициализация пользователей**: Скрипт `mosquitto/init_users.sh` автоматически создает пользователей при первом запуске.
- **Переменные в переменных окружения**: Пароли для IoT-Core и Admin задаются через `.env`.

**Файлы:**
- `mosquitto/config/mosquitto.conf` - Обновленная конфигурация
- `mosquitto/init_users.sh` - Новый скрипт инициализации пользователей
- `app/config.py:40-47` - Параметры MQTT credentials
- `app/modules/ingestion/mqtt_listener.py:179-183` - Использование credentials

**Переменные окружения (в `.env`):**
```
MQTT_USERNAME=iot-core
MQTT_PASSWORD=ChangeThisPassword123!
MQTT_IOT_CORE_PASSWORD=ChangeThisPassword123!
MQTT_ADMIN_PASSWORD=ChangeThisAdminPassword456!
```

## 6. Docker Compose с улучшенной оркестрацией

### Изменения в `docker-compose.yml`

- **Health checks**: Добавлены healthcare checks для всех сервисов.
- **Правильный depends_on**: Используется `condition: service_healthy` для гарантии готовности зависимостей.
- **Автоинициализация Mosquitto**: MQTT broker инициализирует пользователей при старте.
- **Переменные окружения**: Пароли MQTT проходят через environment.

**Файлы:**
- `docker-compose.yml` - Полностью обновленный файл

**Команда для запуска:**
```bash
# Убедитесь что .env заполнен правильно
./rebuild.sh
docker-compose up -d
```

## 7. Буферизация данных в Arduino Bridge

### Изменения в Arduino скриптах

- **Локальный disk-buffer**: При недоступности API, bridge сохраняет данные локально в `./data/bridge_buffer/{device_id}/`.
- **Автоматическая переотправка**: Каждые 30 секунд bridge пытается переотправить буферизованные данные.
- **Статистика**: Отслеживается статус отправки, буферизации и переотправки.

**Файлы:**
- `arduino/bridge.py` - Полностью переработан с буферизацией
- `arduino/bridge_button_dht11.py` - Полностью переработан с буферизацией

**Как это работает:**
1. Device отправляет данные → Bridge пытается отправить в API
2. Если сеть/API недоступны → Данные сохраняются на диск
3. Каждые 30 сек bridge пытается переотправить буферизованные данные
4. При восстановлении связи → Все буферизованные данные переотправляются

**Пример использования:**
```bash
cd arduino
python bridge.py --device-id 550e8400-e29b-41d4-a716-446655440000 \
  --api-url http://192.168.1.100:8000/api/v1/ingest/http
```

## 8. Конфигурационные параметры

### Обновленные переменные в `.env.example`

Добавлены новые параметры для контроля reliability:

```env
# MQTT Authentication
MQTT_USERNAME=iot-core
MQTT_PASSWORD=change-this-mqtt-password
MQTT_IOT_CORE_PASSWORD=change-this-mqtt-password
MQTT_ADMIN_PASSWORD=change-this-admin-password

# Webhook Retry
WEBHOOK_TIMEOUT_SECONDS=10
WEBHOOK_MAX_RETRIES=3
WEBHOOK_RETRY_DELAY_SECONDS=2

# Rule Engine
RULE_ENGINE_POLL_INTERVAL_SECONDS=5
TRIGGER_COOLDOWN_SECONDS=60

# Telemetry
TELEMETRY_TTL_DAYS=30
```

## Мониторинг и диагностика

### Health Check эндпоинт

```bash
curl http://localhost:8000/health | jq
```

Ответ при нормальной работе:
```json
{
  "status": "healthy",
  "service": "IoT-Core",
  "version": "1.0.0",
  "database": "connected",
  "mqtt": "running",
  "rule_engine": "running",
  "services_ready": {
    "db": true,
    "mqtt": true,
    "rule_engine": true
  }
}
```

### Логи

```bash
# Все логи
docker-compose logs -f

# Только iot-core
docker-compose logs -f iot-core

# Только MQTT брокер
docker-compose logs -f mqtt-broker
```

## Развертывание на production

### Обязательные шаги

1. **Обновить все пароли в `.env`:**
   ```bash
   cp .env.example .env
   # Отредактируйте все "change-this" значения
   vi .env
   ```

2. **Пересобрать образы:**
   ```bash
   docker-compose build --no-cache
   ```

3. **Запустить систему:**
   ```bash
   docker-compose up -d
   ```

4. **Проверить здоровье:**
   ```bash
   curl http://localhost:8000/health
   docker-compose ps  # Должны быть healthy
   ```

### Резервное копирование

```bash
# Резервная копия БД
docker cp iot-core-server:/app/data/iot_core.db ./backups/iot_core.db.$(date +%Y%m%d_%H%M%S)

# Резервная копия конфигурации MQTT
docker cp iot-mqtt-broker:/mosquitto/config/mosquitto_passwd ./backups/
```

### Восстановление после сбоя

Система автоматически восстанавливается благодаря:
- Docker restart policy (`unless-stopped`)
- Внутреннему watchdog-таску с retry-логикой
- Persistent volumes для данных

## Тестирование надежности

### Тест: Отключение MQTT брокера

```bash
# Остановить MQTT брокер
docker-compose stop mqtt-broker

# Health check должен вернуть 503
curl http://localhost:8000/health

# Watchdog будет пытаться восстановить
docker-compose logs -f iot-core

# Перезапустить MQTT
docker-compose start mqtt-broker

# Система автоматически восстановит соединение
```

### Тест: Перегрузка системы

```bash
# Сгенерировать большой объем данных
for i in {1..1000}; do
  curl -X POST http://localhost:8000/api/v1/ingest/http \
    -H "X-API-Key: your-api-key" \
    -d '{"device_id":"test","metrics":{"temp":'$i'}}'
done

# Система будет пакетировать и очищать старые данные
# Health check должен остаться в норме
```

## Известные ограничения

1. **Single-host архитектура**: Система работает на одной машине. Для масштабирования требуется миграция на PostgreSQL + Kubernetes.

2. **In-memory rate limiting**: Rate limiting хранит данные в памяти (процесса Uvicorn), теряется при перезагрузке контейнера.

3. **SQLite блокировки**: При интенсивной нагрузке SQLite может конфликтовать на писсе. Рекомендуется мониторинг и планирование переноса на PostgreSQL при ~1M+ записей/день.

4. **Нет distributed cache**: Нет Redis/Memcached для кеширования, каждый запрос идет в БД.

## Дальнейшее улучшение (Phase 2)

- [ ] Миграция на PostgreSQL
- [ ] Добавить Redis для кеширования и DLQ (Dead Letter Queue)
- [ ] Distributed трейсинг (Jaeger, Datadog)
- [ ] Kubernetes deployment configs
- [ ] Backup/restore automation
- [ ] Metrics экспорт (Prometheus)

## Поддержка и проблемы

При возникновении проблем:

1. Проверьте здоровье: `curl http://localhost:8000/health`
2. Посмотрите логи: `docker-compose logs -f`
3. Проверьте disk space: `df -h` (особенно для `/data`)
4. Проверьте MQTT connection: `mosquitto_sub -h localhost -u iot-core -P <password> -t 'iot/#' -n -W 2`
