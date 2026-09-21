from fastapi.testclient import TestClient


def owner_headers(client: TestClient) -> dict[str, str]:
    signed_in = client.post(
        "/api/v1/auth/admin/sign-in",
        json={"email": "owner@nosh.example", "password": "test-admin-password"},
    )
    assert signed_in.status_code == 200
    return {"Authorization": f"Bearer {signed_in.json()['access_token']}"}


def test_home_draft_stays_private_until_a_saved_revision_is_published(
    seeded_client: TestClient,
) -> None:
    headers = owner_headers(seeded_client)
    initial_home = seeded_client.get("/api/v1/catalog/home")
    assert initial_home.status_code == 200
    initial_hero = next(
        block for block in initial_home.json() if block["content_key"] == "hero"
    )

    editable_home = seeded_client.get("/api/v1/admin/home", headers=headers)
    assert editable_home.status_code == 200
    editable_hero = next(
        block for block in editable_home.json() if block["content_key"] == "hero"
    )
    assert editable_hero["latest_draft"] is None

    draft_payload = {
        "heading": "A fresh welcome for local service.",
        "supporting_copy": (
            "This private draft proves that customer content stays stable."
        ),
        "action_label": "See today",
        "action_href": "#menu",
        "media_id": editable_hero["media"]["id"],
    }
    saved_draft = seeded_client.put(
        "/api/v1/admin/home/hero/draft", headers=headers, json=draft_payload
    )
    assert saved_draft.status_code == 200
    saved_hero = saved_draft.json()
    assert saved_hero["latest_draft"]["snapshot"] == draft_payload
    assert saved_hero["latest_draft"]["action"] == "draft_saved"

    public_before_publish = seeded_client.get("/api/v1/catalog/home").json()
    assert (
        next(
            block for block in public_before_publish if block["content_key"] == "hero"
        )["heading"]
        == initial_hero["heading"]
    )

    published = seeded_client.post(
        "/api/v1/admin/home/hero/publish",
        headers=headers,
        json={"revision_id": saved_hero["latest_draft"]["id"]},
    )
    assert published.status_code == 200
    assert published.json()["latest_draft"] is None
    assert published.json()["history"][0]["action"] == "published"

    public_after_publish = seeded_client.get("/api/v1/catalog/home").json()
    assert (
        next(block for block in public_after_publish if block["content_key"] == "hero")[
            "heading"
        ]
        == draft_payload["heading"]
    )


def test_media_metadata_and_usage_visibility_stay_role_protected(
    seeded_client: TestClient,
) -> None:
    headers = owner_headers(seeded_client)
    denied = seeded_client.get("/api/v1/admin/home")
    assert denied.status_code == 401

    home = seeded_client.get("/api/v1/admin/home", headers=headers).json()
    hero = next(block for block in home if block["content_key"] == "hero")
    hero_media_id = hero["media"]["id"]
    admin_thumbnail = seeded_client.get(
        f"/api/v1/admin/media/{hero_media_id}/thumbnail", headers=headers
    )
    assert admin_thumbnail.status_code == 200
    assert admin_thumbnail.headers["content-type"] == "image/webp"

    library = seeded_client.get("/api/v1/admin/media", headers=headers)
    assert library.status_code == 200
    hero_media = next(asset for asset in library.json() if asset["id"] == hero_media_id)
    assert any(usage["content_key"] == "hero" for usage in hero_media["usages"])

    focused = seeded_client.patch(
        f"/api/v1/admin/media/{hero_media_id}",
        headers=headers,
        json={"alt_text": "A refined local kitchen welcome", "focal_point_x": 20},
    )
    assert focused.status_code == 200
    assert focused.json()["focal_point_x"] == 20
    assert focused.json()["alt_text"] == "A refined local kitchen welcome"

    cannot_hide_live_media = seeded_client.patch(
        f"/api/v1/admin/media/{hero_media_id}",
        headers=headers,
        json={"publication_state": "draft"},
    )
    assert cannot_hide_live_media.status_code == 409
