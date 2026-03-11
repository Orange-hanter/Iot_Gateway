#!/usr/bin/env python3
"""Тесты драйвера Arduino Button+DHT11."""

import argparse
import json
import sys

sys.path.insert(0, "/Users/dakh/Git/GatewayDemo")

from app.drivers.arduino_button_dht11 import ArduinoButtonDHT11Driver


def test_discovery() -> None:
    driver = ArduinoButtonDHT11Driver()
    ports = driver.discover_arduino_ports()
    print("Found ports:")
    for item in ports:
        print(f"- {item['port']}: {item['description']}")


def test_parse_sample() -> None:
    driver = ArduinoButtonDHT11Driver()
    sample = {
        "type": "data",
        "sensor": "BUTTON_DHT11",
        "button": 1,
        "button_changed": True,
        "temperature": 23.8,
        "humidity": 46.1,
    }

    print("Validation:", driver.validate(sample))
    print("Metrics:")
    print(json.dumps(driver.parse(sample), indent=2, ensure_ascii=False))

    event_sample = {
        "type": "data",
        "sensor": "BUTTON_DHT11",
        "button": 1,
        "button_event": 1,
        "button_changed": True,
        "button_presses": 1,
    }

    print("Event validation:", driver.validate(event_sample))
    print("Event metrics:")
    print(json.dumps(driver.parse(event_sample), indent=2, ensure_ascii=False))


def test_serial_read(port: str) -> None:
    driver = ArduinoButtonDHT11Driver()
    if not driver.connect_to_arduino(port):
        print("Connection failed")
        return

    data = driver.read_from_arduino(timeout=10)
    print("Data:", json.dumps(data, indent=2, ensure_ascii=False) if data else None)
    if data:
        print("Metrics:")
        print(json.dumps(driver.parse(data), indent=2, ensure_ascii=False))

    driver.disconnect_from_arduino()


def main() -> None:
    parser = argparse.ArgumentParser(description="Test Button+DHT11 driver")
    parser.add_argument("--port", help="Serial port for direct read")
    args = parser.parse_args()

    test_discovery()
    test_parse_sample()

    if args.port:
        test_serial_read(args.port)


if __name__ == "__main__":
    main()
