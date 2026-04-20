---
tags: [module, drivers]
related:
  - "[Base Driver](../../app/drivers/base.py)"
  - "[Интеграционный слой](../architecture/integration_layer.md)"
---

# Система драйверов

> Драйверы отвечают за парсинг данных от конкретных типов устройств в единый формат.

---

## Архитектура

Все драйверы наследуются от базового класса `BaseDriver` и реализуют метод `parse(payload)`.

**Путь:** `app/drivers/`

## Доступные драйверы

### generic_json

**Путь:** `app/drivers/generic_json.py`  
Универсальный драйвер для устройств, отправляющих JSON.

Принимает:
```json
{
  "metrics": {
    "temperature": 25.5,
    "humidity": 60
  }
}
```

### arduino_button_dht11

**Путь:** `app/drivers/arduino_button_dht11.py`  
Драйвер для Arduino с кнопкой и датчиком DHT11.  
**Руководство:** [Arduino Button+DHT11](../guides/arduino_button_dht11.md)

### arduino_mq2

**Путь:** `app/drivers/arduino_mq2.py`  
Драйвер для Arduino с газовым датчиком MQ2.  
**Руководство:** [Arduino MQ2](../guides/arduino_mq2.md)

## Создание нового драйвера

1. Создать файл в `app/drivers/`
2. Наследоваться от `BaseDriver`
3. Реализовать `parse(payload) → list[dict]`
4. Зарегистрировать в `app/drivers/__init__.py`

<!-- @TODO: Формализовать контракт драйвера (DeviceAdapter interface из архитектуры) -->
<!-- @TODO: Добавить Modbus TCP адаптер -->
<!-- @TODO: Добавить OPC UA адаптер -->
<!-- @TODO: Динамическая загрузка из plugins/ -->

---
**См. также:** [Ingestion](ingestion.md) | [Интеграционный слой](../architecture/integration_layer.md) | [← Навигация](../index.md)
