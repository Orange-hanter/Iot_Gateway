#!/usr/bin/env python3
"""
serial_tcp_bridge.py — Пробрасывает Serial порт Arduino как TCP сервер.
Используется на хосте (macOS) для Docker-контейнеров, которые не имеют
прямого доступа к USB Serial.

Запуск:
    python3 serial_tcp_bridge.py --port /dev/cu.usbserial-1240 --tcp-port 8888
"""
import argparse
import logging
import socket
import threading
import sys

try:
    import serial
except ImportError:
    print("Установите pyserial: pip install pyserial")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("serial_tcp_bridge")


def handle_client(client_sock: socket.socket, serial_port: str, baud_rate: int):
    client_addr = client_sock.getpeername()
    log.info("Новое подключение от %s", client_addr)
    try:
        ser = serial.Serial(serial_port, baudrate=baud_rate, timeout=0.1)
        log.info("Открыт serial порт %s @ %d baud", serial_port, baud_rate)
    except serial.SerialException as e:
        log.error("Не удалось открыть serial: %s", e)
        client_sock.close()
        return

    stop_event = threading.Event()

    def serial_to_tcp():
        while not stop_event.is_set():
            try:
                data = ser.read(256)
                if data:
                    client_sock.sendall(data)
            except Exception as e:
                log.debug("serial→tcp ошибка: %s", e)
                break
        stop_event.set()

    def tcp_to_serial():
        while not stop_event.is_set():
            try:
                data = client_sock.recv(256)
                if not data:
                    break
                ser.write(data)
            except Exception as e:
                log.debug("tcp→serial ошибка: %s", e)
                break
        stop_event.set()

    t1 = threading.Thread(target=serial_to_tcp, daemon=True)
    t2 = threading.Thread(target=tcp_to_serial, daemon=True)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    ser.close()
    client_sock.close()
    log.info("Соединение с %s закрыто", client_addr)


def main():
    parser = argparse.ArgumentParser(description="Serial → TCP bridge для Docker")
    parser.add_argument("--port", default="/dev/cu.usbserial-1240", help="Serial порт")
    parser.add_argument("--baud-rate", type=int, default=115200, help="Baud rate")
    parser.add_argument("--tcp-port", type=int, default=8888, help="TCP порт для прослушивания")
    args = parser.parse_args()

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("0.0.0.0", args.tcp_port))
    server.listen(1)
    log.info("Слушаем TCP :%d, Serial=%s @ %d", args.tcp_port, args.port, args.baud_rate)

    try:
        while True:
            client_sock, _ = server.accept()
            t = threading.Thread(
                target=handle_client,
                args=(client_sock, args.port, args.baud_rate),
                daemon=True,
            )
            t.start()
    except KeyboardInterrupt:
        log.info("Останавливаемся")
    finally:
        server.close()


if __name__ == "__main__":
    main()
