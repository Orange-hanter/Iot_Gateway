# Чеклист развертывания системы с улучшениями надежности

## ✅ Выполненные изменения

### Core Reliability (1-3)

- [x] **Graceful Startup с retry-логикой** 
  - Файл: `app/main.py`
  - MQTT Listener и Rule Engine повторяют старт 3 раза с экспоненциальной задержкой
  - Если стартовать не получится - контейнер остается живым, watchdog пытается восстановить

- [x] **Фоновый Watchdog для self-healing**
  - Файл: `app/main.py` (функция `_watchdog_task()`)
  - Каждые 30 секунд проверяет живость MQTT и Rule Engine
  - Автоматически восстанавливает упавшие сервисы

- [x] **Строгая health-проверка**
  - Файл: `app/main.py` (endpoint `/health`)
  - Возвращает HTTP 503 если MQTT, Rule Engine или БД недоступны
  - Отслеживает готовность каждого компонента

### Data Processing (4-5)

- [x] **Правильный Cooldown для триггеров**
  - Файл: `app/modules/engine/rule_engine.py`
  - `last_triggered_at` обновляется ТОЛЬКО при успешной отправке вебхука
  - Предотвращает потерю событий при временных сбоях доставки

- [x] **Регулярный Cleanup данных**
  - Файл: `app/modules/engine/rule_engine.py` (функция `_cleanup_loop()`)
  - Каждый час удаляет старую телеметрию (старше 30 дней)
  - Очищает обработанные очереди(старше 7 дней)

### Infrastructure (6-8)

- [x] **MQTT с аутентификацией**
  - Файлы: `mosquitto/config/mosquitto.conf`, `mosquitto/init_users.sh`
  - MQTT брокер требует учетные данные (пользователь + пароль)
  - Пароли из переменных окружения

- [x] **Улучшенная Docker оркестрация**
  - Файл: `docker-compose.yml`
  - Health checks для всех сервисов
  - Правильные зависимости с `condition: service_healthy`
  - Автоинициализация MQTT пользователей

- [x] **Буферизация данных в Arduino Bridge**
  - Файлы: `arduino/bridge.py`, `arduino/bridge_button_dht11.py`
  - Локальный disk buffer при недоступности API
  - Автоматическая переотправка каждые 30 сек

### Documentation

- [x] **Полная документация улучшений**
  - Файл: `docs/RELIABILITY_IMPROVEMENTS.md`
  - Описание каждого улучшения
  - Примеры использования и тестирования

## 📋 Перед production развертыванием

### 1. Обновить пароли и секреты

```bash
# Скопировать пример конфигурации
cp .env.example .env

# Отредактировать все пароли (замените "change-this" на настоящие пароли)
cat .env | grep "change-this"

# Ключевые переменные для изменения:
# - API_KEY
# - ADMIN_PASSWORD  
# - MQTT_PASSWORD
# - MQTT_IOT_CORE_PASSWORD
# - MQTT_ADMIN_PASSWORD
# - WEBHOOK_SECRET
```

### 2. Собрать Docker образы

```bash
docker-compose build --no-cache
```

### 3. Проверить конфигурацию MQTT

```bash
# Файл должен содержать:
cat mosquitto/config/mosquitto.conf
# allow_anonymous false
# password_file /mosquitto/config/mosquitto_passwd
```

### 4. Запустить систему

```bash
docker-compose up -d
```

### 5. Проверить здоровье всех сервисов

```bash
# Health check endpoint
curl -s http://localhost:8000/health | jq

# Все контейнеры должны быть "healthy"
docker-compose ps

# Должны вывести (примерно):
# STATUS: Up X seconds (healthy) - для iot-core-server
# STATUS: Up X seconds (healthy) - для iot-mqtt-broker
```

### 6. Проверить MQTT подключение

```bash
# Протестировать с новыми credentials
mosquitto_sub -h localhost \
  -u iot-core \
  -P "YOUR-MQTT-PASSWORD" \
  -t "iot/#" \
  -n -W 2

# Должно выдать: Connection successful
```

### 7. Проверить логи

```bash
# Смотреть логи всех сервисов
docker-compose logs -f

# Скопировать вывод в файл для анализа
docker-compose logs > systemstartup.log

# Проверить нет ли ошибок
docker-compose logs | grep -i "error\|fail"
```

## 🧪 Тестирование надежности

### Тест 1: Падение MQTT брокера и восстановление

```bash
# 1. Проверить что MQTT работает
curl http://localhost:8000/health | jq '.mqtt'
# Должно быть: "running"

# 2. Остановить MQTT
docker-compose stop mqtt-broker

# 3. Проверить health (должен вернуть 503)
curl http://localhost:8000/health | jq '.mqtt, .status, .message'

# 4. Смотреть логи - должны быть попытки восстановления
docker-compose logs iot-core | tail -20

# 5. Перезапустить MQTT
docker-compose start mqtt-broker

# 6. Подождать ~30 сек и проверить восстановление
sleep 30
curl http://localhost:8000/health | jq '.mqtt, .status'
# Должны вернуться к "running" и "healthy"
```

### Тест 2: Arduino Bridge буферизация

