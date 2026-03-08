"""
Rule Engine - обработка правил и триггеров
"""
import logging
import asyncio
import re
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import db
from app.database.models import Trigger, Telemetry, WebhookLog
from app.modules.storage import StorageService
from app.modules.engine.webhook_dispatcher import webhook_dispatcher
from app.config import settings

logger = logging.getLogger(__name__)


class RuleEngine:
    """Движок обработки правил и триггеров"""
    
    def __init__(self):
        self.running = False
        self.task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Запуск Rule Engine"""
        if self.running:
            logger.warning("Rule Engine already running")
            return
        
        self.running = True
        self.task = asyncio.create_task(self._poll_loop())
        logger.info("Rule Engine started")
    
    async def stop(self):
        """Остановка Rule Engine"""
        if not self.running:
            return
        
        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        logger.info("Rule Engine stopped")
    
    async def _poll_loop(self):
        """Основной цикл обработки событий"""
        logger.info("Rule Engine poll loop started")
        
        while self.running:
            try:
                async with db.get_session() as session:
                    # Получаем необработанные события из очереди
                    storage = StorageService(session)
                    queue_items = await storage.get_unprocessed_queue_items(limit=100)
                    
                    for item in queue_items:
                        # Обрабатываем только события телеметрии
                        if item.event_type == "telemetry":
                            await self._process_telemetry_event(session, item.payload)
                        
                        # Отмечаем как обработанное
                        await storage.mark_queue_item_processed(item.id)
                
                # Пауза перед следующим циклом
                await asyncio.sleep(settings.rule_engine_poll_interval_seconds)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in Rule Engine poll loop: {e}", exc_info=True)
                await asyncio.sleep(5)  # Пауза при ошибке
    
    async def _process_telemetry_event(self, session: AsyncSession, payload: Dict[str, Any]):
        """
        Обработка события телеметрии.
        
        Args:
            session: Сессия БД
            payload: Данные события
        """
        device_id = payload.get("device_id")
        metrics = payload.get("metrics", [])
        timestamp_str = payload.get("timestamp")
        
        if isinstance(timestamp_str, str):
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        else:
            timestamp = datetime.utcnow()
        
        # Получаем активные триггеры для этого устройства
        triggers = await self._get_active_triggers(session, device_id)
        
        # Проверяем каждую метрику против триггеров
        for metric in metrics:
            metric_name = metric.get("name")
            metric_value = metric.get("value")
            
            for trigger in triggers:
                # Проверяем совпадение метрики
                if trigger.metric_name != metric_name:
                    continue
                
                # Проверяем cooldown
                if not self._check_cooldown(trigger):
                    continue
                
                # Оцениваем условие
                if self._evaluate_condition(trigger.condition, metric_value):
                    logger.info(
                        f"Trigger {trigger.id} fired: {metric_name} {trigger.condition} "
                        f"(value: {metric_value})"
                    )
                    
                    # Отправляем вебхук
                    await self._fire_webhook(
                        session,
                        trigger,
                        device_id,
                        metric_name,
                        metric_value,
                        timestamp
                    )
    
    async def _get_active_triggers(
        self,
        session: AsyncSession,
        device_id: str
    ) -> List[Trigger]:
        """
        Получить активные триггеры для устройства.
        
        Args:
            session: Сессия БД
            device_id: ID устройства
            
        Returns:
            Список активных триггеров
        """
        # Триггеры для конкретного устройства или для всех (device_id IS NULL)
        query = select(Trigger).where(
            and_(
                Trigger.is_active == True,
                (Trigger.device_id == device_id) | (Trigger.device_id == None)
            )
        )
        
        result = await session.execute(query)
        return result.scalars().all()
    
    def _check_cooldown(self, trigger: Trigger) -> bool:
        """
        Проверка cooldown периода триггера.
        
        Args:
            trigger: Триггер
            
        Returns:
            True если можно запускать, False если еще в cooldown
        """
        if not trigger.last_triggered_at:
            return True
        
        cooldown_end = trigger.last_triggered_at + timedelta(seconds=trigger.cooldown_sec)
        return datetime.utcnow() >= cooldown_end
    
    def _evaluate_condition(self, condition: str, value: float) -> bool:
        """
        Оценка условия триггера.
        
        Args:
            condition: Условие в виде строки (например, "> 25")
            value: Значение метрики
            
        Returns:
            True если условие выполнено
        """
        try:
            # Парсим условие
            condition = condition.strip()
            
            # Поддерживаемые операторы
            if condition.startswith(">="):
                threshold = float(condition[2:].strip())
                return value >= threshold
            elif condition.startswith("<="):
                threshold = float(condition[2:].strip())
                return value <= threshold
            elif condition.startswith(">"):
                threshold = float(condition[1:].strip())
                return value > threshold
            elif condition.startswith("<"):
                threshold = float(condition[1:].strip())
                return value < threshold
            elif condition.startswith("==") or condition.startswith("="):
                threshold = float(condition.lstrip("=").strip())
                return abs(value - threshold) < 0.001  # Float comparison
            elif condition.startswith("!="):
                threshold = float(condition[2:].strip())
                return abs(value - threshold) >= 0.001
            
            # Range: "10..30"
            elif ".." in condition:
                parts = condition.split("..")
                min_val = float(parts[0].strip())
                max_val = float(parts[1].strip())
                return min_val <= value <= max_val
            
            else:
                logger.warning(f"Unknown condition format: {condition}")
                return False
        
        except Exception as e:
            logger.error(f"Error evaluating condition '{condition}': {e}")
            return False
    
    async def _fire_webhook(
        self,
        session: AsyncSession,
        trigger: Trigger,
        device_id: str,
        metric_name: str,
        metric_value: float,
        timestamp: datetime
    ):
        """
        Отправка вебхука при срабатывании триггера.
        
        Args:
            session: Сессия БД
            trigger: Триггер
            device_id: ID устройства
            metric_name: Имя метрики
            metric_value: Значение метрики
            timestamp: Время события
        """
        # Формируем payload вебхука
        webhook_payload = {
            "trigger_id": trigger.id,
            "trigger_name": trigger.name,
            "device_id": device_id,
            "metric": metric_name,
            "value": metric_value,
            "condition": trigger.condition,
            "timestamp": timestamp.isoformat(),
            "message": f"Trigger '{trigger.name}' fired: {metric_name} {trigger.condition} (value: {metric_value})"
        }
        
        # Отправляем вебхук
        result = await webhook_dispatcher.send_webhook(
            trigger.webhook_url,
            webhook_payload
        )
        
        # Логируем результат
        webhook_log = WebhookLog(
            trigger_id=trigger.id,
            device_id=device_id,
            metric_name=metric_name,
            metric_value=metric_value,
            status_code=result.get("status_code"),
            response_body=result.get("response_body"),
            success=result["success"],
            error_message=result.get("error_message")
        )
        session.add(webhook_log)
        
        # Обновляем время последнего срабатывания
        trigger.last_triggered_at = datetime.utcnow()
        
        await session.commit()


# Глобальный экземпляр Rule Engine
rule_engine = RuleEngine()
