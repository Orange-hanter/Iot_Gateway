#!/bin/bash
# Скрипт для пересборки Docker контейнера с новым драйвером

set -e

echo "🔄 Rebuilding Docker containers with Arduino MQ2 driver support..."

# Цвета для вывода
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Шаг 1: Остановка контейнеров
echo -e "${BLUE}Step 1: Stopping containers...${NC}"
docker-compose down

# Шаг 2: Пересборка
echo -e "${BLUE}Step 2: Building containers (this may take a few minutes)...${NC}"
docker-compose build --no-cache iot-core

# Шаг 3: Запуск
echo -e "${BLUE}Step 3: Starting containers...${NC}"
docker-compose up -d

# Шаг 4: Ожидание готовности
echo -e "${BLUE}Step 4: Waiting for service to be ready...${NC}"
sleep 5

# Шаг 5: Проверка здоровья
echo -e "${BLUE}Step 5: Health check...${NC}"
if curl -f -s http://localhost:8000/health > /dev/null; then
    echo -e "${GREEN}✓ Service is healthy${NC}"
else
    echo -e "${YELLOW}⚠ Service might not be ready yet. Check logs:${NC}"
    echo "  docker-compose logs -f iot-core"
    exit 1
fi

# Шаг 6: Проверка драйверов
echo -e "${BLUE}Step 6: Checking available drivers...${NC}"

# Получаем API ключ из .env или используем дефолтный
API_KEY=${API_KEY:-"your-secret-api-key-change-this"}

DRIVERS=$(curl -s http://localhost:8000/api/v1/drivers \
  -H "X-API-Key: $API_KEY")

if echo "$DRIVERS" | grep -q "arduino_mq2"; then
    echo -e "${GREEN}✓ Arduino MQ2 driver is registered!${NC}"
    echo ""
    echo "Available drivers:"
    echo "$DRIVERS" | jq '.drivers | keys'
else
    echo -e "${YELLOW}⚠ Arduino MQ2 driver not found in response${NC}"
    echo "Response:"
    echo "$DRIVERS" | jq
    exit 1
fi

# Шаг 7: Проверка pyserial
echo -e "${BLUE}Step 7: Checking pyserial installation...${NC}"
if docker exec iot-core-server pip list | grep -q pyserial; then
    echo -e "${GREEN}✓ pyserial is installed${NC}"
else
    echo -e "${YELLOW}⚠ pyserial is not installed${NC}"
    exit 1
fi

# Финальный вывод
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✓ Docker rebuild completed successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Next steps:"
echo "1. Verify drivers: curl http://localhost:8000/api/v1/drivers -H 'X-API-Key: $API_KEY'"
echo "2. View logs: docker-compose logs -f iot-core"
echo "3. Create Arduino device: see docs/ARDUINO_MQ2.md"
echo ""
echo "For Arduino integration:"
echo "• Upload firmware: arduino/mq2_sensor/mq2_sensor.ino"
echo "• Run bridge: python arduino/bridge.py --device-id YOUR-DEVICE-UUID"
echo "• See docs: arduino/QUICKSTART.md"
