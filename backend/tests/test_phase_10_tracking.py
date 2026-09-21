from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.session import get_engine
from app.models import Order, OrderStatusEvent


def staff_headers(seeded_client, email: str = "kitchen@nosh.example") -> dict[str, str]:
    signed_in = seeded_client.post(
        "/api/v1/auth/admin/sign-in",
        json={"email": email, "password": "test-admin-password"},
    )
    assert signed_in.status_code == 200
    return {"Authorization": f"Bearer {signed_in.json()['access_token']}"}


def create_order(seeded_client, *, method: str = "delivery") -> dict[str, object]:
    item = seeded_client.get("/api/v1/catalog/menu-items/harissa-chicken-bowl").json()
    response = seeded_client.post(
        "/api/v1/orders/checkout",
        json={
            "idempotency_key": f"phase10-tracking-{method}-001",
            "location_slug": "market-quarter",
            "fulfillment_method": method,
            "timing": "immediate",
            "scheduled_for": None,
            "recipient_name": "Sam Example",
            "recipient_email": "sam@example.test",
            "recipient_phone": "+1 555 010 0100",
            "delivery_address": "1 Example Lane" if method == "delivery" else None,
            "fulfillment_instructions": "Leave at the kitchen counter.",
            "promotion_code": None,
            "payment_scenario": "succeeds",
            "lines": [
                {
                    "client_line_id": f"phase10-{method}-line",
                    "menu_item_slug": "harissa-chicken-bowl",
                    "quantity": 1,
                    "option_ids": [item["option_groups"][0]["options"][0]["id"]],
                    "note": None,
                }
            ],
        },
    )
    assert response.status_code == 201
    return response.json()


def transition(
    seeded_client, reference: str, headers: dict[str, str], status: str
) -> dict[str, object]:
    response = seeded_client.post(
        f"/api/v1/admin/orders/{reference}/transitions",
        headers=headers,
        json={"status": status},
    )
    assert response.status_code == 200
    return response.json()


def test_delivery_status_transitions_are_staff_only_and_visible_to_the_tracker(
    seeded_client,
    seeded_settings: Settings,
) -> None:
    receipt = create_order(seeded_client)
    reference = str(receipt["public_reference"])

    unauthenticated = seeded_client.post(
        f"/api/v1/admin/orders/{reference}/transitions",
        json={"status": "accepted"},
    )
    assert unauthenticated.status_code == 401

    invalid_jump = seeded_client.post(
        f"/api/v1/admin/orders/{reference}/transitions",
        headers=staff_headers(seeded_client),
        json={"status": "delivered"},
    )
    assert invalid_jump.status_code == 409

    headers = staff_headers(seeded_client)
    latest = receipt
    for status in (
        "accepted",
        "preparing",
        "ready_for_courier",
        "handed_to_courier",
        "out_for_delivery",
        "delivered",
    ):
        latest = transition(seeded_client, reference, headers, status)

    assert latest["status"] == "delivered"
    assert latest["contact_phone"] == "+1 (555) 010-0195"
    assert latest["estimated_fulfillment_at"] is not None
    assert [event["status"] for event in latest["status_events"]] == [
        "submitted",
        "accepted",
        "preparing",
        "ready_for_courier",
        "handed_to_courier",
        "out_for_delivery",
        "delivered",
    ]
    assert "recipient_name" not in latest
    assert "delivery_address" not in latest
    assert "fulfillment_instructions" not in latest

    with Session(get_engine(seeded_settings.database_url)) as session:
        order = session.scalar(select(Order).where(Order.public_reference == reference))
        assert order is not None
        event = session.scalar(
            select(OrderStatusEvent)
            .where(OrderStatusEvent.order_id == order.id)
            .order_by(OrderStatusEvent.created_at.desc())
        )
        assert event is not None
        assert event.actor_id is not None


def test_issue_reason_and_scheduled_release_window_are_enforced(seeded_client) -> None:
    receipt = create_order(seeded_client, method="pickup")
    reference = str(receipt["public_reference"])
    headers = staff_headers(seeded_client, "manager@nosh.example")

    missing_reason = seeded_client.post(
        f"/api/v1/admin/orders/{reference}/transitions",
        headers=headers,
        json={"status": "needs_contact"},
    )
    assert missing_reason.status_code == 422

    contact_state = seeded_client.post(
        f"/api/v1/admin/orders/{reference}/transitions",
        headers=headers,
        json={"status": "needs_contact", "reason": "fulfillment_details"},
    )
    assert contact_state.status_code == 200
    assert contact_state.json()["status_events"][-1]["note"] == (
        "The kitchen needs to confirm a fulfilment detail before continuing."
    )

    item = seeded_client.get("/api/v1/catalog/menu-items/harissa-chicken-bowl").json()
    scheduled = seeded_client.post(
        "/api/v1/orders/checkout",
        json={
            "idempotency_key": "phase10-scheduled-release-001",
            "location_slug": "market-quarter",
            "fulfillment_method": "pickup",
            "timing": "scheduled",
            "scheduled_for": (datetime.now(UTC) + timedelta(hours=4)).isoformat(),
            "recipient_name": "Sam Example",
            "recipient_email": "sam@example.test",
            "recipient_phone": "+1 555 010 0100",
            "delivery_address": None,
            "fulfillment_instructions": None,
            "promotion_code": None,
            "payment_scenario": "succeeds",
            "lines": [
                {
                    "client_line_id": "phase10-scheduled-line",
                    "menu_item_slug": "harissa-chicken-bowl",
                    "quantity": 1,
                    "option_ids": [item["option_groups"][0]["options"][0]["id"]],
                    "note": None,
                }
            ],
        },
    )
    assert scheduled.status_code == 201

    too_early = seeded_client.post(
        f"/api/v1/admin/orders/{scheduled.json()['public_reference']}/transitions",
        headers=headers,
        json={"status": "accepted"},
    )
    assert too_early.status_code == 409
    assert "preparation window" in too_early.json()["detail"]
