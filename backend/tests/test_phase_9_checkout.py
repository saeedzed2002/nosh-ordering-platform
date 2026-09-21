from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.session import get_engine
from app.models import MenuItem, Order, Promotion


def checkout_payload(
    seeded_client,
    *,
    idempotency_key: str,
    payment_scenario: str = "succeeds",
) -> dict[str, object]:
    item = seeded_client.get("/api/v1/catalog/menu-items/harissa-chicken-bowl").json()
    base_option_id = item["option_groups"][0]["options"][0]["id"]
    extra_option_id = item["option_groups"][1]["options"][1]["id"]
    return {
        "idempotency_key": idempotency_key,
        "location_slug": "market-quarter",
        "fulfillment_method": "delivery",
        "timing": "immediate",
        "recipient_name": "  Sam Example  ",
        "recipient_email": "  sam@example.test  ",
        "recipient_phone": " +1 555 010 0100 ",
        "delivery_address": "  1 Example Lane, Market Quarter  ",
        "fulfillment_instructions": "  Ring the bell once.  ",
        "promotion_code": "  welcome10  ",
        "payment_scenario": payment_scenario,
        "lines": [
            {
                "client_line_id": "harissa-checkout-line",
                "menu_item_slug": "harissa-chicken-bowl",
                "quantity": 2,
                "option_ids": [base_option_id, extra_option_id],
                "note": "  Sauce on the side  ",
            }
        ],
    }


def test_checkout_creates_an_immutable_receipt_from_server_prices(
    seeded_client,
    seeded_settings: Settings,
) -> None:
    payload = checkout_payload(
        seeded_client, idempotency_key="phase9-immutable-receipt-001"
    )

    response = seeded_client.post("/api/v1/orders/checkout", json=payload)

    assert response.status_code == 201
    receipt = response.json()
    assert receipt["public_reference"].startswith("N-")
    assert receipt["status"] == "submitted"
    assert "recipient_name" not in receipt
    assert "delivery_address" not in receipt
    assert receipt["promotion_code"] == "WELCOME10"
    assert receipt["subtotal_minor"] == 3050
    assert receipt["promotion_discount_minor"] == 305
    assert receipt["total_minor"] == 2745
    assert receipt["lines"] == [
        {
            "menu_item_slug": "harissa-chicken-bowl",
            "menu_item_name": "Harissa chicken bowl",
            "quantity": 2,
            "note": "Sauce on the side",
            "unit_price_minor": 1525,
            "line_total_minor": 3050,
            "currency_code": "USD",
            "selected_options": [
                {
                    "id": payload["lines"][0]["option_ids"][0],
                    "name": "Warm grains",
                    "option_group_name": "Choose a base",
                    "price_delta_minor": 0,
                },
                {
                    "id": payload["lines"][0]["option_ids"][1],
                    "name": "Extra harissa",
                    "option_group_name": "Add heat",
                    "price_delta_minor": 75,
                },
            ],
        }
    ]

    with Session(get_engine(seeded_settings.database_url)) as session:
        item = session.scalar(
            select(MenuItem).where(MenuItem.slug == "harissa-chicken-bowl")
        )
        assert item is not None
        item.base_price_minor = 999999
        session.commit()

    refreshed = seeded_client.get(f"/api/v1/orders/{receipt['public_reference']}")

    assert refreshed.status_code == 200
    assert refreshed.json()["lines"][0]["unit_price_minor"] == 1525
    assert refreshed.json()["total_minor"] == 2745


def test_checkout_replay_is_idempotent_and_counts_a_promotion_once(
    seeded_client,
    seeded_settings: Settings,
) -> None:
    payload = checkout_payload(
        seeded_client, idempotency_key="phase9-idempotent-checkout-001"
    )

    first = seeded_client.post("/api/v1/orders/checkout", json=payload)
    second = seeded_client.post("/api/v1/orders/checkout", json=payload)

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["public_reference"] == first.json()["public_reference"]
    with Session(get_engine(seeded_settings.database_url)) as session:
        assert session.query(Order).count() == 1
        promotion = session.scalar(
            select(Promotion).where(Promotion.code == "WELCOME10")
        )
        assert promotion is not None
        assert promotion.usage_count == 1


def test_checkout_mock_payment_failure_does_not_persist_an_order(
    seeded_client,
    seeded_settings: Settings,
) -> None:
    payload = checkout_payload(
        seeded_client,
        idempotency_key="phase9-declined-payment-001",
        payment_scenario="fails",
    )

    response = seeded_client.post("/api/v1/orders/checkout", json=payload)

    assert response.status_code == 402
    assert "No order or payment data was saved" in response.json()["detail"]
    with Session(get_engine(seeded_settings.database_url)) as session:
        assert session.query(Order).count() == 0
        promotion = session.scalar(
            select(Promotion).where(Promotion.code == "WELCOME10")
        )
        assert promotion is not None
        assert promotion.usage_count == 0
