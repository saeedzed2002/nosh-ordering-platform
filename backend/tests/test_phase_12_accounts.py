from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.session import get_engine
from app.models import MenuItem


def create_customer(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/customer/sign-up",
        json={
            "email": email,
            "display_name": "Account Customer",
            "password": "local-account-password-2026",
        },
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def checkout_payload(client: TestClient, idempotency_key: str) -> dict[str, object]:
    item = client.get("/api/v1/catalog/menu-items/harissa-chicken-bowl").json()
    return {
        "idempotency_key": idempotency_key,
        "location_slug": "market-quarter",
        "fulfillment_method": "delivery",
        "timing": "immediate",
        "scheduled_for": None,
        "recipient_name": "Account Customer",
        "recipient_email": "account.customer@example.test",
        "recipient_phone": "+1 555 010 0155",
        "delivery_address": "12 Account Lane",
        "fulfillment_instructions": None,
        "promotion_code": None,
        "payment_scenario": "succeeds",
        "lines": [
            {
                "client_line_id": "account-reorder-line",
                "menu_item_slug": "harissa-chicken-bowl",
                "quantity": 1,
                "option_ids": [item["option_groups"][0]["options"][0]["id"]],
                "note": "No cutlery.",
            }
        ],
    }


def test_customer_account_profile_addresses_and_favorites_are_owned(
    seeded_client: TestClient,
) -> None:
    first_headers = create_customer(seeded_client, "first.account@example.com")
    second_headers = create_customer(seeded_client, "second.account@example.com")

    profile = seeded_client.get("/api/v1/account/profile", headers=first_headers)
    assert profile.status_code == 200
    assert profile.json()["role"] == "customer"
    updated = seeded_client.patch(
        "/api/v1/account/profile",
        headers=first_headers,
        json={"display_name": "Updated Customer"},
    )
    assert updated.status_code == 200
    assert updated.json()["display_name"] == "Updated Customer"

    home = seeded_client.post(
        "/api/v1/account/addresses",
        headers=first_headers,
        json={
            "label": "Home",
            "recipient_name": "Updated Customer",
            "phone": "+1 555 010 0155",
            "address_text": "12 Account Lane",
            "is_default": False,
        },
    )
    assert home.status_code == 201
    assert home.json()["is_default"] is True
    work = seeded_client.post(
        "/api/v1/account/addresses",
        headers=first_headers,
        json={
            "label": "Work",
            "recipient_name": "Updated Customer",
            "phone": "+1 555 010 0156",
            "address_text": "13 Account Lane",
            "is_default": True,
        },
    )
    assert work.status_code == 201
    addresses = seeded_client.get("/api/v1/account/addresses", headers=first_headers)
    assert [entry["label"] for entry in addresses.json()] == ["Work", "Home"]
    assert [entry["is_default"] for entry in addresses.json()] == [True, False]
    assert (
        seeded_client.delete(
            f"/api/v1/account/addresses/{work.json()['id']}", headers=second_headers
        ).status_code
        == 404
    )

    saved = seeded_client.put(
        "/api/v1/account/favorites/harissa-chicken-bowl", headers=first_headers
    )
    assert saved.status_code == 200
    assert saved.json()["is_available"] is True
    assert (
        seeded_client.get("/api/v1/account/favorites", headers=second_headers).json()
        == []
    )
    assert (
        seeded_client.delete(
            "/api/v1/account/favorites/harissa-chicken-bowl", headers=second_headers
        ).status_code
        == 404
    )


def test_customer_order_history_reorder_and_ownership_revalidate_current_menu(
    seeded_client: TestClient, seeded_settings: Settings
) -> None:
    first_headers = create_customer(seeded_client, "history.first@example.com")
    second_headers = create_customer(seeded_client, "history.second@example.com")
    payload = checkout_payload(seeded_client, "phase12-account-checkout-001")
    first_checkout = seeded_client.post(
        "/api/v1/orders/checkout", headers=first_headers, json=payload
    )
    assert first_checkout.status_code == 201
    reference = first_checkout.json()["public_reference"]
    assert (
        seeded_client.post(
            "/api/v1/orders/checkout", headers=second_headers, json=payload
        ).status_code
        == 409
    )

    first_history = seeded_client.get("/api/v1/account/orders", headers=first_headers)
    assert first_history.status_code == 200
    assert [entry["public_reference"] for entry in first_history.json()] == [reference]
    assert (
        seeded_client.get("/api/v1/account/orders", headers=second_headers).json() == []
    )
    forbidden_reorder = seeded_client.post(
        f"/api/v1/account/orders/{reference}/reorder", headers=second_headers
    )
    assert forbidden_reorder.status_code == 404

    with Session(get_engine(seeded_settings.database_url)) as session:
        item = session.scalar(
            select(MenuItem).where(MenuItem.slug == "harissa-chicken-bowl")
        )
        assert item is not None
        item.base_price_minor += 200
        session.commit()

    reordered = seeded_client.post(
        f"/api/v1/account/orders/{reference}/reorder", headers=first_headers
    )
    assert reordered.status_code == 200
    assert reordered.json()["location_slug"] == "market-quarter"
    assert reordered.json()["lines"][0]["note"] == "No cutlery."
    assert reordered.json()["quote"]["lines"][0]["unit_price_minor"] == 1650
    assert first_checkout.json()["lines"][0]["unit_price_minor"] == 1450

    assert seeded_client.get("/api/v1/account/orders").status_code == 401
    assert (
        seeded_client.get(
            "/api/v1/account/orders", headers={"Authorization": "Bearer invalid"}
        ).status_code
        == 401
    )
