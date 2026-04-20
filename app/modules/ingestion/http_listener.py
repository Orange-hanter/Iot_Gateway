"""
HTTP Listener для приема данных от устройств
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Header, Request
from pydantic import BaseModel, Field, validator
from app.database import db
from app.drivers import get_driver
from app.modules.storage import StorageService
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ingest", tags=["ingestion"])


class TelemetryPayload(BaseModel):
    """Модель входящих данных телеметрии"""
    device_id: str = Field(..., description="UUID устройства")
    timestamp: Optional[datetime] = Field(None, description="Timestamp события")
    metrics: Dict[str, Any] = Field(..., description="Метрики устройства")
    
    @validator('timestamp', pre=True, always=True)
    @classmethod
    def set_timestamp(cls, v):
        return v or datetime.utcnow()


class IngestResponse(BaseModel):
    """Ответ на запрос приема данных"""
    success: bool
    message: str
    metrics_count: int = 0


@router.post("/http", response_model=IngestResponse)
async def ingest_http(
    payload: TelemetryPayload,
    request: Request,
    x_api_key: Optional[str] = Header(None),  # pylint: disable=unused-argument
):
    """
    HTTP endpoint для приема телеметрии от устройств.
    
    Пример запроса:
    ```json
    {
        "device_id": "550e8400-e29b-41d4-a716-446655440000",
        "timestamp": "2026-03-08T10:00:00Z",
        "metrics": {
            "temperature": 25.5,
            "humidity": 60.0
        }
    }
    ```
    """
    # Проверка размера payload
    content_length = request.headers.get("content-length")
    if content_length:
        size_kb = int(content_length) / 1024
        if size_kb > settings.max_payload_size_kb:
            raise HTTPException(
                status_code=413,
                detail=f"Payload too large: {size_kb:.2f}KB (max: {settings.max_payload_size_kb}KB)"
            )
    
    # Аутентификация (опционально для устройств)
    # В продакшене здесь должна быть проверка API ключа устройства
    
    try:
        # Получаем устройство из БД
        async with db.get_session() as session:
            from sqlalchemy import select
            from app.database.models import Device
            
            query = select(Device).where(Device.id == payload.device_id)
            result = await session.execute(query)
            device = result.scalar_one_or_none()
            
            if not device:
                raise HTTPException(
                    status_code=404,
                    detail=f"Device {payload.device_id} not found"
                )
            
            if device.status != "active":
                raise HTTPException(
                    status_code=403,
                    detail=f"Device {payload.device_id} is not active"
                )
            
            # Получаем драйвер для устройства
            driver = get_driver(device.driver_type)
            if not driver:
                logger.error(f"Driver {device.driver_type} not found for device {payload.device_id}")
                raise HTTPException(
                    status_code=500,
                    detail="Device driver not available"
                )
            
            # Валидация данных драйвером
            if not driver.validate(payload.dict()):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid payload format for device driver"
                )
            
            # Парсинг метрик
            metrics = driver.parse(payload.dict())
            
            if not metrics:
                raise HTTPException(
                    status_code=400,
                    detail="No valid metrics found in payload"
                )
            
            # Подготовка записей телеметрии
            telemetry_records = []
            for metric in metrics:
                telemetry_records.append({
                    "device_id": payload.device_id,
                    "timestamp": payload.timestamp,
                    "metric_name": metric["name"],
                    "value": metric["value"],
                    "unit": metric.get("unit")
                })
            
            # Сохранение в БД
            storage = StorageService(session)
            count = await storage.save_telemetry_batch(telemetry_records)
            
            # Обновление last_seen устройства
            await storage.update_device_last_seen(payload.device_id)
            
            # Добавление в очередь для Rule Engine
            await storage.add_to_internal_queue("telemetry", {
                "device_id": payload.device_id,
                "timestamp": payload.timestamp.isoformat(),
                "metrics": metrics
            })
            
            logger.info(f"Ingested {count} metrics from device {payload.device_id}")
            
            return IngestResponse(
                success=True,
                message="Data ingested successfully",
                metrics_count=count
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ingesting data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error") from e
