"""
Middleware для API Gateway
"""
import logging
import time
from typing import Callable
from fastapi import Request, Response, HTTPException, Header
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from app.config import settings

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware для аутентификации запросов"""
    
    # Публичные эндпоинты без аутентификации
    PUBLIC_PATHS = ["/health", "/docs", "/openapi.json", "/redoc"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Пропускаем публичные пути
        if any(request.url.path.startswith(path) for path in self.PUBLIC_PATHS):
            return await call_next(request)
        
        # Проверяем API ключ
        api_key = request.headers.get("X-API-Key")
        
        if not api_key:
            return JSONResponse(
                status_code=401,
                content={"detail": "API key required"}
            )
        
        # Простая проверка ключа (в продакшене использовать БД)
        if api_key != settings.api_key:
            return JSONResponse(
                status_code=403,
                content={"detail": "Invalid API key"}
            )
        
        response = await call_next(request)
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware для логирования запросов"""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        
        # Логируем входящий запрос
        logger.info(f"→ {request.method} {request.url.path}")
        
        response = await call_next(request)
        
        # Логируем ответ
        process_time = time.time() - start_time
        logger.info(
            f"← {request.method} {request.url.path} "
            f"[{response.status_code}] {process_time:.3f}s"
        )
        
        # Добавляем заголовок с временем обработки
        response.headers["X-Process-Time"] = str(process_time)
        
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware для ограничения частоты запросов (простая реализация)"""
    
    def __init__(self, app, rate_limit: int = 60):
        super().__init__(app)
        self.rate_limit = rate_limit
        self.requests = {}  # IP -> список timestamp'ов
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = request.client.host
        current_time = time.time()
        
        # Очищаем старые записи (старше 1 минуты)
        if client_ip in self.requests:
            self.requests[client_ip] = [
                ts for ts in self.requests[client_ip]
                if current_time - ts < 60
            ]
        else:
            self.requests[client_ip] = []
        
        # Проверяем лимит
        if len(self.requests[client_ip]) >= self.rate_limit:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": f"Rate limit exceeded. Max {self.rate_limit} requests per minute"
                }
            )
        
        # Добавляем текущий запрос
        self.requests[client_ip].append(current_time)
        
        response = await call_next(request)
        
        # Добавляем заголовки с информацией о лимите
        response.headers["X-RateLimit-Limit"] = str(self.rate_limit)
        response.headers["X-RateLimit-Remaining"] = str(
            self.rate_limit - len(self.requests[client_ip])
        )
        
        return response
