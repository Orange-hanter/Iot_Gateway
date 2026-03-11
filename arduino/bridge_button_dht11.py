#!/usr/bin/env python3
"""
Arduino Button+DHT11 Bridge Script

Читает данные из Serial порта Arduino и пересылает их в GatewayDemo API.
"""

import argparse
import json
import logging
import signal
import sys
import time
from typing import Optional
from pathlib import Path
from datetime import datetime
import pickle

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

DEFAULT_API_URL = "http://localhost:8000/api/v1/ingest/http"
DEFAULT_API_KEY = "your-secret-api-key-change-this"
DEFAULT_BAUD_RATE = 115200
RECONNECT_DELAY = 5
BUFFER_DIR = Path("./data/bridge_buffer")
MAX_BUFFER_FILES = 500   # Максимальное число файлов в буфере на устройство
MAX_BUFFER_AGE_HOURS = 24  # Файлы старше этого времени удаляются

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


ACTIVE_BRIDGE = None


class ArduinoButtonDHT11Bridge:
    """Мост между Arduino Button+DHT11 и API."""

    def __init__(
        self,
        device_id: str,
        port: Optional[str] = None,
        api_url: str = DEFAULT_API_URL,
        api_key: str = DEFAULT_API_KEY,
        baud_rate: int = DEFAULT_BAUD_RATE,
    ):
        self.device_id = device_id
        self.port = port
        self.manual_port = port is not None
        self.api_url = api_url
        self.api_key = api_key
        self.baud_rate = baud_rate
        self.serial_connection: Optional[serial.Serial] = None
        self.running = False
        
        # Локальный буфер для переотправки при недоступности API
        self.buffer_dir = BUFFER_DIR / device_id
        self.buffer_dir.mkdir(parents=True, exist_ok=True)
        
        # Статистика
        self.stats = {
            "sent": 0,
            "buffered": 0,
            "resent": 0,
            "errors": 0,
            "reconnects": 0
        }

    def _save_to_buffer(self, data: dict) -> bool:
        """Сохранить данные в локальный буфер"""
        try:
            # Удаляем файлы старше MAX_BUFFER_AGE_HOURS
            cutoff = datetime.now().timestamp() - MAX_BUFFER_AGE_HOURS * 3600
            for old_file in self.buffer_dir.glob("*.pkl"):
                if old_file.stat().st_mtime < cutoff:
                    old_file.unlink(missing_ok=True)

            # Если буфер заполнен — удаляем самый старый файл (FIFO)
            buffer_files = sorted(self.buffer_dir.glob("*.pkl"), key=lambda f: f.stat().st_mtime)
            while len(buffer_files) >= MAX_BUFFER_FILES:
                oldest = buffer_files.pop(0)
                oldest.unlink(missing_ok=True)
                logger.warning(f"Buffer full: dropped oldest file {oldest.name}")

            timestamp = datetime.now().isoformat()
            buffer_file = self.buffer_dir / f"{timestamp.replace(':', '-')}.pkl"

            with open(buffer_file, 'wb') as f:
                pickle.dump(data, f)

            self.stats["buffered"] += 1
            logger.warning(f"Data buffered to {buffer_file.name} (total buffered: {self.stats['buffered']})")
            return True
        except Exception as e:
            logger.error(f"Failed to buffer data: {e}")
            return False
    
    def _flush_buffer(self) -> int:
        """Переотправить буферизованные данные"""
        count = 0
        try:
            buffer_files = list(self.buffer_dir.glob("*.pkl"))
            if not buffer_files:
                return 0
            
            logger.info(f"Found {len(buffer_files)} buffered messages, attempting to send...")
            
            for buffer_file in buffer_files:
                try:
                    with open(buffer_file, 'rb') as f:
                        data = pickle.load(f)
                    
                    # Пытаемся отправить
                    if self.send_to_api(data, from_buffer=True):
                        buffer_file.unlink()  # Удаляем файл после успешной отправки
                        count += 1
                        self.stats["resent"] += 1
                except Exception as e:
                    logger.error(f"Failed to resend buffered data from {buffer_file.name}: {e}")
        
        except Exception as e:
            logger.error(f"Error flushing buffer: {e}")
        
        if count > 0:
            logger.info(f"Resent {count} buffered messages")
        
        return count

    def discover_arduino(self) -> Optional[str]:
        ports = serial.tools.list_ports.comports()
        for port in ports:
            if port.vid in [0x2341, 0x2A03] or (
                port.description and any(k in port.description.lower() for k in ["arduino", "mega", "ch340", "ch341"])
            ):
                logger.info("Found Arduino: %s - %s", port.device, port.description)
                return port.device
        return None

    def connect(self) -> bool:
        if not self.manual_port:
            self.port = self.discover_arduino()
            if not self.port:
                logger.warning("No Arduino found")
                return False
        elif not self.port:
            logger.warning("Manual serial port is empty")
            return False

        try:
            self.serial_connection = serial.Serial(
                port=self.port,
                baudrate=self.baud_rate,
                timeout=2.0,
            )
            time.sleep(2.0)
            self.serial_connection.reset_input_buffer()
            logger.info("Connected to Arduino on %s", self.port)
            return True
        except Exception as e:
            logger.error("Connection failed: %s", e)
            self.serial_connection = None
            if not self.manual_port:
                self.port = None
            return False

    def disconnect(self):
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
        self.serial_connection = None

    def _normalize_payload(self, data: dict) -> dict:
        """Приводит payload к согласованной схеме для API/драйвера."""
        normalized = dict(data)
        normalized["type"] = "data"
        normalized["sensor"] = "BUTTON_DHT11"

        # Унифицированная влажность
        if "humidity" not in normalized and "dht11_humidity" in normalized:
            normalized["humidity"] = normalized.get("dht11_humidity")

        # Унифицированные температуры
        ds_temp = normalized.get("ds18b20_temperature")
        dht_temp = normalized.get("dht11_temperature")

        if ds_temp is None and "temperature_ds18b20" in normalized:
            ds_temp = normalized.get("temperature_ds18b20")
            normalized["ds18b20_temperature"] = ds_temp

        if dht_temp is None and "temperature_dht11" in normalized:
            dht_temp = normalized.get("temperature_dht11")
            normalized["dht11_temperature"] = dht_temp

        if "temperature" not in normalized:
            if ds_temp is not None:
                normalized["temperature"] = ds_temp
            elif dht_temp is not None:
                normalized["temperature"] = dht_temp

        if "ds18b20_ok" not in normalized:
            try:
                if ds_temp is not None:
                    ds_val = float(ds_temp)
                    normalized["ds18b20_ok"] = -100.0 < ds_val < 125.0
            except (TypeError, ValueError):
                normalized["ds18b20_ok"] = False

        return normalized

    def send_to_api(self, data: dict, from_buffer: bool = False) -> bool:
        # API ожидает формат {"device_id": ..., "metrics": {<arduino_json>}}
        normalized_data = self._normalize_payload(data)
        payload = {
            "device_id": self.device_id,
            "metrics": normalized_data,
        }
        try:
            response = requests.post(
                self.api_url,
                json=payload,
                headers={"X-API-Key": self.api_key},
                timeout=5.0,
            )
            if response.status_code == 200:
                logger.info(
                    "Sent data: button=%s temp=%s hum=%s",
                    normalized_data.get("button"),
                    normalized_data.get("temperature"),
                    normalized_data.get("humidity"),
                )
                
                # Если успешно отправили, пытаемся отправить буферизованные данные
                if (not from_buffer) and any(self.buffer_dir.glob("*.pkl")):
                    self._flush_buffer()
                
                return True

            logger.error("API error %s: %s", response.status_code, response.text)
            self._save_to_buffer(data)
            return False
        except (requests.Timeout, requests.ConnectionError) as e:
            logger.warning(f"Network error: {e}")
            self._save_to_buffer(data)
            return False
        except Exception as e:
            logger.error("Failed to send data: %s", e)
            return False

    def process_line(self, line: str):
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            logger.warning("Invalid JSON: %s", line[:120])
            return

        if data.get("type") == "handshake":
            logger.info("Handshake: %s", data)
            return

        if "status" in data:
            logger.info("Arduino status: %s", data["status"])
            return

        sensor_type = data.get("sensor")
        if data.get("type") == "data" and sensor_type == "BUTTON_DHT11":
            self.send_to_api(data)

    def run(self):
        self.running = True
        logger.info("Starting Button+DHT11 bridge for device %s", self.device_id)
        logger.info(f"Local buffer directory: {self.buffer_dir}")
        
        # Попытаемся отправить буферизованные данные если есть
        self._flush_buffer()
        
        last_buffer_flush = time.time()

        while self.running:
            if not self.serial_connection or not self.serial_connection.is_open:
                if not self.connect():
                    time.sleep(RECONNECT_DELAY)
                    continue

            # Периодически пытаемся отправить буферизованные данные (каждые 30 сек)
            current_time = time.time()
            if current_time - last_buffer_flush > 30 and any(self.buffer_dir.glob("*.pkl")):
                self._flush_buffer()
                last_buffer_flush = current_time

            conn = self.serial_connection
            if conn is None:
                time.sleep(0.1)
                continue

            try:
                if conn.in_waiting:
                    line = conn.readline().decode().strip()
                    if line:
                        self.process_line(line)
                else:
                    time.sleep(0.1)
            except serial.SerialException as e:
                logger.error("Serial error: %s", e)
                self.disconnect()
                time.sleep(RECONNECT_DELAY)
            except Exception as e:
                logger.error("Unexpected error: %s", e)
                time.sleep(1.0)

        self.disconnect()
        logger.info(
            "Statistics: sent=%d, buffered=%d, resent=%d, errors=%d, reconnects=%d",
            self.stats["sent"],
            self.stats["buffered"],
            self.stats["resent"],
            self.stats["errors"],
            self.stats["reconnects"],
        )

    def stop(self):
        self.running = False


def signal_handler(signum, frame):
    if ACTIVE_BRIDGE is not None:
        ACTIVE_BRIDGE.stop()


def main():
    global ACTIVE_BRIDGE

    parser = argparse.ArgumentParser(description="Arduino Button+DHT11 to GatewayDemo bridge")
    parser.add_argument("--device-id", required=True, help="Device UUID from GatewayDemo")
    parser.add_argument("--port", help="Serial port (auto-discover if not specified)")
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help=f"API URL (default: {DEFAULT_API_URL})")
    parser.add_argument("--api-key", default=DEFAULT_API_KEY, help="API key")
    parser.add_argument("--baud-rate", type=int, default=DEFAULT_BAUD_RATE, help="Serial baud rate")
    args = parser.parse_args()

    bridge = ArduinoButtonDHT11Bridge(
        device_id=args.device_id,
        port=args.port,
        api_url=args.api_url,
        api_key=args.api_key,
        baud_rate=args.baud_rate,
    )
    ACTIVE_BRIDGE = bridge

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    bridge.run()


if __name__ == "__main__":
    main()
