#!/usr/bin/env python3
"""
Arduino MQ2 Bridge Script

Скрипт для автоматической пересылки данных от Arduino к GatewayDemo API.
Читает данные из Serial порта и отправляет через HTTP.

Использование:
    python bridge.py --device-id YOUR-DEVICE-UUID --port /dev/ttyUSB0
"""

import argparse
import json
import logging
import signal
import sys
import time
from typing import Optional

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    print("Error: pyserial not installed. Run: pip install pyserial")
    sys.exit(1)

try:
    import requests
except ImportError:
    print("Error: requests not installed. Run: pip install requests")
    sys.exit(1)

# Конфигурация
DEFAULT_API_URL = "http://localhost:8000/api/v1/ingest/http"
DEFAULT_API_KEY = "your-secret-api-key-change-this"
DEFAULT_BAUD_RATE = 115200
RECONNECT_DELAY = 5  # Секунды между попытками переподключения

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ArduinoBridge:
    """Мост между Arduino и GatewayDemo API"""
    
    def __init__(
        self, 
        device_id: str,
        port: Optional[str] = None,
        api_url: str = DEFAULT_API_URL,
        api_key: str = DEFAULT_API_KEY,
        baud_rate: int = DEFAULT_BAUD_RATE
    ):
        self.device_id = device_id
        self.port = port
        self.api_url = api_url
        self.api_key = api_key
        self.baud_rate = baud_rate
        self.serial_connection: Optional[serial.Serial] = None
        self.running = False
        
        # Статистика
        self.stats = {
            "sent": 0,
            "errors": 0,
            "reconnects": 0
        }
    
    def discover_arduino(self) -> Optional[str]:
        """Автоматическое обнаружение Arduino"""
        logger.info("Searching for Arduino...")
        
        ports = serial.tools.list_ports.comports()
        
        for port in ports:
            # Поиск по VID/PID или описанию
            if port.vid in [0x2341, 0x2A03] or \
               (port.description and any(keyword in port.description.lower() 
                                        for keyword in ['arduino', 'mega', 'ch340', 'ch341'])):
                logger.info(f"Found Arduino: {port.device} - {port.description}")
                return port.device
        
        logger.warning("No Arduino found")
        return None
    
    def connect(self) -> bool:
        """Подключение к Arduino"""
        # Автообнаружение если порт не указан
        if not self.port:
            self.port = self.discover_arduino()
            if not self.port:
                return False
        
        try:
            logger.info(f"Connecting to {self.port} at {self.baud_rate} baud...")
            
            self.serial_connection = serial.Serial(
                port=self.port,
                baudrate=self.baud_rate,
                timeout=2.0
            )
            
            # Ждем инициализации Arduino
            time.sleep(2.0)
            
            # Очищаем буфер
            self.serial_connection.reset_input_buffer()
            
            # Проверяем связь
            self.serial_connection.write(b"INFO\n")
            time.sleep(0.5)
            
            if self.serial_connection.in_waiting:
                response = self.serial_connection.readline().decode().strip()
                logger.info(f"Arduino response: {response}")
            
            logger.info(f"✓ Connected to Arduino on {self.port}")
            return True
            
        except Exception as e:
            logger.error(f"✗ Connection failed: {e}")
            self.serial_connection = None
            return False
    
    def disconnect(self):
        """Отключение от Arduino"""
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
            logger.info("Disconnected from Arduino")
        self.serial_connection = None
    
    def send_to_api(self, data: dict) -> bool:
        """Отправка данных в API"""
        try:
            # Добавляем device_id
            data["device_id"] = self.device_id
            
            response = requests.post(
                self.api_url,
                json=data,
                headers={"X-API-Key": self.api_key},
                timeout=5.0
            )
            
            if response.status_code == 200:
                self.stats["sent"] += 1
                ppm = data.get("ppm", 0)
                logger.info(f"✓ Sent data: PPM={ppm:.2f} ({self.stats['sent']} total)")
                return True
            else:
                self.stats["errors"] += 1
                logger.error(f"✗ API error {response.status_code}: {response.text}")
                return False
                
        except Exception as e:
            self.stats["errors"] += 1
            logger.error(f"✗ Failed to send data: {e}")
            return False
    
    def process_line(self, line: str):
        """Обработка строки от Arduino"""
        try:
            data = json.loads(line)
            
            # Логируем статусные сообщения
            if "status" in data:
                logger.info(f"Arduino status: {data['status']}")
                return
            
            # Логируем handshake
            if data.get("type") == "handshake":
                logger.info(f"Arduino handshake: {data}")
                return
            
            # Отправляем данные
            if data.get("type") == "data" and data.get("sensor") == "MQ2":
                self.send_to_api(data)
            
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON: {line[:100]}")
        except Exception as e:
            logger.error(f"Error processing line: {e}")
    
    def run(self):
        """Основной цикл чтения и отправки данных"""
        self.running = True
        logger.info("Starting Arduino Bridge...")
        logger.info(f"Device ID: {self.device_id}")
        logger.info(f"API URL: {self.api_url}")
        
        while self.running:
            # Подключение
            if not self.serial_connection or not self.serial_connection.is_open:
                if not self.connect():
                    logger.info(f"Retrying in {RECONNECT_DELAY} seconds...")
                    time.sleep(RECONNECT_DELAY)
                    self.stats["reconnects"] += 1
                    continue
            
            # Чтение данных
            try:
                if self.serial_connection.in_waiting:
                    line = self.serial_connection.readline().decode().strip()
                    if line:
                        logger.debug(f"Raw: {line}")
                        self.process_line(line)
                else:
                    time.sleep(0.1)
                    
            except serial.SerialException as e:
                logger.error(f"Serial error: {e}")
                self.disconnect()
                time.sleep(RECONNECT_DELAY)
                
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                time.sleep(1.0)
        
        # Завершение
        self.disconnect()
        logger.info("Bridge stopped")
        logger.info(f"Statistics: {self.stats['sent']} sent, "
                   f"{self.stats['errors']} errors, "
                   f"{self.stats['reconnects']} reconnects")
    
    def stop(self):
        """Остановка моста"""
        logger.info("Stopping bridge...")
        self.running = False


