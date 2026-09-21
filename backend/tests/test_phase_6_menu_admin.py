from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient


def owner_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/admin/sign-in",
        json={"email": "owner@nosh.example", "password": "test-admin-password"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def new_menu_item_payload(client: TestClient) -> dict[str, object]:
    headers = owner_headers(client)
    setup = client.get("/api/v1/admin/menu/setup", headers=headers)
    assert setup.status_code == 200
    references = setup.json()
    published_media = next(
        media
        for media in references["media"]
        if media["publication_state"] == "published"
    )
    return {
        "name": "Smoky halloumi plate",
        "slug": "smoky-halloumi-plate",
        "description": "Halloumi, charred peppers, herbs, and a bright lemon dressing.",
        "category_id": references["categories"][0]["id"],
        "media_id": published_media["id"],
        "ingredients": ["Halloumi", "Peppers", "Lemon"],
        "dietary_tags": ["vegetarian", "gluten-aware"],
        "base_price_minor": 1560,
        "demo_discount_minor": 160,
        "display_order": 2,
        "publication_state": "published",
        "allergen_ids": [references["allergens"][0]["id"]],
        "option_groups": [
            {
                "name": "Choose a side",
                "kind": "choice",
                "minimum_selections": 1,
                "maximum_selections": 1,
                "options": [
                    {
                        "name": "Warm grains",
                        "price_delta_minor": 0,
                        "is_available": True,
                    },
                    {
                        "name": "Citrus salad",
                        "price_delta_minor": 75,
                        "is_available": True,
                    },
                ],
            },
            {
                "name": "Add to the plate",
                "kind": "extra",
                "minimum_selections": 0,
                "maximum_selections": 1,
                "options": [
                    {
                        "name": "Extra herbs",
                        "price_delta_minor": 50,
                        "is_available": True,
                    }
                ],
            },
        ],
        "availability": {
            "location_id": references["locations"][0]["id"],
            "state": "available",
        },
    }


def test_owner_can_create_a_publishable_menu_item_with_options_and_allergens(
    seeded_client: TestClient,
) -> None:
    headers = owner_headers(seeded_client)
    payload = new_menu_item_payload(seeded_client)

    created = seeded_client.post("/api/v1/admin/menu", headers=headers, json=payload)

    assert created.status_code == 201
    item = created.json()
    assert item["final_price_minor"] == 1400
    assert item["availability"]["state"] == "available"
    assert item["option_groups"][0]["minimum_selections"] == 1
    assert item["option_groups"][1]["kind"] == "extra"
    assert item["allergens"][0]["id"] == payload["allergen_ids"][0]
    assert item["history"][0]["action"] == "created"

    public_menu = seeded_client.get(
        "/api/v1/catalog/menu-items", params={"location_slug": "market-quarter"}
    )
    assert public_menu.status_code == 200
    published_item = next(
        menu_item
        for menu_item in public_menu.json()
        if menu_item["slug"] == payload["slug"]
    )
    assert published_item["final_price_minor"] == 1400
    assert published_item["option_groups"][0]["kind"] == "choice"
    assert published_item["allergens"][0]["slug"] == item["allergens"][0]["slug"]

    cannot_hide_live_image = seeded_client.patch(
        f"/api/v1/admin/media/{item['media']['id']}",
        headers=headers,
        json={"publication_state": "draft"},
    )
    assert cannot_hide_live_image.status_code == 409

    featured = seeded_client.put(
        "/api/v1/admin/menu/featured",
        headers=headers,
        json={"menu_item_id": item["id"]},
    )
    assert featured.status_code == 200
    assert featured.json()["menu_item_name"] == item["name"]
    public_home = seeded_client.get("/api/v1/catalog/home")
    featured_block = next(
        block for block in public_home.json() if block["content_key"] == "featured-dish"
    )
    assert featured_block["featured_menu_item_slug"] == item["slug"]


def test_availability_can_be_paused_or_scheduled_without_editing_the_item(
    seeded_client: TestClient,
) -> None:
    headers = owner_headers(seeded_client)
    payload = new_menu_item_payload(seeded_client)
    item = seeded_client.post(
        "/api/v1/admin/menu", headers=headers, json=payload
    ).json()

    paused = seeded_client.patch(
        f"/api/v1/admin/menu/{item['slug']}/availability",
        headers=headers,
        json={
            "location_id": payload["availability"]["location_id"],
            "state": "temporarily_unavailable",
        },
    )
    assert paused.status_code == 200
    assert paused.json()["availability"]["state"] == "temporarily_unavailable"
    assert paused.json()["history"][0]["action"] == "availability_changed"

    public_menu = seeded_client.get(
        "/api/v1/catalog/menu-items", params={"location_slug": "market-quarter"}
    ).json()
    assert (
        next(menu_item for menu_item in public_menu if menu_item["id"] == item["id"])[
            "availability"
        ]
        == "temporarily_unavailable"
    )

    invalid_schedule = seeded_client.patch(
        f"/api/v1/admin/menu/{item['slug']}/availability",
        headers=headers,
        json={
            "location_id": payload["availability"]["location_id"],
            "state": "scheduled",
        },
    )
    assert invalid_schedule.status_code == 422

    start = datetime.now(UTC) + timedelta(hours=1)
    end = start + timedelta(hours=2)
    scheduled = seeded_client.patch(
        f"/api/v1/admin/menu/{item['slug']}/availability",
        headers=headers,
        json={
            "location_id": payload["availability"]["location_id"],
            "state": "scheduled",
            "available_from": start.isoformat(),
            "available_until": end.isoformat(),
        },
    )
    assert scheduled.status_code == 200
    assert scheduled.json()["availability"]["state"] == "scheduled"
    scheduled_public_menu = seeded_client.get(
        "/api/v1/catalog/menu-items", params={"location_slug": "market-quarter"}
    ).json()
    assert (
        next(
            menu_item
            for menu_item in scheduled_public_menu
            if menu_item["id"] == item["id"]
        )["availability"]
        == "temporarily_unavailable"
    )


def test_kitchen_user_cannot_change_menu_content(seeded_client: TestClient) -> None:
    signed_in = seeded_client.post(
        "/api/v1/auth/admin/sign-in",
        json={"email": "kitchen@nosh.example", "password": "test-admin-password"},
    )
    assert signed_in.status_code == 200

    denied = seeded_client.get(
        "/api/v1/admin/menu/setup",
        headers={"Authorization": f"Bearer {signed_in.json()['access_token']}"},
    )

    assert denied.status_code == 403
