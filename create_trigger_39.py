#!/usr/bin/env python3
"""
Скрипт для создания триггера с ID 39
"""
import sqlite3
import json
from datetime import datetime

def main():
    conn = sqlite3.connect('/app/data/iot_core.db')
    cursor = conn.cursor()
    
    # Проверяем, существует ли триггер с ID 39
    cursor.execute('SELECT id FROM triggers WHERE id = 39')
    existing = cursor.fetchone()
    
    if existing:
        print('❌ Триггер с ID 39 уже существует')
        conn.close()
        return
    
    # Создаем триггер с ID 39
    firebase_config = {
        'url': 'https://back.processnavigation.com/ci2e4kezb7/firebase-notifications/push-message',
        'title': 'Тестовое уведомление от IoT Gateway',
        'text': 'Сработал триггер {trigger_name}: {metric_name} = {value}',
        'ids': [4, 5, 1]
    }
    
    cursor.execute('''
        INSERT INTO triggers (
            id, name, device_id, metric_name, condition, 
            webhook_url, firebase_notification, cooldown_sec, 
            is_active, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        39,
        'Тестовый триггер Firebase',
        None,  # Для всех устройств
        'test_metric',
        '> 0',
        '',  # Пустой webhook_url
        json.dumps(firebase_config),
        60,
        1,  # is_active = True
        datetime.now().isoformat(),
        datetime.now().isoformat()
    ))
    
    conn.commit()
    print('✅ Триггер с ID 39 успешно создан')
    
    # Проверяем созданный триггер
    cursor.execute('SELECT id, name, metric_name, condition, firebase_notification FROM triggers WHERE id = 39')
    trigger = cursor.fetchone()
    print(f'\n📋 Триггер создан:')
    print(f'  ID: {trigger[0]}')
    print(f'  Name: {trigger[1]}')
    print(f'  Metric: {trigger[2]}')
    print(f'  Condition: {trigger[3]}')
    print(f'  Firebase config: {trigger[4][:80]}...')
    
    conn.close()

if __name__ == '__main__':
    main()
