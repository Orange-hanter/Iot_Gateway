"""
Webhook Receiver - сервис для приема и отображения вебхуков от IoT-Core
"""
from fastapi import FastAPI, Request
from datetime import datetime
import uvicorn

app = FastAPI(title="Webhook Receiver")


@app.post("/webhook")
async def receive_webhook(request: Request):
    """Принимает webhook и выводит в консоль"""
    body = await request.json()
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    print("=" * 80)
    print(f"🔔 ТРИГГЕР СРАБОТАЛ! [{timestamp}]")
    print("=" * 80)
    print(f"📊 Триггер: {body.get('trigger_name', 'N/A')}")
    print(f"🆔 Device ID: {body.get('device_id', 'N/A')}")
    print(f"📈 Метрика: {body.get('metric', 'N/A')} = {body.get('value', 'N/A')}")
    print(f"⚙️  Условие: {body.get('condition', 'N/A')}")
    print(f"💬 Сообщение: {body.get('message', 'N/A')}")
    print(f"⏰ Timestamp: {body.get('timestamp', 'N/A')}")
    print("=" * 80)
    print()
    
    return {"status": "received", "timestamp": timestamp}


@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy"}


if __name__ == "__main__":
    print("🚀 Webhook Receiver запущен на порту 8001")
    print("📡 Ожидание вебхуков на http://0.0.0.0:8001/webhook")
    print()
    uvicorn.run(app, host="0.0.0.0", port=8001)
