import hashlib
import hmac
import json
from uuid import uuid4

from app.db.config import WEBHOOK_SECRET

STANDARD_PRICE = 1_990_000


def post_webhook(client, payload: dict, signature: str | None = "auto"):
    """POST /webhooks/bank с подписью тела (как требует бонус)."""
    raw = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json"}
    if signature == "auto":
        headers["X-Signature"] = hmac.new(
            WEBHOOK_SECRET.encode(),
            raw,
            hashlib.sha256,
        ).hexdigest()
    elif signature is not None:
        headers["X-Signature"] = signature
    return client.post("/webhooks/bank", content=raw, headers=headers)


def test_amount_with_and_without_promo(client):
    without = client.post(
        "/payments",
        json={
            "tariff_id": "standard",
            "email": "a@example.com",
            "method": "card",
        },
    )
    assert without.status_code == 201
    body = without.json()
    assert body["amount"] == STANDARD_PRICE
    assert body["discount"] == 0

    with_promo = client.post(
        "/payments",
        json={
            "tariff_id": "standard",
            "email": "b@example.com",
            "method": "card",
            "promo_code": "kvitto10",
        },
    )
    assert with_promo.status_code == 201
    promo_body = with_promo.json()
    assert promo_body["discount"] == STANDARD_PRICE * 10 // 100
    assert promo_body["amount"] == STANDARD_PRICE - promo_body["discount"]