def signal_handler(signum, frame):
    """Обработчик сигнала для graceful shutdown"""
    logger.info("\nReceived interrupt signal")
    if hasattr(signal_handler, 'bridge'):
        signal_handler.bridge.stop()
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(
        description='Arduino MQ2 to GatewayDemo bridge',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Auto-discover Arduino and use default settings
  python bridge.py --device-id abc-123-def
  
  # Specify serial port
  python bridge.py --device-id abc-123-def --port /dev/ttyUSB0
  
  # Custom API endpoint
  python bridge.py --device-id abc-123-def --api-url http://192.168.1.100:8000/api/v1/ingest/http
        """
    )
    
    parser.add_argument(
        '--device-id',
        required=True,
        help='Device UUID from GatewayDemo'
    )
    
    parser.add_argument(
        '--port',
        help='Serial port (e.g., /dev/ttyUSB0 or COM3). Auto-discover if not specified'
    )
    
    parser.add_argument(
        '--api-url',
        default=DEFAULT_API_URL,
        help=f'GatewayDemo API URL (default: {DEFAULT_API_URL})'
    )
    
    parser.add_argument(
        '--api-key',
        default=DEFAULT_API_KEY,
        help='API key for authentication'
    )
    
    parser.add_argument(
        '--baud-rate',
        type=int,
        default=DEFAULT_BAUD_RATE,
        help=f'Serial baud rate (default: {DEFAULT_BAUD_RATE})'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Настройка уровня логирования
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    # Создание моста
    bridge = ArduinoBridge(
        device_id=args.device_id,
        port=args.port,
        api_url=args.api_url,
        api_key=args.api_key,
        baud_rate=args.baud_rate
    )
    
    # Регистрация обработчика сигналов
    signal_handler.bridge = bridge
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Запуск
    try:
        bridge.run()
    except KeyboardInterrupt:
        bridge.stop()


if __name__ == '__main__':
    main()
