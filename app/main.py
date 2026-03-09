"""
IoT-Core MVP - Главный модуль приложения
"""
import logging
import sys
from contextlib import asynccontextmanager
from sqlalchemy import text
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from app.config import settings
from app.database import db
from app.modules.ingestion import http_router, mqtt_listener
from app.modules.api import router, LoggingMiddleware, RateLimitMiddleware
from app.modules.engine import rule_engine, webhook_dispatcher

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle events для FastAPI.
    Управление запуском и остановкой фоновых сервисов.
    """
    logger.info(f"Starting {settings.app_name}...")
    
    # Инициализация БД
    try:
        await db.initialize()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
        raise
    
    # Запуск MQTT Listener
    try:
        await mqtt_listener.start()
        logger.info("MQTT Listener started")
    except Exception as e:
        logger.error(f"Failed to start MQTT listener: {e}", exc_info=True)
        # Не критично, продолжаем работу
    
    # Запуск Rule Engine
    try:
        await rule_engine.start()
        logger.info("Rule Engine started")
    except Exception as e:
        logger.error(f"Failed to start Rule Engine: {e}", exc_info=True)
    
    logger.info(f"{settings.app_name} started successfully")
    
    # Приложение работает
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    
    # Остановка сервисов
    await rule_engine.stop()
    await mqtt_listener.stop()
    await webhook_dispatcher.close()
    await db.close()
    
    logger.info("Shutdown complete")


# Создание FastAPI приложения
app = FastAPI(
    title=settings.app_name,
    description="IoT Core Platform - Collect, Store, and React to IoT Device Telemetry",
    version="1.0.0",
    lifespan=lifespan
)

# Middleware
app.add_middleware(LoggingMiddleware)
app.add_middleware(
    RateLimitMiddleware,
    rate_limit=settings.rate_limit_per_minute
)
# Примечание: AuthMiddleware не добавляем глобально, т.к. ingestion endpoint должен быть публичным
# Вместо этого используем зависимости в эндпоинтах где нужна аутентификация

# Подключение роутеров
app.include_router(http_router)  # Ingestion endpoints
app.include_router(router)       # API endpoints

# Статические файлы для Admin UI
try:
    app.mount("/admin", StaticFiles(directory="static/admin", html=True), name="admin")
except RuntimeError:
    logger.warning("Static files directory not found, admin UI will not be available")


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint для мониторинга"""
    try:
        # Проверяем подключение к БД
        async with db.get_session() as session:
            await session.execute(text("SELECT 1"))
        
        return {
            "status": "healthy",
            "service": settings.app_name,
            "version": "1.0.0",
            "database": "connected",
            "mqtt": "running" if mqtt_listener.running else "stopped",
            "rule_engine": "running" if rule_engine.running else "stopped"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": settings.app_name,
                "error": str(e)
            }
        )


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint с информацией о системе"""
    return {
        "service": settings.app_name,
        "version": "1.0.0",
        "description": "IoT Core Platform",
        "endpoints": {
            "health": "/health",
            "api_docs": "/docs",
            "admin_panel": "/admin",
            "api": "/api/v1"
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
