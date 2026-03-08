"""
Модели базы данных
"""
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, 
    ForeignKey, Text, JSON, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class DeviceStatus(str, Enum):
    """Статус устройства"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"


class Device(Base):
    """Модель устройства"""
    __tablename__ = "devices"
    
    id = Column(String(36), primary_key=True)  # UUID
    name = Column(String(255), nullable=False)
    driver_type = Column(String(100), nullable=False, default="generic_json")
    config = Column(JSON, nullable=True)  # Специфичные настройки
    status = Column(String(20), nullable=False, default=DeviceStatus.ACTIVE.value)
    last_seen = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_device_status', 'status'),
    )


class Telemetry(Base):
    """Модель телеметрии"""
    __tablename__ = "telemetry"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String(36), ForeignKey('devices.id', ondelete='CASCADE'), nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    metric_name = Column(String(100), nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String(50), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    
    __table_args__ = (
        Index('idx_telemetry_device_time', 'device_id', 'timestamp'),
        Index('idx_telemetry_metric', 'metric_name'),
    )


class Trigger(Base):
    """Модель триггера (правила)"""
    __tablename__ = "triggers"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    device_id = Column(String(36), ForeignKey('devices.id', ondelete='CASCADE'), nullable=True)  # NULL = для всех
    metric_name = Column(String(100), nullable=False)
    condition = Column(String(255), nullable=False)  # Например: "> 25"
    webhook_url = Column(String(500), nullable=False)
    cooldown_sec = Column(Integer, nullable=False, default=60)
    is_active = Column(Boolean, nullable=False, default=True)
    last_triggered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index('idx_trigger_active', 'is_active'),
        Index('idx_trigger_metric', 'metric_name'),
    )


class WebhookLog(Base):
    """Журнал отправки вебхуков"""
    __tablename__ = "webhook_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    trigger_id = Column(Integer, ForeignKey('triggers.id', ondelete='CASCADE'), nullable=False)
    device_id = Column(String(36), nullable=False)
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(Float, nullable=False)
    sent_at = Column(DateTime, nullable=False, server_default=func.now())
    status_code = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    success = Column(Boolean, nullable=False, default=False)
    error_message = Column(Text, nullable=True)
    
    __table_args__ = (
        Index('idx_webhook_trigger', 'trigger_id'),
        Index('idx_webhook_sent_at', 'sent_at'),
    )


class InternalQueue(Base):
    """Внутренняя очередь событий"""
    __tablename__ = "internal_queue"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    event_type = Column(String(50), nullable=False)  # telemetry, trigger, etc.
    payload = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    processed_at = Column(DateTime, nullable=True)
    is_processed = Column(Boolean, nullable=False, default=False)
    
    __table_args__ = (
        Index('idx_queue_processed', 'is_processed', 'created_at'),
    )
