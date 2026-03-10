"""
Webhook Dispatcher - отправка HTTP запросов на внешние URL и Firebase уведомлений
"""
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional, List
import httpx
from app.config import settings

logger = logging.getLogger(__name__)


class WebhookDispatcher:
    """Диспетчер отправки вебхуков и Firebase уведомлений"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=settings.webhook_timeout_seconds)
    
    async def send_webhook(
        self,
        url: str,
        payload: Dict[str, Any],
        max_retries: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Отправка вебхука с поддержкой retry.
        
        Args:
            url: URL вебхука
            payload: Данные для отправки
            max_retries: Максимальное количество попыток (по умолчанию из настроек)
            
        Returns:
            Результат отправки
        """
        if max_retries is None:
            max_retries = settings.webhook_max_retries
        
        last_error = None
        retry_delay = settings.webhook_retry_delay_seconds
        
        for attempt in range(max_retries + 1):
            try:
                # Добавляем заголовки
                headers = {
                    "Content-Type": "application/json",
                    "User-Agent": f"IoT-Core/{settings.app_name}",
                }
                
                # Опционально: добавляем HMAC подпись для безопасности
                # if settings.webhook_secret:
                #     signature = self._generate_signature(payload)
                #     headers["X-IoT-Signature"] = signature
                
                logger.info(f"Sending webhook to {url} (attempt {attempt + 1}/{max_retries + 1})")
                
                response = await self.client.post(
                    url,
                    json=payload,
                    headers=headers
                )
                
                # Проверяем код ответа
                if response.status_code == 200 or response.status_code == 201:
                    logger.info(f"Webhook sent successfully to {url}")
                    return {
                        "success": True,
                        "status_code": response.status_code,
                        "response_body": response.text[:500],  # Ограничиваем размер
                        "error_message": None
                    }
                else:
                    logger.warning(
                        f"Webhook returned non-200 status: {response.status_code}"
                    )
                    last_error = f"HTTP {response.status_code}: {response.text[:200]}"
            
            except httpx.TimeoutException as e:
                last_error = f"Timeout: {str(e)}"
                logger.warning(f"Webhook timeout for {url}: {e}")
            
            except httpx.RequestError as e:
                last_error = f"Request error: {str(e)}"
                logger.warning(f"Webhook request error for {url}: {e}")
            
            except Exception as e:
                last_error = f"Unexpected error: {str(e)}"
                logger.error(f"Unexpected error sending webhook to {url}: {e}", exc_info=True)
            
            # Ждем перед следующей попыткой (с экспоненциальной задержкой)
            if attempt < max_retries:
                delay = retry_delay * (2 ** attempt)  # Экспоненциальная задержка
                logger.info(f"Retrying in {delay}s...")
                await asyncio.sleep(delay)
        
        # Все попытки исчерпаны
        logger.error(f"Failed to send webhook to {url} after {max_retries + 1} attempts")
        return {
            "success": False,
            "status_code": None,
            "response_body": None,
            "error_message": last_error
        }
    
    async def send_firebase_notification(
        self,
        firebase_config: Dict[str, Any],
        context: Dict[str, Any],
        max_retries: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Отправка Firebase уведомления.
        
        Args:
            firebase_config: Конфигурация Firebase {url, title, text, ids}
            context: Контекст с данными для подстановки {device_id, metric_name, value, ...}
            max_retries: Максимальное количество попыток
            
        Returns:
            Результат отправки
        """
        try:
            url = firebase_config.get("url")
            title = firebase_config.get("title", "")
            text = firebase_config.get("text", "")
            user_ids = firebase_config.get("ids", [])
            
            if not url or not user_ids:
                logger.error("Firebase notification requires url and ids")
                return {
                    "success": False,
                    "status_code": None,
                    "response_body": None,
                    "error_message": "Missing url or ids in firebase_config"
                }
            
            # Подстановка значений в title и text
            for key, value in context.items():
                placeholder = f"{{{key}}}"
                title = title.replace(placeholder, str(value))
                text = text.replace(placeholder, str(value))
            
            # Формируем payload для Firebase
            payload = {
                "title": title,
                "text": text,
                "ids": user_ids
            }
            
            logger.info(f"Sending Firebase notification to {len(user_ids)} users: {title}")
            
            # Отправляем через стандартный метод send_webhook
            result = await self.send_webhook(url, payload, max_retries)
            
            if result["success"]:
                logger.info(f"Firebase notification sent successfully")
            else:
                logger.error(f"Failed to send Firebase notification: {result.get('error_message')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error sending Firebase notification: {e}", exc_info=True)
            return {
                "success": False,
                "status_code": None,
                "response_body": None,
                "error_message": f"Exception: {str(e)}"
            }
    
    async def close(self):
        """Закрытие HTTP клиента"""
        await self.client.aclose()


# Глобальный экземпляр dispatcher
webhook_dispatcher = WebhookDispatcher()
