#!/bin/bash
# Скрипт инициализации MQTT пользователей и паролей
# Используется при первом запуске Docker компонента

PASSWD_FILE="/mosquitto/config/mosquitto_passwd"

# Создадим password файл если не существует
if [ ! -f "$PASSWD_FILE" ]; then
    echo "Creating MQTT users..."
    
    # Создаем пользователя iot-core с паролем
    # Password по умолчанию: change-this-mqtt-password
    # (должно быть выбрано в .env при развертывании)
    mosquitto_passwd -c -b "$PASSWD_FILE" iot-core "${MQTT_IOT_CORE_PASSWORD:-change-this-mqtt-password}"
    
    # Опционально: добавим Admin пользователя
    mosquitto_passwd -b "$PASSWD_FILE" mqtt-admin "${MQTT_ADMIN_PASSWORD:-change-this-admin-password}"
    
    echo "MQTT users initialized"
else
    echo "MQTT password file already exists: $PASSWD_FILE"
fi

# Убедимся что права доступа правильные
chmod 600 "$PASSWD_FILE"
chmod 600 /mosquitto/config/mosquitto.conf
