#!/bin/sh
# docker-entrypoint.sh
# На macOS Docker Desktop не имеет прямого доступа к USB Serial.
# Вместо этого хост пробрасывает Serial-порт через socat как TCP (порт 8888),
# а этот скрипт создаёт внутри контейнера виртуальный PTY и подключается к нему.

set -e

SERIAL_HOST="${SERIAL_HOST:-host.docker.internal}"
SERIAL_PORT="${SERIAL_TCP_PORT:-8888}"
VIRTUAL_PORT="/tmp/arduino_serial"

if [ "$USE_SOCAT" = "1" ]; then
    echo "[entrypoint] Ждём TCP serial-туннеля на ${SERIAL_HOST}:${SERIAL_PORT}..."
    # Ждём до 30 секунд пока хост поднимет socat (используем Python, т.к. nc может отсутствовать)
    for i in $(seq 1 30); do
        if python3 -c "import socket; s=socket.create_connection(('$SERIAL_HOST', $SERIAL_PORT), 1); s.close()" 2>/dev/null; then
            echo "[entrypoint] Туннель доступен. Создаём виртуальный PTY..."
            break
        fi
        sleep 1
    done

    # Запускаем socat в фоне: создаёт PTY /tmp/arduino_serial → TCP на хосте
    socat pty,raw,echo=0,link=${VIRTUAL_PORT} \
        TCP:${SERIAL_HOST}:${SERIAL_PORT} &
    SOCAT_PID=$!
    echo "[entrypoint] socat PID=$SOCAT_PID"

    # Ждём пока symlink появится
    for i in $(seq 1 10); do
        if [ -e "$VIRTUAL_PORT" ]; then
            echo "[entrypoint] Виртуальный порт готов: $VIRTUAL_PORT"
            break
        fi
        sleep 0.5
    done

    # Запускаем bridge с виртуальным портом
    exec python /app/bridge_button_dht11.py --port="$VIRTUAL_PORT" "$@"
else
    # Прямой доступ к Serial (Linux с device passthrough)
    exec python /app/bridge_button_dht11.py "$@"
fi
