#!/usr/bin/env python3
"""
Arduino Button+BPM280 Bridge Script

Читает данные из Serial порта Arduino и пересылает их в GatewayDemo API.
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

DEFAULT_API_URL = "http://localhost:8000/api/v1/ingest/http"
DEFAULT_API_KEY = "your-secret-api-key-change-this"
DEFAULT_BAUD_RATE = 115200
RECONNECT_DELAY = 5

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


ACTIVE_BRIDGE = None


class ArduinoButtonBPM280Bridge:
    """Мост между Arduino Button+BPM280 и API."""

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
        self.api_url = api_url
        self.api_key = api_key
        self.baud_rate = baud_rate
        self.serial_connection: Optional[serial.Serial] = None
        self.running = False

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
        if not self.port:
            self.port = self.discover_arduino()
            if not self.port:
                logger.warning("No Arduino found")
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
            return False

    def disconnect(self):
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
        self.serial_connection = None

    def send_to_api(self, data: dict) -> bool:
        data["device_id"] = self.device_id
        try:
            response = requests.post(
                self.api_url,
                json=data,
                headers={"X-API-Key": self.api_key},
                timeout=5.0,
            )
            if response.status_code == 200:
                logger.info(
                    "Sent data: button=%s temp=%s hum=%s",
                    data.get("button"),
                    data.get("temperature"),
                    data.get("humidity"),
                )
                return True

            logger.error("API error %s: %s", response.status_code, response.text)
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

        if data.get("type") == "data" and data.get("sensor") == "BUTTON_BPM280":
            self.send_to_api(data)

    def run(self):
        self.running = True
        logger.info("Starting Button+BPM280 bridge for device %s", self.device_id)

        while self.running:
            if not self.serial_connection or not self.serial_connection.is_open:
                if not self.connect():
                    time.sleep(RECONNECT_DELAY)
                    continue

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

    def stop(self):
        self.running = False


def signal_handler(signum, frame):
    if ACTIVE_BRIDGE is not None:
        ACTIVE_BRIDGE.stop()


def main():
    global ACTIVE_BRIDGE

    parser = argparse.ArgumentParser(description="Arduino Button+BPM280 to GatewayDemo bridge")
    parser.add_argument("--device-id", required=True, help="Device UUID from GatewayDemo")
    parser.add_argument("--port", help="Serial port (auto-discover if not specified)")
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help=f"API URL (default: {DEFAULT_API_URL})")
    parser.add_argument("--api-key", default=DEFAULT_API_KEY, help="API key")
    parser.add_argument("--baud-rate", type=int, default=DEFAULT_BAUD_RATE, help="Serial baud rate")
    args = parser.parse_args()

    bridge = ArduinoButtonBPM280Bridge(
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
