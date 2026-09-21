from fastapi.testclient import TestClient


def harissa_choices(seeded_client: TestClient) -> tuple[dict[str, object], str, str]:
    item = seeded_client.get("/api/v1/catalog/menu-items/harissa-chicken-bowl").json()
    base_option_id = item["option_groups"][0]["options"][0]["id"]
    extra_option_id = item["option_groups"][1]["options"][1]["id"]
    return item, base_option_id, extra_option_id


def test_cart_quote_uses_the_published_price_and_selected_extras(
    seeded_client: TestClient,
) -> None:
    item, base_option_id, extra_option_id = harissa_choices(seeded_client)

    response = seeded_client.post(
        "/api/v1/catalog/cart/quote",
        json={
            "lines": [
                {
                    "client_line_id": "harissa-1",
                    "menu_item_slug": "harissa-chicken-bowl",
                    "quantity": 2,
                    "option_ids": [base_option_id, extra_option_id],
                    "note": "  Sauce on the side  ",
                }
            ]
        },
    )

    assert response.status_code == 200
    quote = response.json()
    expected_unit_price = item["final_price_minor"] + 75
    assert quote["subtotal_minor"] == expected_unit_price * 2
    line = quote["lines"][0]
    assert line["client_line_id"] == "harissa-1"
    assert line["menu_item_slug"] == "harissa-chicken-bowl"
    assert line["name"] == "Harissa chicken bowl"
    assert line["quantity"] == 2
    assert line["note"] == "Sauce on the side"
    assert line["unit_price_minor"] == expected_unit_price
    assert line["line_total_minor"] == expected_unit_price * 2
    assert line["currency_code"] == "USD"
    assert {option["id"] for option in line["selected_options"]} == {
        base_option_id,
        extra_option_id,
    }


def test_cart_quote_rejects_missing_or_excess_required_choices(
    seeded_client: TestClient,
) -> None:
    item, base_option_id, _ = harissa_choices(seeded_client)
    second_base_option_id = item["option_groups"][0]["options"][1]["id"]

    missing = seeded_client.post(
        "/api/v1/catalog/cart/quote",
        json={
            "lines": [
                {
                    "client_line_id": "missing-base",
                    "menu_item_slug": "harissa-chicken-bowl",
                    "quantity": 1,
                    "option_ids": [],
                }
            ]
        },
    )
    too_many = seeded_client.post(
        "/api/v1/catalog/cart/quote",
        json={
            "lines": [
                {
                    "client_line_id": "two-bases",
                    "menu_item_slug": "harissa-chicken-bowl",
                    "quantity": 1,
                    "option_ids": [base_option_id, second_base_option_id],
                }
            ]
        },
    )

    assert missing.status_code == 422
    assert "Choose a base" in missing.json()["detail"]
    assert too_many.status_code == 422
    assert "Choose a base" in too_many.json()["detail"]


def test_cart_quote_rejects_a_dish_the_kitchen_has_paused(
    seeded_client: TestClient,
) -> None:
    response = seeded_client.post(
        "/api/v1/catalog/cart/quote",
        json={
            "lines": [
                {
                    "client_line_id": "paused-cake",
                    "menu_item_slug": "olive-oil-cake",
                    "quantity": 1,
                    "option_ids": [],
                }
            ]
        },
    )

    assert response.status_code == 409
    assert "not available" in response.json()["detail"]
