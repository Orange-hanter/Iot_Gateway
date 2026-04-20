---
tags: [decisions, open, todo]
date: 2026-04-08
related:
  - "[ADR Index](index.md)"
  - "[Бизнес-требования](../business/requirements.md)"
---

# Открытые решения

> Вопросы, требующие решения до перехода к соответствующим фазам разработки.  
> Каждый раздел содержит варианты с плюсами/минусами для быстрого принятия решения.  
> Статусы: `<!-- @DECISION -->` — не начато; `🔄` — анализ готов; `✅` — принято.

---

## 🔴 Блокирующие (нет — Фаза 2)

### [ADR-005] Выбор СУБД

**Статус:** 🔄 Анализ готов → [ADR-005-database.md](ADR-005-database.md)  
**Блокирует:** Фазу 2 (Go core, ORM, миграция)

**Резюме:**
| Вариант | Плюс | Минус | Оценка |
|---------|------|-------|--------|
| **TimescaleDB** | SQL-совместим, автоматические hypertable + aggregates, лёгкая миграция | Нужно знать PostgreSQL | **9/10** |
| PostgreSQL vanilla | Универсален, SQLAlchemy без правок | Нет time-series оптимизации | 7/10 |
| InfluxDB v2 | IoT-native | Нет SQL/JOIN, лицензия v3 плохая | 4/10 |
| QuestDB | Быстрая | Молодой, ограниченный DML | 6/10 |

**Рекомендация:** TimescaleDB  
**Действие:** Подтвердить выбор, закрыть ADR-005.

---

### [ADR-008] Go: модуль организации и структура репозитория

**Статус:** <!-- @DECISION -->  
**Блокирует:** Фазу 2 (нельзя начать без структуры Go monorepo)

**Вопрос:** Как организовать Go-код? Один `go.mod` или несколько? Какая структура директорий?

| Вариант | Описание | Плюс | Минус |
|---------|----------|------|-------|
| **Monorepo, один go.mod** | Все сервисы в `cmd/gateway-core`, `cmd/rule-engine`, `cmd/api-gateway` | Просто, нет проблем с версиями | Всё в одном репозитории |
| Multi-module | Каждый сервис — отдельный `go.mod` | Независимые версии | Сложнее CI/CD |
| Отдельный репозиторий Go | Python-пилот остаётся как есть, Go в новом repo | Чистое разделение | Нужно синхронизировать 2 repo |

**Рекомендация:** Monorepo, один `go.mod`, структура:
```
/cmd/gateway-core/main.go
/cmd/rule-engine/main.go
/cmd/api-gateway/main.go
/internal/ingestion/
/internal/storage/
/internal/rules/
/proto/         ← gRPC proto files
/python/        ← adapter-runtime (subdir, отдельный pyproject.toml)
```

<!-- @DECISION: выбрать структуру репозитория до S1 -->

---

## 🟡 Важные (нет — Фаза 3)

### [ADR-009] CI/CD pipeline

**Статус:** <!-- @DECISION -->  
**Нужно до:** Фазы 3 (первый клиент → нужна автоматизация сборки)

| Вариант | Плюс | Минус |
|---------|------|-------|
| **GitHub Actions** | Бесплатно для public, простой YAML | Зависимость от GitHub |
| GitLab CI | Self-hosted, встроенный registry | Дополнительный сервис |
| Простые Makefile + scripts | Нет external dependency | Только локально |

**Рекомендация:** GitHub Actions (уже используется GitHub).  
Минимальный pipeline: `lint → test → build Docker → push → notify`.

<!-- @DECISION: утвердить GitHub Actions как CI/CD -->

---

### [ADR-010] Стратегия backup и DRP

**Статус:** <!-- @DECISION -->  
**Нужно до:** Фазы 3 (продуктовая система у клиента)

**Сценарий:** On-premise устройство у клиента. При сбое диска — потеря данных?

| Вариант | Описание | RPO | RTO |
|---------|----------|-----|-----|
| **pg_dump по расписанию** | Cron + pg_dump каждый час → S3/local | 1 час | ~15 мин |
| WAL archiving | PostgreSQL WAL → удалённое хранилище | ~минуты | ~10 мин |
| Replication WAL | Hot standby на втором диске/хосте | ~секунды | ~1 мин |
| Без backup (MVP) | Только SQLite .bak | Последний бэкап | Ручное восстановление |

