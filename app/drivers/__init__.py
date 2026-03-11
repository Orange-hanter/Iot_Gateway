"""
Реестр драйверов устройств
"""
from typing import Dict, Type, Optional
from app.drivers.base import BaseDriver
from app.drivers.generic_json import GenericJsonDriver
from app.drivers.arduino_mq2 import ArduinoMQ2Driver
from app.drivers.arduino_button_dht11 import ArduinoButtonDHT11Driver


class DriverRegistry:
    """Реестр драйверов устройств"""
    
    def __init__(self):
        self._drivers: Dict[str, Type[BaseDriver]] = {}
        self._register_builtin_drivers()
    
    def _register_builtin_drivers(self):
        """Регистрация встроенных драйверов"""
        self.register(GenericJsonDriver)
        self.register(ArduinoMQ2Driver)
        self.register(ArduinoButtonDHT11Driver)
    
    def register(self, driver_class: Type[BaseDriver]):
        """
        Регистрация драйвера.
        
        Args:
            driver_class: Класс драйвера (должен наследоваться от BaseDriver)
        """
        if not issubclass(driver_class, BaseDriver):
            raise TypeError(f"{driver_class} must inherit from BaseDriver")
        
        driver_instance = driver_class()
        driver_name = driver_instance.driver_name
        
        if driver_name in self._drivers:
            raise ValueError(f"Driver {driver_name} already registered")
        
        self._drivers[driver_name] = driver_class
    
    def get_driver(self, driver_name: str) -> Optional[BaseDriver]:
        """
        Получить экземпляр драйвера по имени.
        
        Args:
            driver_name: Имя драйвера
            
        Returns:
            Экземпляр драйвера или None
        """
        driver_class = self._drivers.get(driver_name)
        if driver_class:
            return driver_class()
        return None
    
    def list_drivers(self) -> Dict[str, Dict[str, str]]:
        """
        Получить список всех зарегистрированных драйверов.
        
        Returns:
            Словарь с информацией о драйверах
        """
        result = {}
        for driver_name, driver_class in self._drivers.items():
            driver_instance = driver_class()
            result[driver_name] = driver_instance.get_driver_info()
        return result


# Глобальный реестр драйверов
driver_registry = DriverRegistry()


def get_driver(driver_name: str) -> Optional[BaseDriver]:
    """Получить драйвер по имени"""
    return driver_registry.get_driver(driver_name)


def list_available_drivers() -> Dict[str, Dict[str, str]]:
    """Список доступных драйверов"""
    return driver_registry.list_drivers()
