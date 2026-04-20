---
tags: [module, rule-engine]
related:
  - "[Rule Engine](../../app/modules/engine/rule_engine.py)"
  - "[Webhook Dispatcher](../../app/modules/engine/webhook_dispatcher.py)"
  - "[Ядро системы](../architecture/core_engine.md)"
---

# Движок правил (Rule Engine)

> Анализирует данные из InternalQueue, проверяет условия триггеров и отправляет webhook/Firebase уведомления.

---

## Как работает

### Polling Loop

Каждые `RULE_ENGINE_POLL_INTERVAL` (5 сек) секунд:
1. Читает необработанные записи из InternalQueue
2. Для каждой записи загружает активные триггеры
3. Проверяет условие триггера
4. При срабатывании — отправляет webhook / Firebase push
5. Помечает записи как обработанные

### Условия триггеров

Поддерживаемые форматы:
- Простые: `> 30`, `< 10`, `>= 50`, `<= 100`, `== 42`, `!= 0`
- Диапазон: `10..30` (значение между 10 и 30)
- Логические: `value > 30 and value < 80`

### Cooldown

После срабатывания триггер «замораживается» на `cooldown_sec` секунд.
**Важно:** `last_triggered_at` обновляется только при **успешной** доставке webhook (исправлено в пилоте).

### Dispatch

- **Webhook:** HTTP POST на `webhook_url` с телом `{trigger_name, device_id, metric, value, timestamp}`
- **Firebase:** Push-уведомление с `title` и `body` из `firebase_notification`
- **Retry:** 3 попытки с экспоненциальной задержкой (2, 4, 8 сек)
- **Timeout:** 10 сек на запрос

## Ограничения

<!-- @TODO: Нет оконной агрегации (условие "более N секунд") -->
<!-- @TODO: Нет машины состояний событий (pending → active → ack → resolved) -->
<!-- @TODO: Нет DLQ для неудачных событий -->
<!-- @TODO: Нет приоритизации (критические vs информационные) -->

---
**См. также:** [Storage](storage.md) | [API](api_module.md) | [Ядро](../architecture/core_engine.md) | [← Навигация](../index.md)
