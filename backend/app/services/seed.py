from __future__ import annotations

from datetime import time
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import (
    Allergen,
    AvailabilityState,
    Category,
    CollectionMenuItem,
    CuratedCollection,
    HomeContent,
    Location,
    MediaAsset,
    MenuItem,
    MenuItemAllergen,
    MenuItemAvailability,
    OperatingHour,
    Option,
    OptionGroup,
    PublicationState,
    Role,
    RoleCode,
    User,
)
from app.services.auth import hash_password
from app.services.media import (
    create_development_seed_image,
    persist_image,
    validate_image_payload,
)

SEED_NAMESPACE = "https://nosh.local/phase-4/"


def seeded_id(key: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"{SEED_NAMESPACE}{key}")


def find_or_create(
    session: Session,
    model: type[object],
    key_field: object,
    key_value: object,
    **values: object,
) -> object:
    instance = session.scalar(select(model).where(key_field == key_value))
    if instance is None:
        instance = model(**values)
        session.add(instance)
        session.flush()
    return instance


def ensure_seed_media(
    session: Session,
    media_root: Path,
    key: str,
    alt_text: str,
    color: tuple[int, int, int],
) -> MediaAsset:
    media_id = seeded_id(f"media:{key}")
    media = session.get(MediaAsset, media_id)
    if media is not None:
        return media

    payload = create_development_seed_image(color, marker=key.encode("utf-8"))
    validated_image = validate_image_payload(payload, "image/webp")
    stored_image = persist_image(
        media_root,
        f"nosh-{key}-development-placeholder.webp",
        validated_image,
        media_id=media_id,
    )
    media = MediaAsset(
        id=stored_image.id,
        original_filename=f"nosh-{key}-development-placeholder.webp",
        original_path=stored_image.original_path,
        thumbnail_path=stored_image.thumbnail_path,
        mime_type=validated_image.mime_type,
        byte_size=len(validated_image.payload),
        width=validated_image.width,
        height=validated_image.height,
        checksum_sha256=validated_image.checksum_sha256,
        alt_text=alt_text,
        focal_point_x=50,
        focal_point_y=50,
        source_description=(
            "Generated local development placeholder; not restaurant photography."
        ),
        credit="Nosh local development seed",
        publication_state=PublicationState.PUBLISHED,
    )
    session.add(media)
    session.flush()
    return media


