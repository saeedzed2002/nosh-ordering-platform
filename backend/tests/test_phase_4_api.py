from io import BytesIO

from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_engine
from app.models import User
from app.services.auth import create_token


def test_seeded_catalog_is_available_from_versioned_api(seeded_client) -> None:
    api_base = seeded_client.get("/api/v1")
    openapi = seeded_client.get("/api/v1/openapi.json")
    categories = seeded_client.get("/api/v1/catalog/categories")
    menu = seeded_client.get(
        "/api/v1/catalog/menu-items", params={"location_slug": "market-quarter"}
    )
    collections = seeded_client.get("/api/v1/catalog/collections")
    home = seeded_client.get("/api/v1/catalog/home")

    assert api_base.status_code == 200
    assert api_base.json() == {"name": "Nosh API", "version": "v1"}
    assert openapi.status_code == 200
    assert "/api/v1/auth/admin/sign-in" in openapi.json()["paths"]
    assert "/api/v1/admin/media" in openapi.json()["paths"]
    assert categories.status_code == 200
    assert len(categories.json()) == 6
    assert menu.status_code == 200
    assert len(menu.json()) == 16
    assert (
        next(item for item in menu.json() if item["slug"] == "olive-oil-cake")[
            "availability"
        ]
        == "temporarily_unavailable"
    )
    assert collections.status_code == 200
    assert len(collections.json()) == 3
    assert home.status_code == 200
    assert {block["content_key"] for block in home.json()} == {
        "hero",
        "featured-dish",
        "kitchen-story",
        "location-callout",
    }


def test_admin_tokens_protect_media_and_refresh(seeded_client) -> None:
    signed_in = seeded_client.post(
        "/api/v1/auth/admin/sign-in",
        json={"email": "owner@nosh.example", "password": "test-admin-password"},
    )
    assert signed_in.status_code == 200
    token_pair = signed_in.json()

    current_user = seeded_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token_pair['access_token']}"},
    )
    assert current_user.status_code == 200
    assert current_user.json()["role"] == "admin"
    assert seeded_client.get("/api/v1/admin/media").status_code == 401

    admin_media = seeded_client.get(
        "/api/v1/admin/media",
        headers={"Authorization": f"Bearer {token_pair['access_token']}"},
    )
    assert admin_media.status_code == 200
    assert len(admin_media.json()) == 25
    original_media = seeded_client.get(
        f"/api/v1/admin/media/{admin_media.json()[0]['id']}/original",
        headers={"Authorization": f"Bearer {token_pair['access_token']}"},
    )
    assert original_media.status_code == 200
    assert original_media.headers["content-type"] == "image/webp"

    refreshed = seeded_client.post(
        "/api/v1/auth/refresh", json={"refresh_token": token_pair["refresh_token"]}
    )
    assert refreshed.status_code == 200
    refreshed_current_user = seeded_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {refreshed.json()['access_token']}"},
    )
    assert refreshed_current_user.status_code == 200


def test_non_admin_token_cannot_read_admin_media(
    seeded_client, seeded_settings
) -> None:
    with Session(get_engine(seeded_settings.database_url)) as session:
        customer = session.scalar(
            select(User)
            .options(joinedload(User.role))
            .where(User.email == "maya@example.test")
        )
        token = create_token(
            user=customer,
            token_type="access",
            expires_in_minutes=15,
            settings=seeded_settings,
        )

    response = seeded_client.get(
        "/api/v1/admin/media", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403


def webp_bytes() -> bytes:
    image = Image.new("RGB", (24, 16), (13, 36, 23))
    output = BytesIO()
    image.save(output, format="WEBP")
    return output.getvalue()


def test_media_upload_validates_before_persisting(
    seeded_client, seeded_settings
) -> None:
    signed_in = seeded_client.post(
        "/api/v1/auth/admin/sign-in",
        json={"email": "owner@nosh.example", "password": "test-admin-password"},
    )
    headers = {"Authorization": f"Bearer {signed_in.json()['access_token']}"}
    existing_files = sorted(
        path.relative_to(seeded_settings.media_root)
        for path in seeded_settings.media_root.rglob("*")
    )

    invalid_upload = seeded_client.post(
        "/api/v1/admin/media",
        headers=headers,
        data={"alt_text": "Invalid file"},
        files={"file": ("invalid.svg", b"<svg />", "image/svg+xml")},
    )
    assert invalid_upload.status_code == 422
    assert (
        sorted(
            path.relative_to(seeded_settings.media_root)
            for path in seeded_settings.media_root.rglob("*")
        )
        == existing_files
    )

    uploaded = seeded_client.post(
        "/api/v1/admin/media",
        headers=headers,
        data={"alt_text": "Development image for media validation"},
        files={"file": ("valid.webp", webp_bytes(), "image/webp")},
    )
    assert uploaded.status_code == 201
    media = uploaded.json()
    assert media["mime_type"] == "image/webp"
    assert media["width"] == 24
    assert media["height"] == 16
    assert (seeded_settings.media_root / "originals" / f"{media['id']}.webp").is_file()
    assert (seeded_settings.media_root / "thumbnails" / f"{media['id']}.webp").is_file()

    catalog = seeded_client.get("/api/v1/catalog/menu-items").json()
    thumbnail = seeded_client.get(
        f"/api/v1/media/{catalog[0]['media']['id']}/thumbnail"
    )
    assert thumbnail.status_code == 200
    assert thumbnail.headers["content-type"] == "image/webp"
