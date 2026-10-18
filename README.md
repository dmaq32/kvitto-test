# Kvitto Payments API

API приёма оплаты курса (тестовое задание Junior Python / FastAPI).

## Запуск (Docker)

```bash
cp .env.example .env   # поправь пароль при необходимости
docker compose up --build
```

- API: http://localhost:8000  
- Docs: http://localhost:8000/docs  

Миграции применяются при старте контейнера `api`.

## Локальный запуск

```bash
docker compose up -d postgres

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

alembic upgrade head
uvicorn app.main:app --reload
```

Для тестов один раз создай БД `kvitto_test`:

```bash
docker exec -it kvitto-test-postgres-1 psql -U postgres -c "CREATE DATABASE kvitto_test;"
```

## Тесты и линтер

```bash
source .venv/bin/activate
ruff check app tests
pytest
```

CI (GitHub Actions) гоняет `ruff` и `pytest` на каждый push/PR.

## Примеры

```bash
# тарифы
curl http://localhost:8000/tariffs

# платёж
curl -X POST http://localhost:8000/payments \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: demo-1' \
  -d '{"tariff_id":"standard","email":"user@example.com","method":"card","promo_code":"KVITTO10"}'

# вебхук (X-Signature = HMAC-SHA256 тела с WEBHOOK_SECRET)
BODY='{"payment_id":"<uuid>","status":"succeeded"}'
SIG=$(printf '%s' "$BODY" | openssl dgst -sha256 -hmac "$WEBHOOK_SECRET" | awk '{print $2}')
curl -X POST http://localhost:8000/webhooks/bank \
  -H 'Content-Type: application/json' \
  -H "X-Signature: $SIG" \
  -d "$BODY"
```
