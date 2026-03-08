"""
Подключение к базе данных
"""
import os
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool
from app.database.models import Base
from app.config import settings

logger = logging.getLogger(__name__)


class Database:
    """Управление подключением к базе данных"""
    
    def __init__(self):
        self.engine = None
        self.session_factory = None
    
    async def initialize(self):
        """Инициализация подключения к БД"""
        # Создаем директорию для БД если не существует
        db_dir = os.path.dirname(settings.database_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
        
        # Создаем async engine для SQLite
        database_url = f"sqlite+aiosqlite:///{settings.database_path}"
        
        self.engine = create_async_engine(
            database_url,
            echo=settings.debug,
            connect_args={
                "check_same_thread": False,
            },
            poolclass=StaticPool,  # Для SQLite
        )
        
        # Создаем фабрику сессий
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        
        # Создаем таблицы
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        # Включаем WAL mode для SQLite
        if settings.database_wal_mode:
            async with self.engine.connect() as conn:
                await conn.execute("PRAGMA journal_mode=WAL")
        
        logger.info(f"Database initialized: {settings.database_path}")
    
    async def close(self):
        """Закрытие подключения к БД"""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connection closed")
    
    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Контекстный менеджер для получения сессии БД"""
        if not self.session_factory:
            raise RuntimeError("Database not initialized")
        
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()


# Глобальный экземпляр БД
db = Database()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency для FastAPI"""
    async with db.get_session() as session:
        yield session
