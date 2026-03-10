"""
Arduino MQ2 Gas Sensor Driver

Драйвер для датчика газа MQ2 на базе Arduino Mega.
Поддерживает автоматическое обнаружение устройства и коммуникацию через Serial порт.
"""
import json
import logging
import threading
import time
from typing import Dict, List, Any, Optional
from app.drivers.base import BaseDriver

# Опциональная поддержка Serial порта
try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False

logger = logging.getLogger(__name__)


class ArduinoMQ2Driver(BaseDriver):
    """
    Драйвер для Arduino с датчиком MQ2.
    
    Поддерживает два режима работы:
    1. Прямой режим (direct): Данные передаются в том же формате, что Arduino отправляет
    2. Serial режим (serial): Автоматическое подключение и чтение данных с устройства
    """
    
    driver_name = "arduino_mq2"
    description = "Arduino Mega with MQ2 Gas Sensor (auto-discovery via Serial)"
    
    # Конфигурация Serial порта
    BAUD_RATE = 115200
    TIMEOUT = 2.0
    DEVICE_IDENTIFIER = "ARDUINO_MQ2"
    
    def __init__(self):
        super().__init__()
        self._serial_connection = None
        self._reading_thread = None
        self._stop_reading = False
        self._last_data = None
        self._data_lock = threading.Lock()
    
    def validate(self, payload: Dict[str, Any]) -> bool:
        """
        Валидация данных от Arduino MQ2.
        
        Ожидаемый формат:
        {
            "type": "data",
            "sensor": "MQ2",
            "analog": 512,
            "digital": 0,
            "voltage": 2.5,
            "resistance": 10.5,
            "ratio": 1.06,
            "ppm": 100.5,
            "alert": false,
            "timestamp": 123456
        }
        """
        if not isinstance(payload, dict):
            return False
        
        # Проверяем обязательные поля
        required_fields = ["type", "sensor", "analog", "ppm"]
        for field in required_fields:
            if field not in payload:
                logger.warning(f"Missing required field: {field}")
                return False
        
        # Проверяем тип данных
        if payload["type"] != "data":
            logger.warning(f"Invalid type: {payload['type']}")
            return False
        
        # Проверяем датчик
        if payload["sensor"] != "MQ2":
            logger.warning(f"Invalid sensor: {payload['sensor']}")
            return False
        
        return True
    
    def parse(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Парсинг данных MQ2 в нормализованный формат метрик.
        
        Извлекаем:
        - gas_ppm: концентрация газа в PPM
        - gas_analog: сырое аналоговое значение (0-1023)
        - gas_voltage: напряжение на датчике (V)
        - gas_resistance: сопротивление датчика (kOhm)
        - gas_ratio: отношение Rs/R0
        - gas_alert: цифровой сигнал тревоги (0/1)
        """
        result = []
        
        # Концентрация газа (основная метрика)
        result.append({
            "name": "gas_ppm",
            "value": float(payload["ppm"]),
            "unit": "ppm"
        })
        
        # Сырое значение АЦП
        if "analog" in payload:
            result.append({
                "name": "gas_analog",
                "value": float(payload["analog"]),
                "unit": None
            })
        
        # Напряжение
        if "voltage" in payload:
            result.append({
                "name": "gas_voltage",
                "value": float(payload["voltage"]),
                "unit": "V"
            })
        
        # Сопротивление датчика
        if "resistance" in payload:
            result.append({
                "name": "gas_resistance",
                "value": float(payload["resistance"]),
                "unit": "kOhm"
            })
        
        # Отношение Rs/R0
        if "ratio" in payload:
            result.append({
                "name": "gas_ratio",
                "value": float(payload["ratio"]),
                "unit": None
            })
        
        # Цифровой сигнал тревоги
        if "alert" in payload:
            alert_value = 1.0 if payload["alert"] is True else 0.0
            result.append({
                "name": "gas_alert",
                "value": alert_value,
                "unit": None
            })
        
        return result
    
    def get_config_schema(self) -> Dict[str, Any]:
        """
        JSON Schema для конфигурации устройства.
        """
        return {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "title": "Location",
                    "description": "Physical location of the sensor"
                },
                "serial_port": {
                    "type": "string",
                    "title": "Serial Port",
                    "description": "Serial port (e.g., /dev/ttyUSB0 or COM3). Leave empty for auto-discovery",
                    "default": ""
                },
                "auto_connect": {
                    "type": "boolean",
                    "title": "Auto Connect",
                    "description": "Automatically connect to Arduino on startup",
                    "default": False
                },
                "polling_interval": {
                    "type": "number",
                    "title": "Polling Interval (seconds)",
                    "description": "How often to request data from Arduino",
                    "default": 2.0,
                    "minimum": 0.5
                },
                "gas_threshold_ppm": {
                    "type": "number",
                    "title": "Gas Threshold (PPM)",
                    "description": "Alert threshold for gas concentration",
                    "default": 300.0
                }
            },
            "required": ["location"]
        }

    def get_metric_hints(self) -> List[str]:
        """Рекомендуемые имена метрик для триггеров этого драйвера."""
        return [
            "gas_ppm",
            "gas_analog",
            "gas_voltage",
            "gas_resistance",
            "gas_ratio",
            "gas_alert",
        ]
    
    # === Serial Communication Methods ===
    
    @staticmethod
    def discover_arduino_ports() -> List[Dict[str, str]]:
        """
        Автоматическое обнаружение Arduino в системе.
        
        Returns:
            Список найденных портов с информацией
        """
        if not SERIAL_AVAILABLE:
            logger.error("pyserial is not installed. Run: pip install pyserial")
            return []
        
        arduino_ports = []
        ports = serial.tools.list_ports.comports()
        
        for port in ports:
            # Поиск Arduino по VID/PID или описанию
            is_arduino = False
            
            # Arduino Mega обычно имеет VID 0x2341 (Arduino) или 0x2A03
            if port.vid in [0x2341, 0x2A03]:
                is_arduino = True
            
            # Проверка по описанию
            if port.description and any(keyword in port.description.lower() 
                                       for keyword in ['arduino', 'mega', 'ch340', 'ch341']):
                is_arduino = True
            
            if is_arduino:
                arduino_ports.append({
                    "port": port.device,
                    "description": port.description or "Unknown",
                    "vid": hex(port.vid) if port.vid else None,
                    "pid": hex(port.pid) if port.pid else None,
                })
                logger.info(f"Found Arduino: {port.device} - {port.description}")
        
        return arduino_ports
    
    def connect_to_arduino(self, port: Optional[str] = None) -> bool:
        """
        Подключение к Arduino.
        
        Args:
            port: Путь к Serial порту. Если None, будет использовано автоопределение.
            
        Returns:
            True если подключение успешно
        """
        if not SERIAL_AVAILABLE:
            logger.error("pyserial is not installed. Cannot connect to Arduino.")
            return False
        
        # Закрываем предыдущее соединение
        self.disconnect_from_arduino()
        
        # Автоопределение порта
        if not port:
            logger.info("Auto-discovering Arduino...")
            arduino_ports = self.discover_arduino_ports()
            if not arduino_ports:
                logger.error("No Arduino found. Please connect the device.")
                return False
            port = arduino_ports[0]["port"]
            logger.info(f"Using port: {port}")
        
        try:
            # Открываем Serial порт
            self._serial_connection = serial.Serial(
                port=port,
                baudrate=self.BAUD_RATE,
                timeout=self.TIMEOUT
            )
            
            # Ждем инициализации Arduino
            time.sleep(2.0)
            
            # Очищаем буфер
            self._serial_connection.reset_input_buffer()
            
            # Проверяем связь
            self._serial_connection.write(b"PING\n")
            time.sleep(0.5)
            
            if self._serial_connection.in_waiting:
                response = self._serial_connection.readline().decode().strip()
                logger.info(f"Arduino response: {response}")
            
            logger.info(f"Successfully connected to Arduino on {port}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Arduino: {e}")
            self._serial_connection = None
            return False
    
    def disconnect_from_arduino(self):
        """Отключение от Arduino."""
        if self._serial_connection and self._serial_connection.is_open:
            self._serial_connection.close()
            logger.info("Disconnected from Arduino")
        self._serial_connection = None
    
    def read_from_arduino(self, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
        """
        Чтение данных от Arduino.
        
        Args:
            timeout: Таймаут ожидания данных
            
        Returns:
            Распарсенные данные или None
        """
        if not self._serial_connection or not self._serial_connection.is_open:
            logger.error("Not connected to Arduino")
            return None
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                if self._serial_connection.in_waiting:
                    line = self._serial_connection.readline().decode().strip()
                    
                    if line:
                        logger.debug(f"Received: {line}")
                        
                        try:
                            data = json.loads(line)
                            
                            # Фильтруем только данные (не handshake, не статус)
                            if data.get("type") == "data":
                                return data
                                
                        except json.JSONDecodeError:
                            logger.warning(f"Invalid JSON: {line}")
                
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error reading from Arduino: {e}")
                return None
        
        logger.warning("Timeout waiting for Arduino data")
        return None
    
    def __del__(self):
        """Cleanup при удалении объекта."""
        self.disconnect_from_arduino()
