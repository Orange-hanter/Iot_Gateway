"""
Базовый интерфейс драйвера устройства
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional


class BaseDriver(ABC):
    """
    Базовый класс для драйверов устройств.
    Каждый драйвер должен реализовывать методы валидации, парсинга и схемы конфигурации.
    """
    
    # Имя драйвера (переопределяется в наследниках)
    driver_name: str = "base"
    
    # Описание драйвера
    description: str = "Base driver interface"
    
    @abstractmethod
    def validate(self, payload: Dict[str, Any]) -> bool:
        """
        Валидация входящих данных.
        
        Args:
            payload: Сырые данные от устройства
            
        Returns:
            True если данные корректны, False иначе
        """
        pass
    
    @abstractmethod
    def parse(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Парсинг данных в нормализованный формат.
        
        Args:
            payload: Сырые данные от устройства
            
        Returns:
            Список метрик в формате:
            [
                {"name": "temperature", "value": 25.5, "unit": "C"},
                {"name": "humidity", "value": 60.0, "unit": "%"}
            ]
        """
        pass
    
    @abstractmethod
    def get_config_schema(self) -> Dict[str, Any]:
        """
        Возвращает JSON-схему конфигурации для этого типа устройства.
        Используется в Admin UI для отображения формы настроек.
        
        Returns:
            JSON Schema объект
        """
        pass
    
    def get_driver_info(self) -> Dict[str, str]:
        """Информация о драйвере"""
        return {
            "name": self.driver_name,
            "description": self.description
        }