def test_installment_schedule_sums_to_amount(client):
    for months in (3, 6, 12):
        response = client.post(
            "/payments",
            json={
                "tariff_id": "standard",
                "email": f"inst{months}@example.com",
                "method": "installment",
                "installment_months": months,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["amount"] == STANDARD_PRICE
        assert data["schedule"] is not None
        assert len(data["schedule"]) == months
        assert sum(data["schedule"]) == data["amount"]


def test_idempotency_key_returns_same_payment(client):
    payload = {
        "tariff_id": "basic",
        "email": "idem@example.com",
        "method": "sbp",
    }
    headers = {"Idempotency-Key": "same-key-1"}

    first = client.post("/payments", json=payload, headers=headers)
    second = client.post("/payments", json=payload, headers=headers)

    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]

    listed = client.get("/payments", params={"email": "idem@example.com"})
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_invalid_status_transition_returns_409(client):
    created = client.post(
        "/payments",
        json={
            "tariff_id": "basic",
            "email": "wh@example.com",
            "method": "card",
        },
    )
    assert created.status_code == 201
    payment_id = created.json()["id"]
    assert created.json()["status"] == "pending"

    bad = post_webhook(client, {"payment_id": payment_id, "status": "refunded"})
    assert bad.status_code == 409
    assert bad.json() == {"error": "invalid_transition"}

    current = client.get(f"/payments/{payment_id}")
    assert current.status_code == 200
    assert current.json()["status"] == "pending"


def test_get_missing_payment_returns_404(client):
    response = client.get(f"/payments/{uuid4()}")
    assert response.status_code == 404


def test_unknown_promo_returns_422(client):
    response = client.post(
        "/payments",
        json={
            "tariff_id": "standard",
            "email": "x@example.com",
            "method": "card",
            "promo_code": "NOTREAL",
        },
    )
    assert response.status_code == 422


def test_uppercase_promo_works(client):
    response = client.post(
        "/payments",
        json={
            "tariff_id": "standard",
            "email": "up@example.com",
            "method": "card",
            "promo_code": "KVITTO10",
        },
    )
    assert response.status_code == 201
    assert response.json()["discount"] == 199_000
    assert response.json()["amount"] == 1_791_000


def test_installment_requires_months(client):
    response = client.post(
        "/payments",
        json={
            "tariff_id": "standard",
            "email": "m@example.com",
            "method": "installment",
        },
    )
    assert response.status_code == 422


def test_card_rejects_installment_months(client):
    response = client.post(
        "/payments",
        json={
            "tariff_id": "standard",
            "email": "c@example.com",
            "method": "card",
            "installment_months": 3,
        },
    )
    assert response.status_code == 422


def test_unknown_tariff_returns_404(client):
    response = client.post(
        "/payments",
        json={
            "tariff_id": "nope",
            "email": "t@example.com",
            "method": "card",
        },
    )
    assert response.status_code == 404


def test_list_tariffs(client):
    response = client.get("/tariffs")
    assert response.status_code == 200
    data = response.json()
    assert {t["id"] for t in data} == {"basic", "standard", "premium"}
    assert all(isinstance(t["price"], int) for t in data)


def test_get_payment_returns_created(client):
    created = client.post(
        "/payments",
        json={
            "tariff_id": "premium",
            "email": "get@example.com",
            "method": "card",
        },
    )
    payment_id = created.json()["id"]
    response = client.get(f"/payments/{payment_id}")
    assert response.status_code == 200
    assert response.json()["id"] == payment_id
    assert response.json()["email"] == "get@example.com"


def test_webhook_success_then_refund(client):
    created = client.post(
        "/payments",
        json={
            "tariff_id": "basic",
            "email": "ok@example.com",
            "method": "card",
        },
    )
    payment_id = created.json()["id"]

    ok = post_webhook(client, {"payment_id": payment_id, "status": "succeeded"})
    assert ok.status_code == 200
    assert ok.json() == {"result": "ok"}
    assert client.get(f"/payments/{payment_id}").json()["status"] == "succeeded"

    refund = post_webhook(client, {"payment_id": payment_id, "status": "refunded"})
    assert refund.status_code == 200
    assert client.get(f"/payments/{payment_id}").json()["status"] == "refunded"


def test_webhook_missing_payment_404(client):
    response = post_webhook(
        client, {"payment_id": str(uuid4()), "status": "succeeded"}
    )
    assert response.status_code == 404


def test_webhook_invalid_signature_401(client):
    created = client.post(
        "/payments",
        json={
            "tariff_id": "basic",
            "email": "sig@example.com",
            "method": "card",
        },
    )
    payment_id = created.json()["id"]

    bad = post_webhook(
        client,
        {"payment_id": payment_id, "status": "succeeded"},
        signature="deadbeef",
    )
    assert bad.status_code == 401

    missing = post_webhook(
        client,
        {"payment_id": payment_id, "status": "succeeded"},
        signature=None,
    )
    assert missing.status_code == 401


def test_list_payments_filter_by_status(client):
    client.post(
        "/payments",
        json={
            "tariff_id": "basic",
            "email": "f1@example.com",
            "method": "card",
        },
    )
    paid = client.post(
        "/payments",
        json={
            "tariff_id": "basic",
            "email": "f2@example.com",
            "method": "card",
        },
    ).json()
    post_webhook(client, {"payment_id": paid["id"], "status": "succeeded"})

    pending = client.get("/payments", params={"status": "pending"})
    succeeded = client.get("/payments", params={"status": "succeeded"})
    assert pending.status_code == 200
    assert succeeded.status_code == 200
    assert all(p["status"] == "pending" for p in pending.json())
    assert all(p["status"] == "succeeded" for p in succeeded.json())
    assert len(succeeded.json()) == 1


def test_schedule_matches_tz_example(client):
    """standard без промо, 3 месяца → [663334, 663333, 663333]."""
    response = client.post(
        "/payments",
        json={
            "tariff_id": "standard",
            "email": "ex@example.com",
            "method": "installment",
            "installment_months": 3,
        },
    )
    assert response.status_code == 201
    assert response.json()["schedule"] == [663334, 663333, 663333]


def test_webhook_invalid_body_returns_422(client):
    created = client.post(
        "/payments",
        json={
            "tariff_id": "basic",
            "email": "badbody@example.com",
            "method": "card",
        },
    )
    payment_id = created.json()["id"]
    # невалидный status
    response = post_webhook(
        client,
        {"payment_id": payment_id, "status": "not_a_status"},
    )
    assert response.status_code == 422
