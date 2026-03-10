"""
API Routes - REST API эндпоинты
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from uuid import uuid4
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.database.models import Device, Telemetry, Trigger, WebhookLog, DeviceStatus
from app.modules.storage import StorageService
from app.modules.engine import webhook_dispatcher
from app.drivers import list_available_drivers, get_driver

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["api"])


# ===== Pydantic Models =====

class DeviceCreate(BaseModel):
    """Модель создания устройства"""
    id: Optional[str] = Field(None, description="UUID (генерируется автоматически если не указан)")
    name: str = Field(..., description="Название устройства")
    driver_type: str = Field(default="generic_json", description="Тип драйвера")
    config: Optional[dict] = Field(None, description="Конфигурация устройства")


class DeviceResponse(BaseModel):
    """Модель ответа с устройством"""
    id: str
    name: str
    driver_type: str
    config: Optional[dict]
    status: str
    last_seen: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class TelemetryResponse(BaseModel):
    """Модель телеметрии"""
    id: int
    device_id: str
    timestamp: datetime
    metric_name: str
    value: float
    unit: Optional[str]
    
    class Config:
        from_attributes = True


class FirebaseNotification(BaseModel):
    """Модель Firebase уведомления"""
    url: str = Field(..., description="URL для отправки уведомления")
    title: str = Field(..., description="Заголовок уведомления")
    text: str = Field(..., description="Текст уведомления")
    ids: List[int] = Field(..., description="ID пользователей")


class TriggerCreate(BaseModel):
    """Модель создания триггера"""
    name: str = Field(..., description="Название триггера")
    device_id: Optional[str] = Field(None, description="ID устройства (null для всех)")
    metric_name: str = Field(..., description="Имя метрики")
    condition: str = Field(..., description="Условие (например, '> 25')")
    webhook_url: Optional[str] = Field(None, description="URL вебхука (опционально)")
    firebase_notification: Optional[FirebaseNotification] = Field(None, description="Firebase уведомление (обязательно)")
    cooldown_sec: int = Field(default=60, description="Cooldown в секундах")
    is_active: bool = Field(default=True, description="Активен ли триггер")


class TriggerResponse(BaseModel):
    """Модель ответа с триггером"""
    id: int
    name: str
    device_id: Optional[str]
    metric_name: str
    condition: str
    webhook_url: Optional[str]
    firebase_notification: Optional[dict]
    cooldown_sec: int
    is_active: bool
    last_triggered_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class WebhookTestRequest(BaseModel):
    """Запрос на тестовую отправку вебхука"""
    url: str = Field(..., description="URL вебхука")
    payload: dict = Field(default={}, description="Данные для отправки")


# ===== Devices Endpoints =====

@router.get("/devices", response_model=List[DeviceResponse])
async def list_devices(
    status: Optional[str] = Query(None, description="Фильтр по статусу"),
    db: AsyncSession = Depends(get_db)
):
    """Получить список устройств"""
    query = select(Device)
    
    if status:
        query = query.where(Device.status == status)
    
    result = await db.execute(query)
    devices = result.scalars().all()
    
    return devices


@router.post("/devices", response_model=DeviceResponse, status_code=201)
async def create_device(
    device_data: DeviceCreate,
    db: AsyncSession = Depends(get_db)
):
    """Создать новое устройство"""
    # Генерируем UUID если не указан
    device_id = device_data.id or str(uuid4())
    
    # Проверяем существование
    query = select(Device).where(Device.id == device_id)
    result = await db.execute(query)
    existing = result.scalar_one_or_none()
    
    if existing:
        raise HTTPException(status_code=409, detail="Device already exists")
    
    # Создаем устройство
    device = Device(
        id=device_id,
        name=device_data.name,
        driver_type=device_data.driver_type,
        config=device_data.config,
        status=DeviceStatus.ACTIVE.value
    )
    
    db.add(device)
    await db.commit()
    await db.refresh(device)
    
    logger.info(f"Created device: {device_id}")
    return device


@router.get("/devices/{device_id}", response_model=DeviceResponse)
async def get_device(
    device_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Получить информацию об устройстве"""
    query = select(Device).where(Device.id == device_id)
    result = await db.execute(query)
    device = result.scalar_one_or_none()
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    return device


@router.put("/devices/{device_id}", response_model=DeviceResponse)
async def update_device(
    device_id: str,
    device_data: DeviceCreate,
    db: AsyncSession = Depends(get_db)
):
    """Обновить устройство"""
    query = select(Device).where(Device.id == device_id)
    result = await db.execute(query)
    device = result.scalar_one_or_none()
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Обновляем поля
    device.name = device_data.name
    device.driver_type = device_data.driver_type
    device.config = device_data.config
    
    await db.commit()
    await db.refresh(device)
    
    logger.info(f"Updated device: {device_id}")
    return device


