"""
Generic JSON Driver - драйвер по умолчанию
"""
from typing import Dict, List, Any
from app.drivers.base import BaseDriver


class GenericJsonDriver(BaseDriver):
    """
    Универсальный драйвер для JSON-устройств.
    
    Ожидает формат:
    {
        "metrics": {
            "temperature": 25.5,
            "humidity": 60.0
        }
    }
    
    Или с единицами измерения:
    {
        "metrics": {
            "temperature": {"value": 25.5, "unit": "C"},
            "humidity": {"value": 60.0, "unit": "%"}
        }
    }
    """
    
    driver_name = "generic_json"
    description = "Universal JSON driver for simple key-value metrics"
    
    def validate(self, payload: Dict[str, Any]) -> bool:
        """Валидация JSON payload"""
        if not isinstance(payload, dict):
            return False
        
        # Проверяем наличие поля metrics
        if "metrics" not in payload:
            return False
        
        metrics = payload["metrics"]
        if not isinstance(metrics, dict):
            return False
        
        # Проверяем что metrics не пустой
        if not metrics:
            return False
        
        return True
    
    def parse(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Парсинг метрик в нормализованный формат"""
        metrics_data = payload["metrics"]
        result = []
        
        for metric_name, metric_value in metrics_data.items():
            # Если значение - словарь с value и unit
            if isinstance(metric_value, dict):
                value = metric_value.get("value")
                unit = metric_value.get("unit")
            else:
                # Если значение - простое число
                value = metric_value
                unit = None
            
            # Преобразуем в float
            try:
                value = float(value)
            except (TypeError, ValueError):
                continue  # Пропускаем невалидные значения
            
            result.append({
                "name": metric_name,
                "value": value,
                "unit": unit
            })
        
        return result
    
    def get_config_schema(self) -> Dict[str, Any]:
        """JSON Schema для конфигурации устройства"""
        return {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "title": "Description",
                    "description": "Optional device description"
                }
            },
            "required": []
        }
