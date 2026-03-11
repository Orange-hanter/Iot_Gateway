"""
Arduino Button + DHT11 Driver

Драйвер для Arduino-устройства с кнопкой и датчиком DHT11
(температура и влажность).
"""
import json
import logging
import time
from typing import Dict, List, Any, Optional

from app.drivers.base import BaseDriver

try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    serial = None
    SERIAL_AVAILABLE = False

logger = logging.getLogger(__name__)


class TemperatureSensorAdapter:
    """
    Обертка для температурного сенсора.

    Сейчас адаптер предоставляет единый интерфейс извлечения температуры
    из payload независимо от конкретной реализации сенсора.
    Позже сюда можно добавить специализированные реализации
    (например, DS18B20, DHT22, BMP/BME280 и т.д.).
    """

    def __init__(self, sensor_class: str = "generic"):
        self.sensor_class = (sensor_class or "generic").lower()

    def extract_celsius(self, payload: Dict[str, Any]) -> Optional[float]:
        """Пытается извлечь температуру в градусах Цельсия из разных полей."""
        if not isinstance(payload, dict):
            return None

        candidate_fields = [
            "ds18b20_temperature",
            "temperature",
            "temperature_c",
            "temp",
            "temp_c",
            "dht11_temperature",
            "dht11_temp",
        ]

        for field in candidate_fields:
            if field in payload:
                try:
                    return float(payload[field])
                except (TypeError, ValueError):
                    logger.warning("Invalid temperature value in field '%s'", field)
                    return None

        return None