**Рекомендация:** `pg_dump` каждый час + внешний диск. При наличии второго компьютера у клиента — WAL archiving.

<!-- @DECISION: определить DRP до поставки первому клиенту -->

---

### [ADR-011] Стратегия тестирования

**Статус:** <!-- @DECISION -->  
**Нужно до:** Фазы 2 (старт написания Go-кода)

| Уровень | Инструмент | Статус |
|---------|-----------|--------|
| Unit (Go) | `testing` + `testify/mock` | <!-- @TODO: настроить в S1 --> |
| Unit (Python) | `pytest` | ✅ Частично есть в пилоте |
| Integration (Go+DB) | `testcontainers-go` с TimescaleDB | <!-- @TODO --> |
| API integration | `httptest` (Go) или `pytest` + `httpx` | <!-- @TODO --> |
| Hardware-in-Loop (HIL) | Ручное + Arduino simulator | <!-- @TODO: определить подход --> |
| Load testing | `k6` или `vegeta` | <!-- @TODO: S7 --> |

**Рекомендация:** Unit + integration automation с первого спринта; HIL — ручной протокол для первого клиента; load test — перед релизом.

<!-- @DECISION: утвердить стратегию тестирования -->

---

## 🟢 Отложенные (Фаза 4+)

### [ADR-012] Аутентификация и IAM

**Статус:** <!-- @DECISION -->  
**Нужно до:** Фазы 4 (Dashboard Platform с внешними пользователями)

| Вариант | Описание | Плюс | Минус |
|---------|----------|------|-------|
| **JWT (собственный)** | Go: `golang-jwt/jwt` | Нет external dependency | Нужно управлять ключами |
| API Keys | `X-API-Key` header | Просто | Нет expiry, ротации сложнее |
| OAuth2 + Keycloak | External identity provider | Enterprise-ready | Дополнительный сервис, overengineering для MVP |
| mTLS | Сертификаты на устройствах | Максимальная безопасность | Сложная операционная модель |

**Рекомендация:**
- Dashboard users: JWT (HS256 или RS256) с refresh tokens
- Устройства → gateway: API Key (хранится в БД, хэш bcrypt)
- Будущее (enterprise): mTLS для устройств

<!-- @DECISION: выбрать auth модель перед Фазой 4 -->

---

### [ADR-013] Версионирование конфигурации устройств

**Статус:** <!-- @DECISION -->  
**Нужно до:** Фазы 5 (профили устройств, rollback к предыдущей версии)

| Вариант | Описание | Плюс | Минус |
|---------|----------|------|-------|
| **Git-native** | Конфиги как YAML-файлы в repo | Версионирование бесплатно | Нужен git client на устройстве |
| DB-versioned | Таблица `device_config_versions` | Всё в одном месте | Ручной rollback |
| Node-RED built-in | История потоков в Node-RED storage | Уже есть | Только для Node-RED конфигов |

**Рекомендация:** DB-versioned + экспорт в YAML по запросу.

<!-- @DECISION: определить до реализации профилей устройств -->

---

### [ADR-014] Интеграция с MES/ERP (будущее)

**Статус:** Отложено  
**Нужно до:** Когда появится первый запрос от клиента

Текущее решение: **Наша dashboard platform** является потребителем данных. MES интеграция — будущий проект.

Возможные протоколы: REST webhooks (уже есть), OPC UA (для промышленных систем), MQTT federation.

<!-- @TODO: создать отдельный документ при появлении запроса от клиента -->

---

## Журнал принятых решений (справка)

| ADR | Дата | Решение |
|-----|------|---------|
| ADR-001 | 2025 | SQLite для MVP |
| ADR-002 | 2025 | FastAPI для MVP |
| ADR-003 | 2025 | Mosquitto брокер |
| ADR-004 | 2026 | Модульный монолит для MVP |
| ADR-006 | 2026-04-08 | Runtime-плагины через Python adapter-runtime |
| ADR-007 | 2026-04-08 | Node-RED для device configuration |
| ADR-008 | 2026-04-08 | Go для продуктового ядра |

---
**См. также:** [ADR Index](index.md) | [ADR-005 Database](ADR-005-database.md) | [Polyglot архитектура](../architecture/polyglot.md) | [← Навигация](../index.md)
