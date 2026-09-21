from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_engine
from app.models import Location, OnlineOrderingState
from app.services.seed import seed_database


def staff_headers(client: TestClient, email: str) -> dict[str, str]:
    signed_in = client.post(
        "/api/v1/auth/admin/sign-in",
        json={"email": email, "password": "test-admin-password"},
    )
    assert signed_in.status_code == 200
    return {"Authorization": f"Bearer {signed_in.json()['access_token']}"}


def checkout_payload(client: TestClient, *, idempotency_key: str) -> dict[str, object]:
    item = client.get("/api/v1/catalog/menu-items/harissa-chicken-bowl").json()
    return {
        "idempotency_key": idempotency_key,
        "location_slug": "market-quarter",
        "fulfillment_method": "delivery",
        "timing": "immediate",
        "scheduled_for": None,
        "recipient_name": "Desk Customer",
        "recipient_email": "desk@example.test",
        "recipient_phone": "+1 555 010 0111",
        "delivery_address": "11 Desk Lane",
        "fulfillment_instructions": "Leave with the host.",
        "promotion_code": None,
        "payment_scenario": "succeeds",
        "lines": [
            {
                "client_line_id": "phase11-desk-line",
                "menu_item_slug": "harissa-chicken-bowl",
                "quantity": 2,
                "option_ids": [item["option_groups"][0]["options"][0]["id"]],
                "note": "No cutlery, please.",
            }
        ],
    }


def checkout_order(client: TestClient, *, idempotency_key: str) -> dict[str, object]:
    response = client.post(
        "/api/v1/orders/checkout",
        json=checkout_payload(client, idempotency_key=idempotency_key),
    )
    assert response.status_code == 201
    return response.json()


def transition(
    client: TestClient,
    reference: str,
    headers: dict[str, str],
    next_status: str,
) -> dict[str, object]:
    response = client.post(
        f"/api/v1/admin/orders/{reference}/transitions",
        headers=headers,
        json={"status": next_status},
    )
    assert response.status_code == 200
    return response.json()


def test_order_desk_queues_filters_and_private_staff_detail(
    seeded_client: TestClient,
) -> None:
    receipt = checkout_order(seeded_client, idempotency_key="phase11-desk-order-001")
    reference = str(receipt["public_reference"])
    kitchen_headers = staff_headers(seeded_client, "kitchen@nosh.example")

    desk = seeded_client.get(
        "/api/v1/admin/orders",
        headers=kitchen_headers,
        params={
            "query": "desk customer",
            "fulfillment_method": "delivery",
            "status": "submitted",
            "starts_at": (datetime.now(UTC) - timedelta(minutes=1)).isoformat(),
        },
    )
    assert desk.status_code == 200
    payload = desk.json()
    assert payload["total"] == 1
    assert payload["orders"][0]["public_reference"] == reference
    assert payload["orders"][0]["queue"] == "needs_approval"
    assert (
        next(
            entry
            for entry in payload["queue_counts"]
            if entry["queue"] == "needs_approval"
        )["count"]
        == 1
    )

    detail = seeded_client.get(
        f"/api/v1/admin/orders/{reference}", headers=kitchen_headers
    )
    assert detail.status_code == 200
    assert detail.json()["recipient_email"] == "desk@example.test"
    assert detail.json()["delivery_address"] == "11 Desk Lane"
    assert detail.json()["fulfillment_instructions"] == "Leave with the host."
    assert detail.json()["lines"][0]["note"] == "No cutlery, please."
    assert detail.json()["lines"][0]["allergens"] == [
        {"name": "Sesame", "slug": "sesame"}
    ]
    assert detail.json()["valid_next_statuses"] == [
        "accepted",
        "declined",
        "cancelled",
        "needs_contact",
    ]

    transition(seeded_client, reference, kitchen_headers, "accepted")
    transition(seeded_client, reference, kitchen_headers, "preparing")
    transition(seeded_client, reference, kitchen_headers, "ready_for_courier")

    ready_queue = seeded_client.get(
        "/api/v1/admin/orders", headers=kitchen_headers, params={"queue": "ready"}
    )
    assert ready_queue.status_code == 200
    assert ready_queue.json()["orders"][0]["status"] == "ready_for_courier"
    assert ready_queue.json()["orders"][0]["public_reference"] == reference

    current_detail = seeded_client.get(
        f"/api/v1/admin/orders/{reference}", headers=kitchen_headers
    )
    assert current_detail.json()["valid_next_statuses"] == [
        "handed_to_courier",
        "declined",
        "cancelled",
        "needs_contact",
    ]
    assert current_detail.json()["status_events"][-1]["actor_name"] == "Nosh kitchen"