```bash
# 1. Остановить iot-core (имитация недоступности API)
docker-compose stop iot-core

# 2. Запустить Arduino bridge
cd arduino
python bridge.py --device-id test-device-123 \
  --api-url http://localhost:8000/api/v1/ingest/http

# 3. Bridge должен сохранить данные в буфер:
ls -la ./data/bridge_buffer/test-device-123/
# Должны появиться .pkl файлы

# 4. Перезапустить iot-core
docker-compose start iot-core

# 5. Bridge должен автоматически отправить буферизованные данные
# Проверить логи bridge - должны быть "Resent N buffered messages"

# 6. Буферизованные .pkl файлы должны удалиться после успешной отправки
ls -la ./data/bridge_buffer/test-device-123/
# Папка должна быть пуста (или не существовать)
```

### Тест 3: Cleanup старых данных

```bash
# После 1 часа работы системы, проверить логи cleanup:
docker-compose logs iot-core | grep "Cleanup"

# Должны быть логи типа:
# "Cleanup: deleted 1234 old telemetry records and 56 old queue items"
```

## 🔍 Мониторинг в production

### Daily checks

```bash
# 1. Здоровье системы
curl http://localhost:8000/health | jq

# 2. Размер БД
ls -lh data/iot_core.db*

# 3. Наличие буферов в bridges
du -sh ./data/bridge_buffer/

# 4. Свободное место на диске
df -h | grep -E '/|data'

# 5. Логи за последний час
docker-compose logs --since 1h | grep -E "ERROR|CRITICAL"
```

### Alerts to watch for

- ⚠️ Health endpoint возвращает 503
- ⚠️ MQTT disconnected в логах
- ⚠️ Rule Engine stopped
- ⚠️ Database error
- ⚠️ Disk space < 10%
- ⚠️ Large buffer accumulation (> 1GB)

## 📈 Performance tuning

### Если высокая нагрузка

```env
# Увеличить количество рабочих процессов
# В docker-compose.yml для iot-core:
command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# Увеличить rate limit если нужно
RATE_LIMIT_PER_MINUTE=300

# Уменьшить Rule Engine poll interval
RULE_ENGINE_POLL_INTERVAL_SECONDS=2
```

### Если медленная БД

```env
# Увеличить TTL cleanup (реже удалять старые данные)
TELEMETRY_TTL_DAYS=60

# Или уменьшить (чаще чистить):
TELEMETRY_TTL_DAYS=7

# Увеличить batch size в storage (если есть)
```

## 🆘 Troubleshooting

### Problem: Health check returns 503

**Решение:**
```bash
# 1. Проверить какой сервис упал
curl http://localhost:8000/health | jq '.services_ready'

# 2. Если mqtt: false
docker-compose logs mqtt-broker | tail -20
docker-compose restart mqtt-broker

# 3. Если rule_engine: false
docker-compose logs iot-core | tail -20
docker-compose restart iot-core

# 4. Если db: false
docker-compose logs iot-core | tail -20
# Проверить disk space
df -h /Users/dakh/Git/GatewayDemo/data

# 5. Если проблема persists, перезагрузить всё
docker-compose down
docker-compose up -d
sleep 30
curl http://localhost:8000/health
```

### Problem: Arduino bridge data loss

**Решение:**
```bash
# 1. Проверить буфер
ls -la ./data/bridge_buffer/

# 2. Убедиться что bridge запущен и видит буфер
# Должны быть логи: "Found X buffered messages, attempting to send..."

# 3. Проверить API доступность
curl http://localhost:8000/api/v1/ingest/http \
  -H "X-API-Key: your-key"

# 4. Если буфер не отправляется, проверить device существует
curl http://localhost:8000/api/v1/devices \
  -H "X-API-Key: your-key" | jq
```

### Problem: MQTT authentication fails

**Решение:**
```bash
# 1. Проверить что пароль файл создан
docker exec iot-mqtt-broker ls -la /mosquitto/config/mosquitto_passwd

# 2. Проверить пользователей
docker exec iot-mqtt-broker mosquitto_passwd -c /mosquitto/config/mosquitto_passwd iot-core <new-password>

# 3. Перезапустить брокер
docker-compose restart mqtt-broker

# 4. Проверить в .env что пароли совпадают
grep MQTT .env | grep PASSWORD
```

## 📊 Метрики для отслеживания

Рекомендуется добавить мониторинг:

- Uptime каждого контейнера
- Health endpoint response time (target: < 100ms)
- MQTT message rate (in/out)
- Rule Engine lag (очередь событий)
- Database size (alert если > 80% от лимита)
- Bridge buffer size (alert если > 100MB)

## Дальнейшие улучшения

После stabilизации production:
- [ ] Добавить Prometheus metrics экспорт
- [ ] Настроить Grafana dashboard
- [ ] Настроить alerting (PagerDuty, Slack)
- [ ] Automated backups в S3/GCS
- [ ] Kubernetes deployment configs
- [ ] PostgreSQL миграция (при >1M events/day)

---

**Автор:** GitHub Copilot  
**Дата:** 10 марта 2026 г.  
**Версия системы:** 1.0.0 (RC2 - Reliability Improvements)
