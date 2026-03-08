#!/bin/bash

# Скрипт быстрого запуска IoT-Core платформы

set -e

echo "🚀 IoT-Core Quick Start"
echo "======================"
echo ""

# Проверка Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker не установлен. Установите Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose не установлен."
    exit 1
fi

echo "✅ Docker и Docker Compose найдены"
echo ""

# Создание .env если не существует
if [ ! -f .env ]; then
    echo "📝 Создание .env файла..."
    cp .env.example .env
    echo "✅ .env файл создан"
    echo "⚠️  ВАЖНО: Измените API_KEY в .env файле перед продакшен использованием!"
    echo ""
fi

# Создание необходимых директорий
echo "📁 Создание директорий..."
mkdir -p data logs mosquitto/data mosquitto/log
echo "✅ Директории созданы"
echo ""

# Сборка и запуск
echo "🏗️  Сборка Docker образов..."
docker-compose build

echo ""
echo "🚀 Запуск сервисов..."
docker-compose up -d

echo ""
echo "⏳ Ожидание готовности сервисов..."
sleep 5

# Проверка health
echo ""
echo "🏥 Проверка состояния..."
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ Сервисы запущены успешно!"
else
    echo "⚠️  Сервисы запускаются, это может занять некоторое время"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✨ IoT-Core платформа готова!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📍 Доступные сервисы:"
echo "   • API:         http://localhost:8000"
echo "   • Admin Panel: http://localhost:8000/admin"
echo "   • API Docs:    http://localhost:8000/docs"
echo "   • Health:      http://localhost:8000/health"
echo "   • MQTT Broker: mqtt://localhost:1883"
echo ""
echo "🔑 API Key (из .env): your-secret-api-key-change-this"
echo ""
echo "📚 Полезные команды:"
echo "   • Логи:          docker-compose logs -f"
echo "   • Остановка:     docker-compose down"
echo "   • Перезапуск:    docker-compose restart"
echo ""
echo "📖 Документация:"
echo "   • API:           docs/API.md"
echo "   • Development:   docs/DEVELOPMENT.md"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