def test_sensitive_order_outcomes_and_online_controls_are_server_enforced(
    seeded_client: TestClient,
) -> None:
    receipt = checkout_order(
        seeded_client, idempotency_key="phase11-controls-order-001"
    )
    reference = str(receipt["public_reference"])
    kitchen_headers = staff_headers(seeded_client, "kitchen@nosh.example")
    manager_headers = staff_headers(seeded_client, "manager@nosh.example")

    kitchen_decline = seeded_client.post(
        f"/api/v1/admin/orders/{reference}/transitions",
        headers=kitchen_headers,
        json={"status": "declined", "reason": "kitchen_unavailable"},
    )
    assert kitchen_decline.status_code == 403

    controls = seeded_client.get(
        "/api/v1/admin/orders/controls", headers=manager_headers
    )
    assert controls.status_code == 200
    location = controls.json()[0]
    pause_until = datetime.now(UTC) + timedelta(minutes=30)
    paused = seeded_client.put(
        f"/api/v1/admin/orders/locations/{location['id']}/controls",
        headers=manager_headers,
        json={
            "online_ordering_state": "timed_pause",
            "online_ordering_paused_until": pause_until.isoformat(),
            "preparation_minutes": 35,
            "demo_capacity": 24,
        },
    )
    assert paused.status_code == 200
    assert paused.json()["ordering_available"] is False
    assert paused.json()["preparation_minutes"] == 35

    public_location = seeded_client.get("/api/v1/catalog/locations").json()[0]
    assert public_location["online_ordering_available"] is False
    assert "paused until" in public_location["online_ordering_message"]

    item = seeded_client.get("/api/v1/catalog/menu-items/harissa-chicken-bowl").json()
    paused_quote = seeded_client.post(
        "/api/v1/catalog/cart/quote",
        json={
            "lines": [
                {
                    "client_line_id": "phase11-paused-quote",
                    "menu_item_slug": "harissa-chicken-bowl",
                    "quantity": 1,
                    "option_ids": [item["option_groups"][0]["options"][0]["id"]],
                    "note": None,
                }
            ]
        },
    )
    assert paused_quote.status_code == 409

    capacity_disabled = seeded_client.put(
        f"/api/v1/admin/orders/locations/{location['id']}/controls",
        headers=manager_headers,
        json={
            "online_ordering_state": "on",
            "online_ordering_paused_until": None,
            "preparation_minutes": 35,
            "demo_capacity": 0,
        },
    )
    assert capacity_disabled.status_code == 200
    capacity_checkout = seeded_client.post(
        "/api/v1/orders/checkout",
        json=checkout_payload(
            seeded_client, idempotency_key="phase11-capacity-exhausted-001"
        ),
    )
    assert capacity_checkout.status_code == 409
    assert "capacity" in capacity_checkout.json()["detail"]

    kitchen_controls = seeded_client.put(
        f"/api/v1/admin/orders/locations/{location['id']}/controls",
        headers=kitchen_headers,
        json={
            "online_ordering_state": "off",
            "online_ordering_paused_until": None,
            "preparation_minutes": 25,
            "demo_capacity": 40,
        },
    )
    assert kitchen_controls.status_code == 403


def test_repeatable_seed_preserves_staff_order_controls(seeded_settings) -> None:
    with Session(get_engine(seeded_settings.database_url)) as session:
        location = session.scalar(
            select(Location).where(Location.slug == "market-quarter")
        )
        assert location is not None
        location.online_ordering_state = OnlineOrderingState.OFF
        location.online_ordering_paused_until = None
        location.preparation_minutes = 55
        location.demo_capacity = 7
        session.commit()

        seed_database(session, seeded_settings)
        session.refresh(location)
        assert location.online_ordering_state == OnlineOrderingState.OFF
        assert location.online_ordering_paused_until is None
        assert location.preparation_minutes == 55
        assert location.demo_capacity == 7
