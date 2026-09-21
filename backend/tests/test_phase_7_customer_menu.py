from fastapi.testclient import TestClient


def test_customer_menu_uses_the_default_published_location(
    seeded_client: TestClient,
) -> None:
    response = seeded_client.get("/api/v1/catalog/menu-items")

    assert response.status_code == 200
    olive_oil_cake = next(
        item for item in response.json() if item["slug"] == "olive-oil-cake"
    )
    assert olive_oil_cake["availability"] == "temporarily_unavailable"


def test_customer_can_read_a_published_dish_detail(seeded_client: TestClient) -> None:
    response = seeded_client.get("/api/v1/catalog/menu-items/harissa-chicken-bowl")

    assert response.status_code == 200
    item = response.json()
    assert item["name"] == "Harissa chicken bowl"
    assert item["availability"] == "available"
    assert item["option_groups"]
    assert item["allergens"]


def test_customer_menu_detail_hides_missing_or_private_dishes(
    seeded_client: TestClient,
) -> None:
    response = seeded_client.get("/api/v1/catalog/menu-items/not-on-the-menu")

    assert response.status_code == 404
