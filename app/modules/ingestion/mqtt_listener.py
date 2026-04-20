"""
MQTT Listener для приема данных от устройств
"""
import logging
import json
import asyncio
from datetime import datetime
from typing import Optional
import paho.mqtt.client as mqtt
from app.config import settings
from app.database import db
from app.drivers import get_driver
from app.modules.storage import StorageService

logger = logging.getLogger(__name__)


class MQTTListener:
    """MQTT клиент для приема данных от устройств"""
    
    def __init__(self):
        self.client: Optional[mqtt.Client] = None
        self.running = False
        self.loop: Optional[asyncio.AbstractEventLoop] = None
    
    def on_connect(self, client, userdata, flags, rc):  # pylint: disable=unused-argument
        """Callback при подключении к MQTT брокеру"""
        if rc == 0:
            logger.info("Connected to MQTT broker")
            # Подписка на топик iot/+/data
            topic = settings.mqtt_topic_pattern
            client.subscribe(topic, qos=settings.mqtt_qos)
            logger.info(f"Subscribed to topic: {topic}")
        else:
            logger.error(f"Failed to connect to MQTT broker: {rc}")
    
    def on_disconnect(self, client, userdata, rc):  # pylint: disable=unused-argument
        """Callback при отключении от MQTT брокера"""
        if rc != 0:
            logger.warning(f"Unexpected MQTT disconnect: {rc}")
    
    def on_message(self, client, userdata, msg):  # pylint: disable=unused-argument
        """Callback при получении сообщения"""
        try:
            # Извлекаем device_id из топика: iot/{device_id}/data
            topic_parts = msg.topic.split('/')
            if len(topic_parts) != 3:
                logger.warning(f"Invalid topic format: {msg.topic}")
                return
            
            device_id = topic_parts[1]
            
            # Парсим JSON payload
            try:
                payload = json.loads(msg.payload.decode('utf-8'))
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON from device {device_id}: {e}")
                return
            
            # Добавляем device_id в payload если его нет
            if "device_id" not in payload:
                payload["device_id"] = device_id
            
            # Добавляем timestamp если его нет
            if "timestamp" not in payload:
                payload["timestamp"] = datetime.utcnow().isoformat()
            
            # Обрабатываем асинхронно через основной event loop
            if self.loop and self.loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self.process_message(device_id, payload),
                    self.loop
                )
            else:
                logger.error("Event loop not available for MQTT message processing")
        
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}", exc_info=True)
    
    async def process_message(self, device_id: str, payload: dict):
        """
        Асинхронная обработка MQTT сообщения.
        
        Args:
            device_id: ID устройства
            payload: Данные от устройства
        """
        try:
            async with db.get_session() as session:
                from sqlalchemy import select
                from app.database.models import Device
                
                # Получаем устройство
                query = select(Device).where(Device.id == device_id)
                result = await session.execute(query)
                device = result.scalar_one_or_none()
                
                if not device:
                    logger.warning(f"Device {device_id} not found")
                    return
                
                if device.status != "active":
                    logger.warning(f"Device {device_id} is not active")
                    return
                
                # Получаем драйвер
                driver = get_driver(device.driver_type)
                if not driver:
                    logger.error(f"Driver {device.driver_type} not found")
                    return
                
                # Валидация и парсинг
                if not driver.validate(payload):
                    logger.error(f"Invalid payload from device {device_id}")
                    return
                
                metrics = driver.parse(payload)
                if not metrics:
                    logger.warning(f"No valid metrics from device {device_id}")
                    return
                
                # Парсим timestamp
                timestamp_str = payload.get("timestamp")
                if isinstance(timestamp_str, str):
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                else:
                    timestamp = datetime.utcnow()
                
                # Подготовка записей
                telemetry_records = []
                for metric in metrics:
                    telemetry_records.append({
                        "device_id": device_id,
                        "timestamp": timestamp,
                        "metric_name": metric["name"],
                        "value": metric["value"],
                        "unit": metric.get("unit")
                    })
                
                # Сохранение
                storage = StorageService(session)
                count = await storage.save_telemetry_batch(telemetry_records)
                
                # Обновление last_seen
                await storage.update_device_last_seen(device_id)
                
                # Добавление в очередь
                await storage.add_to_internal_queue("telemetry", {
                    "device_id": device_id,
                    "timestamp": timestamp.isoformat(),
                    "metrics": metrics
                })
                
                logger.info(f"MQTT: Ingested {count} metrics from device {device_id}")
        
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}", exc_info=True)
    
    async def start(self):
        """Запуск MQTT клиента"""
        if self.running:
            logger.warning("MQTT listener already running")
            return
        
        try:
            # Сохраняем ссылку на текущий event loop
            self.loop = asyncio.get_running_loop()
            
            self.client = mqtt.Client(client_id=settings.mqtt_client_id)
            self.client.on_connect = self.on_connect
            self.client.on_disconnect = self.on_disconnect
            self.client.on_message = self.on_message
            
            # Устанавливаем аутентификацию
            self.client.username_pw_set(
                settings.mqtt_username,
                settings.mqtt_password
            )
            
            logger.info(f"Connecting to MQTT broker at {settings.mqtt_broker_host}:{settings.mqtt_broker_port}")
            self.client.connect(
                settings.mqtt_broker_host,
                settings.mqtt_broker_port,
                keepalive=60
            )
            
            # Запуск loop в отдельном потоке
            self.client.loop_start()
            self.running = True
            
            logger.info("MQTT listener started")
        
        except Exception as e:
            logger.error(f"Failed to start MQTT listener: {e}", exc_info=True)
            raise
    
    async def stop(self):
        """Остановка MQTT клиента"""
        if not self.running:
            return
        
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
        
        self.running = False
        logger.info("MQTT listener stopped")


# Глобальный экземпляр MQTT listener
mqtt_listener = MQTTListener()
