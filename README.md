# Kvitto — Payments API

Тестовое задание Junior Python (FastAPI): приём оплаты курса, рассрочка, вебхук банка.

Как работал с ИИ — в [`AI_LOG.md`](AI_LOG.md).

## Что есть

| Метод | Путь | Зачем |
|-------|------|--------|
| `GET` | `/tariffs` | список тарифов |
| `POST` | `/payments` | создать платёж (`Idempotency-Key` обязателен) |
| `GET` | `/payments` | список, фильтры `email` / `status` |
| `GET` | `/payments/{id}` | один платёж |
| `POST` | `/webhooks/bank` | статус от банка + HMAC (`X-Signature`) |

Коротко по правилам из ТЗ:

- суммы в **копейках** (`int`)
- промо `KVITTO10` → −10%, регистр не важен
- рассрочка: остаток копеек уходит в первые платежи (`1990000` / 3 → `[663334, 663333, 663333]`)
- повтор с тем же `Idempotency-Key` → тот же платёж, статус **200**
- запрещённый переход статуса → **409**, запись не меняется

Swagger после запуска: http://localhost:8000/docs

## Быстрый старт

```bash
cp .env.example .env
docker compose up --build
```

Поднимается Postgres и API. Миграции крутятся при старте контейнера `api`.

Проверка:

```bash
curl http://localhost:8000/tariffs
```

## Локально (без контейнера API)

Нужен Python 3.12+ и Postgres (можно только БД из compose):

```bash
docker compose up -d postgres

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

alembic upgrade head
uvicorn app.main:app --reload
```

## Тесты

Один раз создать тестовую БД:

```bash
docker exec kvitto-test-postgres-1 psql -U postgres -c "CREATE DATABASE kvitto_test;"
```

Дальше:

```bash
source .venv/bin/activate
ruff check app tests
pytest
```

## Примеры запросов

Тарифы:

```bash
curl http://localhost:8000/tariffs
```

Платёж с промо:

```bash
curl -X POST http://localhost:8000/payments \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: demo-1' \
  -d '{"tariff_id":"standard","email":"user@example.com","method":"card","promo_code":"KVITTO10"}'
```

Вебхук — подставь `id` из ответа платежа (секрет как в `.env.example`):

```bash
PAYMENT_ID="uuid-из-ответа"
BODY="{\"payment_id\":\"${PAYMENT_ID}\",\"status\":\"succeeded\"}"
SIG=$(printf '%s' "$BODY" | openssl dgst -sha256 -hmac "dev-webhook-secret" | awk '{print $2}')
curl -sS -X POST http://localhost:8000/webhooks/bank \
  -H "Content-Type: application/json" \
  -H "X-Signature: $SIG" \
  -d "$BODY"
```

## CI

На каждый push и pull request GitHub Actions (`.github/workflows/ci.yml`):

1. поднимает Postgres;
2. ставит зависимости;
3. гоняет `ruff check app tests`;
4. создаёт БД `kvitto_test`;
5. применяет миграции (`alembic upgrade head`);
6. запускает `pytest`.
