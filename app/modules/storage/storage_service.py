"""
Модуль хранения данных (Storage Module)
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy import select, delete, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.models import Device, Telemetry, InternalQueue
from app.config import settings

logger = logging.getLogger(__name__)


class StorageService:
    """Сервис управления хранением данных"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def save_telemetry_batch(self, telemetry_records: List[Dict[str, Any]]) -> int:
        """
        Пакетная запись телеметрии.
        
        Args:
            telemetry_records: Список записей телеметрии
            
        Returns:
            Количество сохраненных записей
        """
        try:
            count = 0
            for record in telemetry_records:
                telemetry = Telemetry(
                    device_id=record["device_id"],
                    timestamp=record["timestamp"],
                    metric_name=record["metric_name"],
                    value=record["value"],
                    unit=record.get("unit")
                )
                self.session.add(telemetry)
                count += 1
            
            await self.session.commit()
            logger.info(f"Saved {count} telemetry records")
            return count
        
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Error saving telemetry: {e}")
            raise
    
    async def get_telemetry(
        self,
        device_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        metric_name: Optional[str] = None,
        limit: int = 1000
    ) -> List[Telemetry]:
        """
        Получить историю телеметрии для устройства.
        
        Args:
            device_id: ID устройства
            start_time: Начало временного диапазона
            end_time: Конец временного диапазона
            metric_name: Фильтр по имени метрики
            limit: Максимальное количество записей
            
        Returns:
            Список записей телеметрии
        """
        query = select(Telemetry).where(Telemetry.device_id == device_id)
        
        if start_time:
            query = query.where(Telemetry.timestamp >= start_time)
        
        if end_time:
            query = query.where(Telemetry.timestamp <= end_time)
        
        if metric_name:
            query = query.where(Telemetry.metric_name == metric_name)
        
        query = query.order_by(desc(Telemetry.timestamp)).limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def get_latest_metric(self, device_id: str, metric_name: str) -> Optional[Telemetry]:
        """
        Получить последнее значение метрики.
        
        Args:
            device_id: ID устройства
            metric_name: Имя метрики
            
        Returns:
            Последняя запись или None
        """
        query = select(Telemetry).where(
            and_(
                Telemetry.device_id == device_id,
                Telemetry.metric_name == metric_name
            )
        ).order_by(desc(Telemetry.timestamp)).limit(1)
        
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def cleanup_old_telemetry(self) -> int:
        """
        Удаление старых записей телеметрии согласно TTL.
        
        Returns:
            Количество удаленных записей
        """
        cutoff_date = datetime.utcnow() - timedelta(days=settings.telemetry_ttl_days)
        
        query = delete(Telemetry).where(Telemetry.timestamp < cutoff_date)
        
        result = await self.session.execute(query)
        await self.session.commit()
        
        deleted_count = result.rowcount
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} old telemetry records")
        
        return deleted_count
    
    async def update_device_last_seen(self, device_id: str):
        """
        Обновить время последней активности устройства.
        
        Args:
            device_id: ID устройства
        """
        query = select(Device).where(Device.id == device_id)
        result = await self.session.execute(query)
        device = result.scalar_one_or_none()
        
        if device:
            device.last_seen = datetime.utcnow()
            device.status = "active"
            await self.session.commit()
    
    async def add_to_internal_queue(self, event_type: str, payload: Dict[str, Any]):
        """
        Добавить событие во внутреннюю очередь.
        
        Args:
            event_type: Тип события
            payload: Данные события
        """
        queue_item = InternalQueue(
            event_type=event_type,
            payload=payload
        )
        self.session.add(queue_item)
        await self.session.commit()
    
    async def get_unprocessed_queue_items(self, limit: int = 100) -> List[InternalQueue]:
        """
        Получить необработанные события из очереди.
        
        Args:
            limit: Максимальное количество
            
        Returns:
            Список событий
        """
        query = select(InternalQueue).where(
            InternalQueue.is_processed == False
        ).order_by(InternalQueue.created_at).limit(limit)
        
        result = await self.session.execute(query)
        return result.scalars().all()
    
    async def mark_queue_item_processed(self, item_id: int):
        """
        Отметить событие как обработанное.
        
        Args:
            item_id: ID события
        """
        query = select(InternalQueue).where(InternalQueue.id == item_id)
        result = await self.session.execute(query)
        item = result.scalar_one_or_none()
        
        if item:
            item.is_processed = True
            item.processed_at = datetime.utcnow()
            await self.session.commit()
