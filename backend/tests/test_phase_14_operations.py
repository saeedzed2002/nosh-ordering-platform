from fastapi.testclient import TestClient


def staff_headers(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/admin/sign-in",
        json={"email": email, "password": "test-admin-password"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def customer_headers(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/customer/sign-up",
        json={
            "email": email,
            "display_name": "Operations Customer",
            "password": "local-operations-password-2026",
        },
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def checkout_with_promotion(client: TestClient) -> None:
    item = client.get("/api/v1/catalog/menu-items/harissa-chicken-bowl").json()
    response = client.post(
        "/api/v1/orders/checkout",
        json={
            "idempotency_key": "phase14-reports-order-001",
            "location_slug": "market-quarter",
            "fulfillment_method": "pickup",
            "timing": "immediate",
            "scheduled_for": None,
            "recipient_name": "Report Customer",
            "recipient_email": "report@example.test",
            "recipient_phone": "+1 555 010 0190",
            "delivery_address": None,
            "fulfillment_instructions": None,
            "promotion_code": "WELCOME10",
            "payment_scenario": "succeeds",
            "lines": [
                {
                    "client_line_id": "phase14-report-line",
                    "menu_item_slug": "harissa-chicken-bowl",
                    "quantity": 2,
                    "option_ids": [item["option_groups"][0]["options"][0]["id"]],
                    "note": None,
                }
            ],
        },
    )
    assert response.status_code == 201


def test_promotions_settings_and_audit_are_operable_by_staff(
    seeded_client: TestClient,
) -> None:
    manager = staff_headers(seeded_client, "manager@nosh.example")
    owner = staff_headers(seeded_client, "owner@nosh.example")
    created = seeded_client.post(
        "/api/v1/admin/operations/promotions",
        headers=manager,
        json={
            "code": "AUTUMN15",
            "name": "Autumn fifteen",
            "kind": "percentage",
            "discount_value": 1500,
            "minimum_order_minor": 1000,
            "starts_at": None,
            "ends_at": None,
            "usage_limit": 25,
            "is_active": True,
        },
    )
    assert created.status_code == 201
    promotion = created.json()
    assert promotion["remaining_uses"] == 25
    updated = seeded_client.put(
        f"/api/v1/admin/operations/promotions/{promotion['id']}",
        headers=manager,
        json={
            **{
                key: promotion[key]
                for key in (
                    "code",
                    "kind",
                    "discount_value",
                    "minimum_order_minor",
                    "starts_at",
                    "ends_at",
                    "usage_limit",
                    "is_active",
                )
            },
            "name": "Autumn fifteen percent",
        },
    )
    assert updated.status_code == 200
    deactivated = seeded_client.post(
        f"/api/v1/admin/operations/promotions/{promotion['id']}/deactivate",
        headers=manager,
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False

    settings = seeded_client.get("/api/v1/admin/operations/settings", headers=manager)
    assert settings.status_code == 200
    location = settings.json()[0]
    saved = seeded_client.put(
        f"/api/v1/admin/operations/settings/{location['id']}",
        headers=manager,
        json={
            **{
                key: location[key]
                for key in location
                if key
                not in {"id", "slug", "hours", "preparation_minutes", "demo_capacity"}
            },
            "preparation_minutes": 31,
            "demo_capacity": 48,
            "hours": location["hours"],
        },
    )
    assert saved.status_code == 200
    assert saved.json()["preparation_minutes"] == 31

    audit = seeded_client.get("/api/v1/admin/operations/audit", headers=owner)
    assert audit.status_code == 200
    actions = {(entry["entity_type"], entry["action"]) for entry in audit.json()}
    assert ("promotion", "created") in actions
    assert ("promotion", "updated") in actions
    assert ("promotion", "deactivated") in actions
    assert ("restaurant_settings", "updated") in actions


def test_customer_state_is_owner_only_and_reports_are_based_on_orders(
    seeded_client: TestClient,
) -> None:
    manager = staff_headers(seeded_client, "manager@nosh.example")
    owner = staff_headers(seeded_client, "owner@nosh.example")
    customer = customer_headers(seeded_client, "operations.customer@example.com")
    customers = seeded_client.get("/api/v1/admin/operations/customers", headers=manager)
    assert customers.status_code == 200
    account = next(
        entry
        for entry in customers.json()
        if entry["email"] == "operations.customer@example.com"
    )
    assert "password_hash" not in account
    assert "orders" in account
    assert (
        seeded_client.patch(
            f"/api/v1/admin/operations/customers/{account['id']}/state",
            headers=manager,
            json={"is_active": False},
        ).status_code
        == 403
    )
    disabled = seeded_client.patch(
        f"/api/v1/admin/operations/customers/{account['id']}/state",
        headers=owner,
        json={"is_active": False},
    )
    assert disabled.status_code == 200
    assert disabled.json()["is_active"] is False
    assert (
        seeded_client.get("/api/v1/account/profile", headers=customer).status_code
        == 401
    )

    checkout_with_promotion(seeded_client)
    report = seeded_client.get("/api/v1/admin/operations/reports", headers=manager)
    assert report.status_code == 200
    payload = report.json()
    assert payload["order_count"] == 1
    assert payload["demo_revenue_minor"] == 2610
    assert payload["average_order_value_minor"] == 2610
    assert payload["popular_food"] == [
        {"menu_item_name": "Harissa chicken bowl", "quantity": 2, "revenue_minor": 2900}
    ]
    assert payload["promotion_use"] == [
        {"code": "WELCOME10", "uses": 1, "discount_minor": 290}
    ]