@router.delete("/devices/{device_id}", status_code=204)
async def delete_device(
    device_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Удалить устройство"""
    query = select(Device).where(Device.id == device_id)
    result = await db.execute(query)
    device = result.scalar_one_or_none()
    
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    await db.delete(device)
    await db.commit()
    
    logger.info(f"Deleted device: {device_id}")


# ===== Telemetry Endpoints =====

@router.get("/telemetry/{device_id}", response_model=List[TelemetryResponse])
async def get_telemetry(
    device_id: str,
    start_time: Optional[datetime] = Query(None, description="Начало диапазона"),
    end_time: Optional[datetime] = Query(None, description="Конец диапазона"),
    metric_name: Optional[str] = Query(None, description="Имя метрики"),
    limit: int = Query(1000, description="Максимальное количество записей", le=10000),
    db: AsyncSession = Depends(get_db)
):
    """Получить историю телеметрии для устройства"""
    storage = StorageService(db)
    telemetry = await storage.get_telemetry(
        device_id=device_id,
        start_time=start_time,
        end_time=end_time,
        metric_name=metric_name,
        limit=limit
    )
    
    return telemetry


# ===== Triggers Endpoints =====

@router.get("/triggers", response_model=List[TriggerResponse])
async def list_triggers(
    device_id: Optional[str] = Query(None, description="Фильтр по устройству"),
    is_active: Optional[bool] = Query(None, description="Фильтр по статусу"),
    db: AsyncSession = Depends(get_db)
):
    """Получить список триггеров"""
    query = select(Trigger)
    
    if device_id:
        query = query.where(Trigger.device_id == device_id)
    
    if is_active is not None:
        query = query.where(Trigger.is_active == is_active)
    
    result = await db.execute(query)
    triggers = result.scalars().all()
    
    return triggers


@router.post("/triggers", response_model=TriggerResponse, status_code=201)
async def create_trigger(
    trigger_data: TriggerCreate,
    db: AsyncSession = Depends(get_db)
):
    """Создать новый триггер"""
    # Проверка: должен быть указан хотя бы один способ уведомления
    if not trigger_data.firebase_notification and not trigger_data.webhook_url:
        raise HTTPException(
            status_code=400, 
            detail="Either firebase_notification or webhook_url must be provided"
        )
    
    # Если указан device_id, проверяем существование устройства
    if trigger_data.device_id:
        query = select(Device).where(Device.id == trigger_data.device_id)
        result = await db.execute(query)
        device = result.scalar_one_or_none()
        
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
    
    # Создаем триггер
    firebase_data = None
    if trigger_data.firebase_notification:
        firebase_data = trigger_data.firebase_notification.model_dump()
    
    trigger = Trigger(
        name=trigger_data.name,
        device_id=trigger_data.device_id,
        metric_name=trigger_data.metric_name,
        condition=trigger_data.condition,
        webhook_url=trigger_data.webhook_url or "",
        firebase_notification=firebase_data,
        cooldown_sec=trigger_data.cooldown_sec,
        is_active=trigger_data.is_active
    )
    
    db.add(trigger)
    await db.commit()
    await db.refresh(trigger)
    
    logger.info(f"Created trigger: {trigger.id} (Firebase: {bool(firebase_data)}, Webhook: {bool(trigger_data.webhook_url)})")
    return trigger


@router.put("/triggers/{trigger_id}", response_model=TriggerResponse)
async def update_trigger(
    trigger_id: int,
    trigger_data: TriggerCreate,
    db: AsyncSession = Depends(get_db)
):
    """Обновить триггер"""
    query = select(Trigger).where(Trigger.id == trigger_id)
    result = await db.execute(query)
    trigger = result.scalar_one_or_none()
    
    if not trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")
    
    # Проверка: должен быть указан хотя бы один способ уведомления
    if not trigger_data.firebase_notification and not trigger_data.webhook_url:
        raise HTTPException(
            status_code=400, 
            detail="Either firebase_notification or webhook_url must be provided"
        )
    
    # Обновляем поля
    firebase_data = None
    if trigger_data.firebase_notification:
        firebase_data = trigger_data.firebase_notification.model_dump()
    
    trigger.name = trigger_data.name
    trigger.device_id = trigger_data.device_id
    trigger.metric_name = trigger_data.metric_name
    trigger.condition = trigger_data.condition
    trigger.webhook_url = trigger_data.webhook_url or ""
    trigger.firebase_notification = firebase_data
    trigger.cooldown_sec = trigger_data.cooldown_sec
    trigger.is_active = trigger_data.is_active
    
    await db.commit()
    await db.refresh(trigger)
    
    logger.info(f"Updated trigger: {trigger_id}")
    return trigger


@router.delete("/triggers/{trigger_id}", status_code=204)
async def delete_trigger(
    trigger_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Удалить триггер"""
    query = select(Trigger).where(Trigger.id == trigger_id)
    result = await db.execute(query)
    trigger = result.scalar_one_or_none()
    
    if not trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")
    
    await db.delete(trigger)
    await db.commit()
    
    logger.info(f"Deleted trigger: {trigger_id}")


# ===== Webhooks Endpoints =====

@router.post("/webhooks/test")
async def test_webhook(webhook_test: WebhookTestRequest):
    """Тестовая отправка вебхука"""
    result = await webhook_dispatcher.send_webhook(
        webhook_test.url,
        webhook_test.payload or {"test": "data", "timestamp": datetime.utcnow().isoformat()}
    )
    
    return {
        "success": result["success"],
        "status_code": result.get("status_code"),
        "error_message": result.get("error_message")
    }


@router.get("/webhooks/logs")
async def get_webhook_logs(
    trigger_id: Optional[int] = Query(None, description="Фильтр по триггеру"),
    limit: int = Query(100, description="Максимальное количество записей", le=1000),
    db: AsyncSession = Depends(get_db)
):
    """Получить журнал вебхуков"""
    query = select(WebhookLog)
    
    if trigger_id:
        query = query.where(WebhookLog.trigger_id == trigger_id)
    
    query = query.order_by(WebhookLog.sent_at.desc()).limit(limit)
    
    result = await db.execute(query)
    logs = result.scalars().all()
    
    return [
        {
            "id": log.id,
            "trigger_id": log.trigger_id,
            "device_id": log.device_id,
            "metric_name": log.metric_name,
            "metric_value": log.metric_value,
            "sent_at": log.sent_at,
            "status_code": log.status_code,
            "success": log.success,
            "error_message": log.error_message
        }
        for log in logs
    ]


# ===== System Endpoints =====

@router.get("/drivers")
async def get_drivers():
    """Получить список доступных драйверов"""
    drivers = list_available_drivers()
    return {"drivers": drivers}


@router.get("/metrics")
async def get_metrics(
    device_id: Optional[str] = Query(None, description="Фильтр по устройству"),
    db: AsyncSession = Depends(get_db)
):
    """Получить список существующих метрик из телеметрии"""
    query = select(Telemetry.metric_name).distinct().order_by(Telemetry.metric_name)

    if device_id:
        query = query.where(Telemetry.device_id == device_id)

    result = await db.execute(query)
    metrics = [row[0] for row in result.all() if row[0]]

    return {"metrics": metrics}


@router.get("/metrics/suggestions")
async def get_metric_suggestions(
    device_id: Optional[str] = Query(None, description="ID устройства для подсказок"),
    db: AsyncSession = Depends(get_db)
):
    """Получить подсказки метрик (из телеметрии + из драйвера устройства)."""
    suggestions = set()

    # 1. Метрики из телеметрии
    query = select(Telemetry.metric_name).distinct().order_by(Telemetry.metric_name)
    if device_id:
        query = query.where(Telemetry.device_id == device_id)

    result = await db.execute(query)
    for row in result.all():
        if row[0]:
            suggestions.add(row[0])

    # 2. Подсказки из драйвера выбранного устройства
    driver_hints = []
    driver_type = None
    if device_id:
        device_result = await db.execute(select(Device).where(Device.id == device_id))
        device = device_result.scalar_one_or_none()
        if device:
            driver_type = device.driver_type
            driver = get_driver(driver_type)
            if driver:
                driver_hints = driver.get_metric_hints()
                suggestions.update(driver_hints)

    return {
        "metrics": sorted(suggestions),
        "driver_type": driver_type,
        "driver_hints": driver_hints,
    }


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Получить статистику системы"""
    # Количество устройств
    devices_query = select(func.count()).select_from(Device)
    devices_result = await db.execute(devices_query)
    devices_count = devices_result.scalar()
    
    # Количество активных устройств
    active_devices_query = select(func.count()).select_from(Device).where(
        Device.status == DeviceStatus.ACTIVE.value
    )
    active_result = await db.execute(active_devices_query)
    active_count = active_result.scalar()
    
    # Количество триггеров
    triggers_query = select(func.count()).select_from(Trigger)
    triggers_result = await db.execute(triggers_query)
    triggers_count = triggers_result.scalar()
    
    # Количество записей телеметрии за последние 24 часа
    yesterday = datetime.utcnow() - timedelta(days=1)
    telemetry_query = select(func.count()).select_from(Telemetry).where(
        Telemetry.timestamp >= yesterday
    )
    telemetry_result = await db.execute(telemetry_query)
    telemetry_count = telemetry_result.scalar()
    
    return {
        "devices_total": devices_count,
        "devices_active": active_count,
        "triggers_total": triggers_count,
        "telemetry_24h": telemetry_count
    }