class ArduinoButtonDHT11Driver(BaseDriver):
    """Драйвер Arduino: кнопка + температура + влажность (DHT11)."""

    driver_name = "arduino_button_dht11"
    description = "Arduino with button + DHT11 humidity and temperature"

    BAUD_RATE = 115200
    TIMEOUT = 2.0
    DEVICE_IDENTIFIER = "ARDUINO_BUTTON_DHT11"

    def __init__(self):
        super().__init__()
        self._serial_connection = None

    def _get_raw(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Извлекает сырой Arduino-payload.

        API передаёт данные в формате {"device_id": ..., "metrics": {<arduino_json>}}.
        При прямом вызове (тесты, MQTT) данные могут прийти без обёртки.
        """
        if "metrics" in payload and isinstance(payload["metrics"], dict):
            return payload["metrics"]
        return payload

    def validate(self, payload: Dict[str, Any]) -> bool:
        """
        Валидация payload от Arduino.

        Пример формата (через API):
        {
            "device_id": "...",
            "metrics": {
                "type": "data",
                "sensor": "BUTTON_DHT11",
                "button": 1,
                "humidity": 45.2,
                "timestamp": 123456
            }
        }
        """
        if not isinstance(payload, dict):
            return False

        raw = self._get_raw(payload)

        if raw.get("type") != "data":
            logger.warning("Invalid type for arduino_button_dht11: %s", raw.get("type"))
            return False

        sensor_type = raw.get("sensor")
        if sensor_type and sensor_type != "BUTTON_DHT11":
            logger.warning("Invalid sensor for arduino_button_dht11: %s", sensor_type)
            return False

        # Событийный пакет кнопки: отдельное сообщение на каждое нажатие.
        if "button_event" in raw:
            return True

        if "button" not in raw:
            logger.warning("Missing required field: button")
            return False

        if "humidity" not in raw and "dht11_humidity" not in raw:
            logger.warning("Missing required humidity field")
            return False

        return True

    def parse(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Парсинг payload в нормализованные метрики."""
        result: List[Dict[str, Any]] = []
        raw = self._get_raw(payload)

        if "button" in raw:
            button_state = self._to_bool(raw.get("button"))
            result.append({
                "name": "button_state",
                "value": 1.0 if button_state else 0.0,
                "unit": None,
            })

        if "button_event" in raw:
            event_value = self._to_bool(raw.get("button_event"))
            result.append({
                "name": "button_event",
                "value": 1.0 if event_value else 0.0,
                "unit": None,
            })

        humidity_raw = raw.get("humidity")
        if humidity_raw is None:
            humidity_raw = raw.get("dht11_humidity")
        if humidity_raw is not None:
            try:
                humidity_value = float(humidity_raw)
                result.append({
                    "name": "humidity",
                    "value": humidity_value,
                    "unit": "%",
                })
            except (TypeError, ValueError):
                logger.warning("Invalid humidity value: %s", humidity_raw)

        sensor_class = "generic"
        if isinstance(payload.get("config"), dict):
            sensor_class = payload["config"].get("temperature_sensor_class", "generic")

        temp_adapter = TemperatureSensorAdapter(sensor_class=sensor_class)
        temperature_value = temp_adapter.extract_celsius(raw)
        if temperature_value is not None:
            result.append({
                "name": "temperature",
                "value": temperature_value,
                "unit": "C",
            })

        if "button_changed" in raw:
            changed = self._to_bool(raw.get("button_changed"))
            result.append({
                "name": "button_changed",
                "value": 1.0 if changed else 0.0,
                "unit": None,
            })

        if "button_presses" in raw:
            try:
                result.append({
                    "name": "button_presses",
                    "value": float(raw.get("button_presses", 0)),
                    "unit": None,
                })
            except (TypeError, ValueError):
                logger.warning("Invalid button_presses value: %s", raw.get("button_presses"))

        return result

    def get_config_schema(self) -> Dict[str, Any]:
        """JSON Schema конфигурации устройства."""
        return {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "title": "Location",
                    "description": "Physical location of the device",
                },
                "serial_port": {
                    "type": "string",
                    "title": "Serial Port",
                    "description": "Serial port (leave empty for auto-discovery)",
                    "default": "",
                },
                "auto_connect": {
                    "type": "boolean",
                    "title": "Auto Connect",
                    "description": "Automatically connect to Arduino on startup",
                    "default": False,
                },
                "polling_interval": {
                    "type": "number",
                    "title": "Polling Interval (seconds)",
                    "description": "How often to request data from Arduino",
                    "default": 2.0,
                    "minimum": 0.5,
                },
                "temperature_sensor_class": {
                    "type": "string",
                    "title": "Temperature Sensor Class",
                    "description": "Wrapper class name for temperature sensor implementation",
                    "default": "generic",
                },
                "humidity_sensor_type": {
                    "type": "string",
                    "title": "Humidity Sensor Type",
                    "description": "Humidity sensor family",
                    "default": "dht11",
                    "enum": ["dht11"],
                },
            },
            "required": ["location"],
        }

    def get_metric_hints(self) -> List[str]:
        return [
            "button_state",
            "button_changed",
            "button_presses",
            "button_event",
            "temperature",
            "humidity",
        ]

    @staticmethod
    def discover_arduino_ports() -> List[Dict[str, Optional[str]]]:
        """Автоматическое обнаружение Arduino в системе."""
        if not SERIAL_AVAILABLE:
            logger.error("pyserial is not installed. Run: pip install pyserial")
            return []

        arduino_ports: List[Dict[str, Optional[str]]] = []
        ports = serial.tools.list_ports.comports()

        for port in ports:
            is_arduino = False

            if port.vid in [0x2341, 0x2A03]:
                is_arduino = True

            if port.description and any(
                keyword in port.description.lower() for keyword in ["arduino", "mega", "ch340", "ch341"]
            ):
                is_arduino = True

            if is_arduino:
                arduino_ports.append({
                    "port": port.device,
                    "description": port.description or "Unknown",
                    "vid": hex(port.vid) if port.vid else None,
                    "pid": hex(port.pid) if port.pid else None,
                })

        return arduino_ports

    def connect_to_arduino(self, port: Optional[str] = None) -> bool:
        """Подключение к Arduino через serial."""
        if not SERIAL_AVAILABLE:
            logger.error("pyserial is not installed. Cannot connect to Arduino.")
            return False

        self.disconnect_from_arduino()

        if not port:
            arduino_ports = self.discover_arduino_ports()
            if not arduino_ports:
                logger.error("No Arduino found. Please connect the device.")
                return False
            port = arduino_ports[0]["port"]

        try:
            self._serial_connection = serial.Serial(
                port=port,
                baudrate=self.BAUD_RATE,
                timeout=self.TIMEOUT,
            )
            time.sleep(2.0)
            self._serial_connection.reset_input_buffer()

            self._serial_connection.write(b"PING\n")
            time.sleep(0.3)

            if self._serial_connection.in_waiting:
                response = self._serial_connection.readline().decode().strip()
                logger.info("Arduino response: %s", response)

            logger.info("Successfully connected to Arduino on %s", port)
            return True

        except Exception as e:
            logger.error("Failed to connect to Arduino: %s", e)
            self._serial_connection = None
            return False

    def disconnect_from_arduino(self):
        """Отключение от Arduino."""
        if self._serial_connection and self._serial_connection.is_open:
            self._serial_connection.close()
        self._serial_connection = None

    def read_from_arduino(self, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
        """Чтение одной data-записи от Arduino."""
        if not self._serial_connection or not self._serial_connection.is_open:
            logger.error("Not connected to Arduino")
            return None

        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                if self._serial_connection.in_waiting:
                    line = self._serial_connection.readline().decode().strip()
                    if not line:
                        continue

                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        logger.warning("Invalid JSON from Arduino: %s", line)
                        continue

                    if data.get("type") == "data":
                        return data

                time.sleep(0.1)

            except Exception as e:
                logger.error("Error reading from Arduino: %s", e)
                return None

        logger.warning("Timeout waiting for Arduino data")
        return None

    def __del__(self):
        self.disconnect_from_arduino()

    @staticmethod
    def _to_bool(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "on", "pressed", "yes"}
        return False