def seed_database(session: Session, settings: Settings) -> None:
    if settings.seed_admin_password is None:
        raise ValueError(
            "NOSH_SEED_ADMIN_PASSWORD is required before running the local seed."
        )

    roles = {
        code: find_or_create(
            session,
            Role,
            Role.code,
            code,
            id=seeded_id(f"role:{code.value}"),
            code=code,
            label=code.value.capitalize(),
        )
        for code in RoleCode
    }

    for email, display_name, role_code in [
        ("owner@nosh.example", "Nosh owner", RoleCode.OWNER),
        ("manager@nosh.example", "Nosh manager", RoleCode.MANAGER),
        ("kitchen@nosh.example", "Nosh kitchen", RoleCode.KITCHEN),
        ("maya@nosh.example", "Maya Reed", RoleCode.CUSTOMER),
        ("jordan@nosh.example", "Jordan Bell", RoleCode.CUSTOMER),
    ]:
        user = find_or_create(
            session,
            User,
            User.email,
            email,
            id=seeded_id(f"user:{email}"),
            email=email,
            display_name=display_name,
            password_hash=hash_password(settings.seed_admin_password),
            role_id=roles[role_code].id,
            is_active=True,
        )
        if user.role_id != roles[role_code].id:
            user.role_id = roles[role_code].id

    location = find_or_create(
        session,
        Location,
        Location.slug,
        "market-quarter",
        id=seeded_id("location:market-quarter"),
        name="Nosh Kitchen — Market Quarter",
        slug="market-quarter",
        address_text="12 Market Street, Market Quarter",
        pickup_instructions="Collect from the Nosh Kitchen counter.",
        delivery_area_text="Simulated delivery within the Market Quarter demo area.",
        pickup_available=True,
        delivery_available=True,
        preparation_minutes=25,
        demo_capacity=40,
        is_published=True,
    )
    for weekday in range(7):
        find_or_create(
            session,
            OperatingHour,
            OperatingHour.id,
            seeded_id(f"hour:market-quarter:{weekday}"),
            id=seeded_id(f"hour:market-quarter:{weekday}"),
            location_id=location.id,
            weekday=weekday,
            opens_at=None if weekday == 0 else time(12, 0),
            closes_at=None if weekday == 0 else time(21, 30),
            is_closed=weekday == 0,
        )

    category_specs = [
        ("fire-grill", "Fire & Grill", "Charred dishes from the Nosh grill."),
        ("grain-greens", "Grain & Greens", "Bright bowls and generous greens."),
        ("handhelds", "Handhelds", "Warm breads and fillings built for the hand."),
        ("sides", "Sides", "Useful plates for the middle of the table."),
        ("sweet-finish", "Sweet Finish", "A short and considered dessert list."),
        ("drinks", "Drinks", "Fresh non-alcoholic drinks for the local demo."),
    ]
    categories: dict[str, Category] = {}
    for index, (slug, name, description) in enumerate(category_specs):
        media = ensure_seed_media(
            session,
            settings.media_root,
            f"category-{slug}",
            f"Development placeholder for the {name} category.",
            ((70 + index * 19) % 256, (92 + index * 29) % 256, (54 + index * 37) % 256),
        )
        category = find_or_create(
            session,
            Category,
            Category.slug,
            slug,
            id=seeded_id(f"category:{slug}"),
            name=name,
            slug=slug,
            media_id=media.id,
            description=description,
            display_order=index,
            is_published=True,
        )
        if category.media_id is None:
            category.media_id = media.id
        categories[slug] = category
    allergens = {
        slug: find_or_create(
            session,
            Allergen,
            Allergen.slug,
            slug,
            id=seeded_id(f"allergen:{slug}"),
            name=name,
            slug=slug,
            description=f"Declared {name.lower()} allergen information.",
        )
        for slug, name in [
            ("wheat-gluten", "Wheat / gluten"),
            ("sesame", "Sesame"),
            ("dairy", "Dairy"),
            ("egg", "Egg"),
            ("soy", "Soy"),
            ("tree-nuts", "Tree nuts"),
            ("peanut", "Peanut"),
        ]
    }

    dish_specs = [
        (
            "harissa-chicken-bowl",
            "fire-grill",
            "Harissa chicken bowl",
            1450,
            ["halal-style", "spicy"],
            ["sesame"],
            "Charred chicken, hummus, cucumber, chickpeas, and pickled onion.",
        ),
        (
            "charred-lamb-kofta",
            "fire-grill",
            "Charred lamb kofta",
            1680,
            ["halal-style"],
            ["wheat-gluten", "dairy"],
            "Lamb kofta with warm flatbread, herbs, and yoghurt.",
        ),
        (
            "sumac-salmon",
            "fire-grill",
            "Sumac salmon",
            1820,
            ["gluten-aware"],
            ["sesame"],
            "Sumac salmon with lemon, herbs, and a roasted vegetable side.",
        ),
        (
            "mushroom-shawarma",
            "fire-grill",
            "Mushroom shawarma",
            1380,
            ["vegetarian", "spicy"],
            ["sesame"],
            "Spiced mushrooms with tahini, herbs, and crisp greens.",
        ),
        (
            "green-tahini-bowl",
            "grain-greens",
            "Green tahini bowl",
            1290,
            ["vegan", "gluten-aware"],
            ["sesame"],
            "Freekeh, greens, cucumber, chickpeas, and bright tahini.",
        ),
        (
            "citrus-salad",
            "grain-greens",
            "Citrus and fennel",
            850,
            ["vegan", "gluten-aware"],
            ["tree-nuts"],
            "Blood orange, shaved fennel, pistachio, and soft herbs.",
        ),
        (
            "roasted-carrot-grains",
            "grain-greens",
            "Roasted carrot grains",
            1190,
            ["vegetarian"],
            ["dairy"],
            "Roasted carrots, grains, labneh, and toasted seeds.",
        ),
        (
            "market-flatbread",
            "handhelds",
            "Market flatbread",
            1250,
            ["vegetarian", "shareable"],
            ["wheat-gluten", "dairy"],
            "Fire-kissed vegetables, feta, herb oil, and a blistered crust.",
        ),
        (
            "chicken-shawarma-wrap",
            "handhelds",
            "Chicken shawarma wrap",
            1320,
            ["halal-style"],
            ["wheat-gluten", "sesame"],
            "Chicken shawarma, pickles, herbs, and tahini in warm flatbread.",
        ),
        (
            "halloumi-pita",
            "handhelds",
            "Halloumi pita",
            1180,
            ["vegetarian"],
            ["wheat-gluten", "dairy"],
            "Halloumi, roasted peppers, herbs, and lemon in pita.",
        ),
        (
            "smoky-potatoes",
            "sides",
            "Smoky potatoes",
            520,
            ["vegan", "gluten-aware"],
            [],
            "Crisp potatoes with smoked paprika and herbs.",
        ),
        (
            "labneh-dip",
            "sides",
            "Labneh dip",
            580,
            ["vegetarian", "gluten-aware"],
            ["dairy"],
            "Strained yoghurt with olive oil, herbs, and sumac.",
        ),
        (
            "charred-broccoli",
            "sides",
            "Charred broccoli",
            610,
            ["vegan", "gluten-aware"],
            ["sesame"],
            "Charred broccoli with lemon, chilli, and sesame.",
        ),
        (
            "olive-oil-cake",
            "sweet-finish",
            "Olive oil cake",
            650,
            ["seasonal"],
            ["wheat-gluten", "dairy", "egg"],
            "Citrus olive oil cake with labneh cream and sea salt.",
        ),
        (
            "date-molasses-pudding",
            "sweet-finish",
            "Date molasses pudding",
            690,
            ["vegetarian"],
            ["dairy", "egg"],
            "Warm date pudding with molasses and softly whipped cream.",
        ),
        (
            "mint-lemonade",
            "drinks",
            "Mint lemonade",
            390,
            ["vegan", "gluten-aware"],
            [],
            "Fresh lemon, mint, and sparkling water.",
        ),
    ]
    colors = [(106, 86, 53), (194, 117, 46), (55, 101, 76), (143, 91, 54)]
    menu_items: dict[str, MenuItem] = {}
    for index, (
        slug,
        category_slug,
        name,
        price,
        tags,
        allergen_slugs,
        description,
    ) in enumerate(dish_specs):
        media = ensure_seed_media(
            session,
            settings.media_root,
            f"dish-{slug}",
            f"Development placeholder for {name}.",
            colors[index % len(colors)],
        )
        item = find_or_create(
            session,
            MenuItem,
            MenuItem.slug,
            slug,
            id=seeded_id(f"menu-item:{slug}"),
            category_id=categories[category_slug].id,
            media_id=media.id,
            name=name,
            slug=slug,
            description=description,
            ingredients=["See seeded menu details before ordering."],
            dietary_tags=tags,
            base_price_minor=price,
            currency_code="USD",
            publication_state=PublicationState.PUBLISHED,
        )
        menu_items[slug] = item
        find_or_create(
            session,
            MenuItemAvailability,
            MenuItemAvailability.id,
            seeded_id(f"availability:market-quarter:{slug}"),
            id=seeded_id(f"availability:market-quarter:{slug}"),
            location_id=location.id,
            menu_item_id=item.id,
            state=(
                AvailabilityState.TEMPORARILY_UNAVAILABLE
                if slug == "olive-oil-cake"
                else AvailabilityState.AVAILABLE
            ),
        )
        for allergen_slug in allergen_slugs:
            existing_link = session.scalar(
                select(MenuItemAllergen).where(
                    MenuItemAllergen.menu_item_id == item.id,
                    MenuItemAllergen.allergen_id == allergens[allergen_slug].id,
                )
            )
            if existing_link is None:
                session.add(
                    MenuItemAllergen(
                        id=seeded_id(f"item-allergen:{slug}:{allergen_slug}"),
                        menu_item_id=item.id,
                        allergen_id=allergens[allergen_slug].id,
                    )
                )

    for item_slug, group_name, minimum, maximum, options in [
        (
            "harissa-chicken-bowl",
            "Choose a base",
            1,
            1,
            [("Warm grains", 0), ("Greens", 0)],
        ),
        (
            "harissa-chicken-bowl",
            "Add heat",
            0,
            1,
            [("Mild", 0), ("Extra harissa", 75)],
        ),
        (
            "market-flatbread",
            "Choose a side",
            0,
            1,
            [("Citrus salad", 250), ("Smoky potatoes", 200)],
        ),
        (
            "chicken-shawarma-wrap",
            "Add a sauce",
            0,
            1,
            [("Tahini", 0), ("Garlic yoghurt", 0)],
        ),
    ]:
        item = menu_items[item_slug]
        option_group = session.scalar(
            select(OptionGroup).where(
                OptionGroup.menu_item_id == item.id, OptionGroup.name == group_name
            )
        )
        if option_group is None:
            option_group = OptionGroup(
                id=seeded_id(f"option-group:{item_slug}:{group_name}"),
                menu_item_id=item.id,
                name=group_name,
                minimum_selections=minimum,
                maximum_selections=maximum,
                display_order=0,
            )
            session.add(option_group)
            session.flush()
        for display_order, (name, price_delta_minor) in enumerate(options):
            existing_option = session.scalar(
                select(Option).where(
                    Option.option_group_id == option_group.id, Option.name == name
                )
            )
            if existing_option is None:
                session.add(
                    Option(
                        id=seeded_id(f"option:{item_slug}:{group_name}:{name}"),
                        option_group_id=option_group.id,
                        name=name,
                        price_delta_minor=price_delta_minor,
                        display_order=display_order,
                        is_available=True,
                    )
                )

    for display_order, (slug, name, description, item_slugs) in enumerate(
        [
            (
                "kitchen-favourites",
                "Kitchen favourites",
                "Reliable Nosh plates for the first visit.",
                ["harissa-chicken-bowl", "market-flatbread", "charred-lamb-kofta"],
            ),
            (
                "bright-lunch",
                "Bright lunch",
                "Fresh, quick plates for a midday table.",
                ["green-tahini-bowl", "citrus-salad", "mint-lemonade"],
            ),
            (
                "weekend-slow-down",
                "Weekend slow-down",
                "A longer, slower table with sides and dessert.",
                ["sumac-salmon", "labneh-dip", "olive-oil-cake"],
            ),
        ]
    ):
        collection = find_or_create(
            session,
            CuratedCollection,
            CuratedCollection.slug,
            slug,
            id=seeded_id(f"collection:{slug}"),
            name=name,
            slug=slug,
            description=description,
            display_order=display_order,
            publication_state=PublicationState.PUBLISHED,
        )
        for item_order, item_slug in enumerate(item_slugs):
            item = menu_items[item_slug]
            link = session.scalar(
                select(CollectionMenuItem).where(
                    CollectionMenuItem.collection_id == collection.id,
                    CollectionMenuItem.menu_item_id == item.id,
                )
            )
            if link is None:
                session.add(
                    CollectionMenuItem(
                        id=seeded_id(f"collection-item:{slug}:{item_slug}"),
                        collection_id=collection.id,
                        menu_item_id=item.id,
                        display_order=item_order,
                    )
                )

    home_specs = [
        (
            "hero",
            "A table worth coming home to.",
            "Thoughtful plates from one local kitchen.",
            "Explore today’s menu",
            "#menu",
            "hero",
            None,
        ),
        (
            "featured-dish",
            "Harissa chicken is on the fire.",
            "A featured dish with its full ingredients, availability, and notes ready "
            "to explore.",
            "View dish",
            "#menu",
            "dish-harissa-chicken-bowl",
            "harissa-chicken-bowl",
        ),
        (
            "kitchen-story",
            "A kitchen with a point of view.",
            "One fictional kitchen, one clear ordering path.",
            "Meet the kitchen",
            "#kitchen",
            "kitchen-story",
            None,
        ),
        (
            "location-callout",
            "Nosh on Market Street.",
            "Pickup and simulated delivery start from Market Quarter.",
            "Find the kitchen",
            "#location",
            "location",
            None,
        ),
    ]
    for display_order, (
        content_key,
        heading,
        copy,
        action_label,
        action_href,
        media_key,
        item_slug,
    ) in enumerate(home_specs):
        media = ensure_seed_media(
            session,
            settings.media_root,
            media_key,
            f"Development placeholder for Nosh {content_key.replace('-', ' ')}.",
            colors[display_order % len(colors)],
        )
        find_or_create(
            session,
            HomeContent,
            HomeContent.content_key,
            content_key,
            id=seeded_id(f"home:{content_key}"),
            content_key=content_key,
            heading=heading,
            supporting_copy=copy,
            action_label=action_label,
            action_href=action_href,
            media_id=media.id,
            menu_item_id=menu_items[item_slug].id if item_slug else None,
            display_order=display_order,
            publication_state=PublicationState.PUBLISHED,
        )

    session.commit()
