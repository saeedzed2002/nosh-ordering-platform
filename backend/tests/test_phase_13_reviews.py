from fastapi.testclient import TestClient


def customer_headers(client: TestClient, email: str) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/customer/sign-up",
        json={
            "email": email,
            "display_name": "Review Customer",
            "password": "local-review-password-2026",
        },
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def manager_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/admin/sign-in",
        json={"email": "manager@nosh.example", "password": "test-admin-password"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def checkout_payload(client: TestClient) -> dict[str, object]:
    item = client.get("/api/v1/catalog/menu-items/harissa-chicken-bowl").json()
    return {
        "idempotency_key": "phase13-review-checkout-001",
        "location_slug": "market-quarter",
        "fulfillment_method": "delivery",
        "timing": "immediate",
        "recipient_name": "Review Customer",
        "recipient_email": "review.customer@example.test",
        "recipient_phone": "+1 555 010 0190",
        "delivery_address": "13 Review Lane",
        "fulfillment_instructions": None,
        "promotion_code": None,
        "payment_scenario": "succeeds",
        "lines": [
            {
                "client_line_id": "phase13-review-line",
                "menu_item_slug": "harissa-chicken-bowl",
                "quantity": 1,
                "option_ids": [item["option_groups"][0]["options"][0]["id"]],
                "note": None,
            }
        ],
    }


def transition_to_delivered(
    client: TestClient, reference: str, headers: dict[str, str]
) -> None:
    for next_status in [
        "accepted",
        "preparing",
        "ready_for_courier",
        "handed_to_courier",
        "out_for_delivery",
        "delivered",
    ]:
        response = client.post(
            f"/api/v1/admin/orders/{reference}/transitions",
            headers=headers,
            json={"status": next_status},
        )
        assert response.status_code == 200


def test_reviews_require_an_owned_delivered_item_and_public_only_shows_approved(
    seeded_client: TestClient,
) -> None:
    owner_headers = customer_headers(seeded_client, "review.owner@example.com")
    other_headers = customer_headers(seeded_client, "review.other@example.com")
    order = seeded_client.post(
        "/api/v1/orders/checkout",
        headers=owner_headers,
        json=checkout_payload(seeded_client),
    )
    assert order.status_code == 201
    reference = order.json()["public_reference"]
    order_item_id = seeded_client.get(
        "/api/v1/account/orders", headers=owner_headers
    ).json()[0]["lines"][0]["id"]

    before_delivery = seeded_client.post(
        "/api/v1/account/reviews",
        headers=owner_headers,
        json={
            "order_item_id": order_item_id,
            "rating": 5,
            "body": "A clear, thoughtful bowl with a bright finish.",
        },
    )
    assert before_delivery.status_code == 404

    transition_to_delivered(seeded_client, reference, manager_headers(seeded_client))
    created = seeded_client.post(
        "/api/v1/account/reviews",
        headers=owner_headers,
        json={
            "order_item_id": order_item_id,
            "rating": 5,
            "body": "A clear, thoughtful bowl with a bright finish.",
        },
    )
    assert created.status_code == 201
    assert created.json()["status"] == "pending"
    review_id = created.json()["id"]
    assert (
        seeded_client.post(
            "/api/v1/account/reviews",
            headers=owner_headers,
            json={
                "order_item_id": order_item_id,
                "rating": 4,
                "body": "This duplicate review must not be accepted again.",
            },
        ).status_code
        == 409
    )
    assert (
        seeded_client.patch(
            f"/api/v1/account/reviews/{review_id}",
            headers=other_headers,
            json={"rating": 1, "body": "Another customer cannot edit this review."},
        ).status_code
        == 404
    )

    public_pending = seeded_client.get(
        "/api/v1/catalog/menu-items/harissa-chicken-bowl/reviews"
    )
    assert public_pending.json() == {
        "review_count": 0,
        "average_rating": None,
        "reviews": [],
    }
    moderated = seeded_client.post(
        f"/api/v1/admin/reviews/{review_id}/moderation",
        headers=manager_headers(seeded_client),
        json={"action": "approve"},
    )
    assert moderated.status_code == 200
    public_approved = seeded_client.get(
        "/api/v1/catalog/menu-items/harissa-chicken-bowl/reviews"
    )
    assert public_approved.json()["review_count"] == 1
    assert public_approved.json()["reviews"][0]["reviewer_name"] == "Review C."
    assert public_approved.json()["reviews"][0]["rating"] == 5

    hidden = seeded_client.post(
        f"/api/v1/admin/reviews/{review_id}/moderation",
        headers=manager_headers(seeded_client),
        json={"action": "hide", "internal_reason": "Needs clarification."},
    )
    assert hidden.status_code == 200
    assert (
        seeded_client.get(
            "/api/v1/catalog/menu-items/harissa-chicken-bowl/reviews"
        ).json()["reviews"]
        == []
    )
    kitchen = seeded_client.post(
        "/api/v1/auth/admin/sign-in",
        json={"email": "kitchen@nosh.example", "password": "test-admin-password"},
    )
    assert (
        seeded_client.get(
            "/api/v1/admin/reviews",
            headers={"Authorization": f"Bearer {kitchen.json()['access_token']}"},
        ).status_code
        == 403
    )
