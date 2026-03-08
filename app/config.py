"""
Конфигурация приложения
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Настройки приложения из переменных окружения"""
    
    # Application
    app_name: str = "IoT-Core"
    app_env: str = "development"
    debug: bool = False
    log_level: str = "INFO"
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Database
    database_path: str = "./data/iot_core.db"
    database_wal_mode: bool = True
    telemetry_ttl_days: int = 30
    
    # MQTT
    mqtt_broker_host: str = "mqtt-broker"
    mqtt_broker_port: int = 1883
    mqtt_client_id: str = "iot-core-server"
    mqtt_topic_pattern: str = "iot/+/data"
    mqtt_qos: int = 1
    
    # Security
    api_key: str = "change-this-api-key"
    admin_username: str = "admin"
    admin_password: str = "change-this-password"
    webhook_secret: str = "webhook-secret"
    
    # Rate Limiting
    rate_limit_per_minute: int = 60
    max_payload_size_kb: int = 64
    
    # Webhook
    webhook_timeout_seconds: int = 10
    webhook_max_retries: int = 3
    webhook_retry_delay_seconds: int = 2
    
    # Rule Engine
    rule_engine_poll_interval_seconds: int = 5
    trigger_cooldown_seconds: int = 60
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Глобальный экземпляр настроек
settings = Settings()
