#!/usr/bin/env python3
"""
Тестовый скрипт для проверки драйвера Arduino MQ2

Использование:
    python test_driver.py
    python test_driver.py --port /dev/ttyUSB0
"""

import argparse
import json
import sys
import time

# Добавляем путь к приложению
sys.path.insert(0, '/Users/dakh/Git/GatewayDemo')

from app.drivers.arduino_mq2 import ArduinoMQ2Driver


def test_discovery():
    """Тест автоматического обнаружения Arduino"""
    print("\n=== Test 1: Auto-discovery ===")
    
    driver = ArduinoMQ2Driver()
    ports = driver.discover_arduino_ports()
    
    if ports:
        print(f"✓ Found {len(ports)} Arduino port(s):")
        for port_info in ports:
            print(f"  - {port_info['port']}: {port_info['description']}")
        return ports[0]['port']
    else:
        print("✗ No Arduino found")
        return None


def test_connection(port=None):
    """Тест подключения к Arduino"""
    print("\n=== Test 2: Connection ===")
    
    driver = ArduinoMQ2Driver()
    
    if driver.connect_to_arduino(port):
        print("✓ Successfully connected")
        driver.disconnect_from_arduino()
        return True
    else:
        print("✗ Connection failed")
        return False


def test_data_reading(port=None):
    """Тест чтения данных"""
    print("\n=== Test 3: Data Reading ===")
    
    driver = ArduinoMQ2Driver()
    
    if not driver.connect_to_arduino(port):
        print("✗ Cannot connect")
        return False
    
    print("Waiting for data (timeout: 10s)...")
    data = driver.read_from_arduino(timeout=10)
    
    if data:
        print("✓ Received data:")
        print(json.dumps(data, indent=2))
        driver.disconnect_from_arduino()
        return data
    else:
        print("✗ No data received")
        driver.disconnect_from_arduino()
        return None


def test_validation(data):
    """Тест валидации данных"""
    print("\n=== Test 4: Validation ===")
    
    driver = ArduinoMQ2Driver()
    
    if data and driver.validate(data):
        print("✓ Data validation passed")
        return True
    else:
        print("✗ Data validation failed")
        return False


def test_parsing(data):
    """Тест парсинга данных"""
    print("\n=== Test 5: Parsing ===")
    
    driver = ArduinoMQ2Driver()
    
    try:
        metrics = driver.parse(data)
        print(f"✓ Parsed {len(metrics)} metrics:")
        for metric in metrics:
            unit = f" {metric['unit']}" if metric['unit'] else ""
            print(f"  - {metric['name']}: {metric['value']:.2f}{unit}")
        return True
    except Exception as e:
        print(f"✗ Parsing failed: {e}")
        return False


def test_config_schema():
    """Тест получения схемы конфигурации"""
    print("\n=== Test 6: Config Schema ===")
    
    driver = ArduinoMQ2Driver()
    schema = driver.get_config_schema()
    
    print("✓ Config schema:")
    print(json.dumps(schema, indent=2))
    return True


def test_continuous_reading(port=None, duration=30):
    """Тест непрерывного чтения (30 секунд)"""
    print(f"\n=== Test 7: Continuous Reading ({duration}s) ===")
    
    driver = ArduinoMQ2Driver()
    
    if not driver.connect_to_arduino(port):
        print("✗ Cannot connect")
        return False
    
    print("Reading data...")
    start_time = time.time()
    count = 0
    
    try:
        while time.time() - start_time < duration:
            data = driver.read_from_arduino(timeout=5)
            if data:
                count += 1
                ppm = data.get('ppm', 0)
                alert = data.get('alert', False)
                alert_str = "⚠️ ALERT" if alert else "OK"
                print(f"  [{count}] PPM: {ppm:.2f} - {alert_str}")
            else:
                print("  No data")
            
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    
    finally:
        driver.disconnect_from_arduino()
    
    print(f"✓ Received {count} readings")
    return True


def main():
    parser = argparse.ArgumentParser(description='Test Arduino MQ2 driver')
    parser.add_argument(
        '--port',
        help='Serial port (auto-discover if not specified)'
    )
    parser.add_argument(
        '--continuous',
        action='store_true',
        help='Run continuous reading test'
    )
    parser.add_argument(
        '--duration',
        type=int,
        default=30,
        help='Duration for continuous test (seconds)'
    )
    
    args = parser.parse_args()
    
    print("=" * 50)
    print("Arduino MQ2 Driver Test Suite")
    print("=" * 50)
    
    # Test 1: Discovery
    discovered_port = test_discovery()
    port = args.port or discovered_port
    
    if not port:
        print("\n❌ No Arduino found. Please connect the device and try again.")
        return 1
    
    # Test 2: Connection
    if not test_connection(port):
        print("\n❌ Cannot establish connection. Check the port and try again.")
        return 1
    
    # Test 3: Data reading
    data = test_data_reading(port)
    if not data:
        print("\n⚠️  Data reading test failed. Arduino may still be warming up.")
        print("    Wait 30 seconds and try again.")
        return 1
    
    # Test 4: Validation
    test_validation(data)
    
    # Test 5: Parsing
    test_parsing(data)
    
    # Test 6: Config schema
    test_config_schema()
    
    # Test 7: Continuous (optional)
    if args.continuous:
        test_continuous_reading(port, args.duration)
    
    print("\n" + "=" * 50)
    print("✅ All tests completed!")
    print("=" * 50)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
