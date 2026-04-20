"""
Rule Engine - обработка правил и триггеров
"""
import logging
import asyncio
import re
import ast
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
        self.cleanup_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Запуск Rule Engine"""
        if self.running:
            logger.warning("Rule Engine already running")
            return
        
        self.running = True
        self.task = asyncio.create_task(self._poll_loop())
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Rule Engine started")
    
    async def stop(self):
        """Остановка Rule Engine"""
        if not self.running:
            return
        
        self.running = False
        
        # Остановка poll loop
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        
        # Остановка cleanup loop
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Rule Engine stopped")
    
    async def _cleanup_loop(self):
        """
        Фоновый цикл для regularного cleanup старых данных.
        Запускается каждый час.
        """
        logger.info("Cleanup loop started (runs every 60 minutes)")
        
        while self.running:
            try:
                await asyncio.sleep(3600)  # Каждый час
                
                async with db.get_session() as session:
                    storage = StorageService(session)
                    
                    # Cleanup старой телеметрии
                    deleted_telemetry = await storage.cleanup_old_telemetry()
                    
                    # Cleanup обработанных событий из очереди (старше 7 дней)
                    cutoff_date = datetime.utcnow() - timedelta(days=7)
                    from sqlalchemy import delete
                    from app.database.models import InternalQueue
                    
                    query = delete(InternalQueue).where(
                        (InternalQueue.is_processed.is_(True)) &
                        (InternalQueue.processed_at < cutoff_date)
                    )
                    result = await session.execute(query)
                    await session.commit()
                    deleted_queue = result.rowcount
                    
                    logger.info(
                        f"Cleanup: deleted {deleted_telemetry} old telemetry records "
                        f"and {deleted_queue} old queue items"
                    )
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}", exc_info=True)
    
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
                Trigger.is_active.is_(True),
                (Trigger.device_id == device_id) | (Trigger.device_id.is_(None))
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

            # Логические выражения: "value > 30 and value < 80", "x >= 10 or x == 0"
            if any(token in condition.lower() for token in (" and ", " or ", " not ", "(", ")", "value", "x")):
                return self._evaluate_logical_expression(condition, value)
            
            # Поддерживаемые операторы
            if condition.startswith(">="):
                threshold = float(condition[2:].strip())
                return value >= threshold
            if condition.startswith("<="):
                threshold = float(condition[2:].strip())
                return value <= threshold
            if condition.startswith(">"):
                threshold = float(condition[1:].strip())
                return value > threshold
            if condition.startswith("<"):
                threshold = float(condition[1:].strip())
                return value < threshold
            if condition.startswith("==") or condition.startswith("="):
                threshold = float(condition.lstrip("=").strip())
                return abs(value - threshold) < 0.001  # Float comparison
            if condition.startswith("!="):
                threshold = float(condition[2:].strip())
                return abs(value - threshold) >= 0.001
            
            # Range: "10..30"
            if ".." in condition:
                parts = condition.split("..")
                min_val = float(parts[0].strip())
                max_val = float(parts[1].strip())
                return min_val <= value <= max_val
            
            logger.warning(f"Unknown condition format: {condition}")
            return False
        
        except Exception as e:
            logger.error(f"Error evaluating condition '{condition}': {e}")
            return False

    def _evaluate_logical_expression(self, condition: str, value: float) -> bool:
        """
        Безопасная оценка логического выражения для поля condition.

        Поддерживает:
        - value/x как переменную метрики
        - and/or/not, скобки
        - сравнения >, >=, <, <=, ==, !=
        - числовые литералы
        """
        normalized = condition.strip()
        # Поддержка популярных JS-подобных операторов
        normalized = normalized.replace("&&", " and ").replace("||", " or ")

        # Аккуратно заменяем "!" на "not", не трогая "!="
        if "!=" in normalized:
            normalized = normalized.replace("!=", " __NE__ ")
            normalized = normalized.replace("!", " not ")
            normalized = normalized.replace(" __NE__ ", " != ")
        else:
            normalized = normalized.replace("!", " not ")

        tree = ast.parse(normalized, mode="eval")

        allowed_nodes = (
            ast.Expression,
            ast.BoolOp,
            ast.UnaryOp,
            ast.Compare,
            ast.Name,
            ast.Load,
            ast.Constant,
            ast.And,
            ast.Or,
            ast.Not,
            ast.Gt,
            ast.GtE,
            ast.Lt,
            ast.LtE,
            ast.Eq,
            ast.NotEq,
        )

        for node in ast.walk(tree):
            if not isinstance(node, allowed_nodes):
                logger.warning(f"Unsafe node in condition expression: {type(node).__name__}")
                return False

        def eval_node(node):
            if isinstance(node, ast.Expression):
                return eval_node(node.body)

            if isinstance(node, ast.BoolOp):
                values = [bool(eval_node(v)) for v in node.values]
                if isinstance(node.op, ast.And):
                    return all(values)
                if isinstance(node.op, ast.Or):
                    return any(values)
                return False

            if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
                return not bool(eval_node(node.operand))

            if isinstance(node, ast.Name):
                if node.id in ("value", "x"):
                    return float(value)
                raise ValueError(f"Unknown variable: {node.id}")

            if isinstance(node, ast.Constant):
                if isinstance(node.value, (int, float, bool)):
                    return node.value
                raise ValueError("Only numeric and boolean constants are allowed")

            if isinstance(node, ast.Compare):
                left = eval_node(node.left)
                for op, comparator in zip(node.ops, node.comparators):
                    right = eval_node(comparator)

                    if isinstance(op, ast.Gt):
                        ok = left > right
                    elif isinstance(op, ast.GtE):
                        ok = left >= right
                    elif isinstance(op, ast.Lt):
                        ok = left < right
                    elif isinstance(op, ast.LtE):
                        ok = left <= right
                    elif isinstance(op, ast.Eq):
                        ok = abs(left - right) < 0.001
                    elif isinstance(op, ast.NotEq):
                        ok = abs(left - right) >= 0.001
                    else:
                        return False

                    if not ok:
                        return False
                    left = right

                return True

            raise ValueError(f"Unsupported node: {type(node).__name__}")

        return bool(eval_node(tree))
    
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
        Отправка вебхука и/или Firebase уведомления при срабатывании триггера.
        
        Args:
            session: Сессия БД
            trigger: Триггер
            device_id: ID устройства
            metric_name: Имя метрики
            metric_value: Значение метрики
            timestamp: Время события
        """
        # Контекст для подстановки в шаблоны
        context = {
            "trigger_id": trigger.id,
            "trigger_name": trigger.name,
            "device_id": device_id,
            "metric": metric_name,
            "metric_name": metric_name,
            "value": metric_value,
            "condition": trigger.condition,
            "timestamp": timestamp.isoformat()
        }
        
        # Отправляем Firebase уведомление (если настроено)
        firebase_result = None
        if trigger.firebase_notification:
            try:
                firebase_result = await webhook_dispatcher.send_firebase_notification(
                    trigger.firebase_notification,
                    context
                )
                logger.info(
                    f"Firebase notification for trigger {trigger.id}: "
                    f"{'success' if firebase_result['success'] else 'failed'}"
                )
            except Exception as e:
                logger.error(f"Error sending Firebase notification: {e}", exc_info=True)
                firebase_result = {
                    "success": False,
                    "error_message": str(e)
                }
        
        # Отправляем вебхук (если настроен)
        webhook_result = None
        if trigger.webhook_url:
            # Формируем payload вебхука
            webhook_payload = {
                **context,
                "message": f"Trigger '{trigger.name}' fired: {metric_name} {trigger.condition} (value: {metric_value})"
            }
            
            try:
                webhook_result = await webhook_dispatcher.send_webhook(
                    trigger.webhook_url,
                    webhook_payload
                )
                logger.info(
                    f"Webhook for trigger {trigger.id}: "
                    f"{'success' if webhook_result['success'] else 'failed'}"
                )
            except Exception as e:
                logger.error(f"Error sending webhook: {e}", exc_info=True)
                webhook_result = {
                    "success": False,
                    "error_message": str(e)
                }
        
        # Определяем общий успех: хотя бы одна отправка успешна
        overall_success = (
            (firebase_result and firebase_result.get("success")) or
            (webhook_result and webhook_result.get("success"))
        )
        
        # Логируем результат (предпочитаем webhook_result для совместимости)
        primary_result = webhook_result or firebase_result or {"success": False}
        
        webhook_log = WebhookLog(
            trigger_id=trigger.id,
            device_id=device_id,
            metric_name=metric_name,
            metric_value=metric_value,
            status_code=primary_result.get("status_code"),
            response_body=primary_result.get("response_body"),
            success=overall_success,
            error_message=primary_result.get("error_message")
        )
        session.add(webhook_log)
        
        # ⚠️ ВАЖНО: Обновляем last_triggered_at ТОЛЬКО при успешной отправке!
        # Это гарантирует, что неудачные попытки не "гасят" cooldown для следующих попыток
        if overall_success:
            trigger.last_triggered_at = datetime.utcnow()
            logger.info(
                f"Trigger {trigger.id} success: cooldown now active for {trigger.cooldown_sec}s"
            )
        else:
            logger.warning(f"Trigger {trigger.id} failed to send notification, cooldown NOT updated")
        
        await session.commit()


# Глобальный экземпляр Rule Engine
rule_engine = RuleEngine()
