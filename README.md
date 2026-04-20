# Gateway

Edge-платформа сбора телеметрии с IoT-устройств для MES/IIoT: приём данных, нормализация, хранение, правила и webhook-интеграции.

## Статус

| Версия | Язык | Состояние |
|--------|------|-----------|
| **v0** | Python (FastAPI, SQLite, MQTT) | Пилот/демо завершён 2026-04-20. Заморожен. Доступен в ветке [`legacy/python-demo`](../../tree/legacy/python-demo) и теге `v0.1-demo`. |
| **v2** | Go | Greenfield-переработка. На текущей ветке ведётся планирование: бизнес-требования, архитектура, бэклог. Кода пока нет. |

Эта ветка (`main`) — рабочее пространство v2. Исходники, конфигурация и документация v0 в `main` больше не поддерживаются.

## Навигация

- [docs/index.md](docs/index.md) — хаб документации
- [docs/business/requirements.md](docs/business/requirements.md) — бизнес-требования (точка входа для владельца)
- [docs/architecture/overview.md](docs/architecture/overview.md) — общая архитектура
- [docs/backlog/user_stories.md](docs/backlog/user_stories.md) — бэклог user stories
- [docs/decisions/](docs/decisions/) — ADR

## Доступ к архиву v0

```bash
git checkout v0.1-demo        # тег-снимок пилота
git checkout legacy/python-demo  # ветка с тем же содержимым
```

## Лицензия

Proprietary
