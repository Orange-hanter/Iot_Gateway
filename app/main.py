"""
IoT-Core MVP - Главный модуль приложения
"""
import asyncio
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.config import settings
from app.database import db
from app.modules.api import LoggingMiddleware, RateLimitMiddleware, router
from app.modules.engine import rule_engine, webhook_dispatcher
from app.modules.ingestion import http_router, mqtt_listener

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
    ]
)

logger = logging.getLogger(__name__)

# Флаги готовности сервисов
class ServiceStatus:
    mqtt_ready = False
    rule_engine_ready = False
    db_ready = False


async def _retry_async_operation(
    operation,
    name: str,
    max_retries: int = 5,
    initial_delay: float = 2.0
) -> bool:
    """
    Повторная попытка асинхронной операции с экспоненциальной задержкой.

    Args:
        operation: async callable
        name: Имя операции для логирования
        max_retries: Максимальное количество попыток
        initial_delay: Начальная задержка в секундах

    Returns:
        True если успех, False если все попытки исчерпаны
    """
    for attempt in range(max_retries):
        try:
            logger.info(f"[{name}] Attempt {attempt + 1}/{max_retries}...")
            await operation()
            logger.info(f"[{name}] ✓ Success")
            return True
        except Exception as e:
            logger.warning(f"[{name}] Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                delay = initial_delay * (2 ** attempt)  # Экспоненциальная задержка
                logger.info(f"[{name}] Retrying in {delay:.1f}s...")
                await asyncio.sleep(delay)
            else:
                logger.error(f"[{name}] ✗ Failed after {max_retries} attempts")
    return False


async def _watchdog_task():
    """
    Фоновый watchdog для восстановления упавших сервисов.
    """
    logger.info("Service watchdog started")

    while True:
        try:
            await asyncio.sleep(30)  # Проверяем каждые 30 сек

            # Проверяем MQTT
            if not mqtt_listener.running:
                logger.warning("MQTT listener is down, attempting recovery...")
                try:
                    await mqtt_listener.start()
                    ServiceStatus.mqtt_ready = True
                    logger.info("MQTT listener recovered")
                except Exception as e:
                    logger.error(f"Failed to recover MQTT: {e}")
                    ServiceStatus.mqtt_ready = False

            # Проверяем Rule Engine
            if not rule_engine.running:
                logger.warning("Rule Engine is down, attempting recovery...")
                try:
                    await rule_engine.start()
                    ServiceStatus.rule_engine_ready = True
                    logger.info("Rule Engine recovered")
                except Exception as e:
                    logger.error(f"Failed to recover Rule Engine: {e}")
                    ServiceStatus.rule_engine_ready = False

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Watchdog error: {e}", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifecycle events для FastAPI.
    Управление запуском и остановкой фоновых сервисов с retry-логикой.
    """
    watchdog_task = None

    logger.info(f"Starting {settings.app_name}...")

    # Инициализация БД (критична, fail-fast)
    try:
        logger.info("Initializing database...")
        await db.initialize()
        ServiceStatus.db_ready = True
        logger.info("✓ Database initialized")
    except Exception as e:
        logger.error(f"✗ Failed to initialize database: {e}", exc_info=True)
        raise

    # MQTT Listener (важна, но не критична для HTTP ingestion)
    if not await _retry_async_operation(
        mqtt_listener.start,
        name="MQTT Listener",
        max_retries=3,
        initial_delay=1.0
    ):
        logger.warning("⚠️  MQTT Listener failed to start (HTTP ingestion still available)")
        ServiceStatus.mqtt_ready = False
    else:
        ServiceStatus.mqtt_ready = True

    # Rule Engine (важна, но не критична для ingestion)
    if not await _retry_async_operation(
        rule_engine.start,
        name="Rule Engine",
        max_retries=3,
        initial_delay=1.0
    ):
        logger.warning("⚠️  Rule Engine failed to start (triggers will not fire)")
        ServiceStatus.rule_engine_ready = False
    else:
        ServiceStatus.rule_engine_ready = True

    # Запускаем фоновый watchdog для восстановления
    watchdog_task = asyncio.create_task(_watchdog_task())

    logger.info(f"✓ {settings.app_name} started successfully")

    # Приложение работает
    yield

    # Shutdown
    logger.info("Shutting down...")

    # Остановка watchdog
    if watchdog_task:
        watchdog_task.cancel()
        try:
            await watchdog_task
        except asyncio.CancelledError:
            pass

    # Остановка сервисов
    await rule_engine.stop()
    await mqtt_listener.stop()
    await webhook_dispatcher.close()
    await db.close()

    logger.info("✓ Shutdown complete")



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
    """
    Health check endpoint для мониторинга.
    Возвращает 503 если критичные компоненты недоступны.
    """
    status_code = 200

    try:
        # Проверяем подключение к БД
        async with db.get_session() as session:
            await session.execute(text("SELECT 1"))

        db_status = "connected"
    except Exception as e:
        logger.error(f"Health check - DB error: {e}")
        db_status = f"disconnected: {str(e)[:50]}"
        status_code = 503

    mqtt_status = "running" if mqtt_listener.running else "stopped"
    if not mqtt_listener.running:
        status_code = 503

    rule_engine_status = "running" if rule_engine.running else "stopped"
    if not rule_engine.running:
        status_code = 503

    response = {
        "status": "healthy" if status_code == 200 else "degraded",
        "service": settings.app_name,
        "version": "1.0.0",
        "database": db_status,
        "mqtt": mqtt_status,
        "rule_engine": rule_engine_status,
        "services_ready": {
            "db": ServiceStatus.db_ready,
            "mqtt": ServiceStatus.mqtt_ready,
            "rule_engine": ServiceStatus.rule_engine_ready
        }
    }

    if status_code != 200:
        response["message"] = "One or more critical services are down"

    return JSONResponse(status_code=status_code, content=response)


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
