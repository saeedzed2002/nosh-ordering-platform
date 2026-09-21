from __future__ import annotations

import hashlib
import warnings
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from uuid import UUID, uuid4

from PIL import Image, ImageOps, UnidentifiedImageError

ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ("JPEG", "jpg"),
    "image/png": ("PNG", "png"),
    "image/webp": ("WEBP", "webp"),
}
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_IMAGE_DIMENSION = 4096
MAX_IMAGE_PIXELS = MAX_IMAGE_DIMENSION**2
THUMBNAIL_SIZE = (480, 480)


class MediaValidationError(ValueError):
    pass


@dataclass(frozen=True)
class ValidatedImage:
    payload: bytes
    mime_type: str
    file_extension: str
    width: int
    height: int
    checksum_sha256: str


@dataclass(frozen=True)
class StoredImage:
    id: UUID
    original_path: str
    thumbnail_path: str
    validated: ValidatedImage


def validate_image_payload(payload: bytes, mime_type: str | None) -> ValidatedImage:
    if mime_type not in ALLOWED_IMAGE_TYPES:
        raise MediaValidationError("Only JPEG, PNG, and WebP images are supported.")
    if not payload:
        raise MediaValidationError("The image file is empty.")
    if len(payload) > MAX_IMAGE_BYTES:
        raise MediaValidationError("The image must be 5 MB or smaller.")

    expected_format, file_extension = ALLOWED_IMAGE_TYPES[mime_type]
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(payload)) as opened_image:
                opened_image.verify()
            with Image.open(BytesIO(payload)) as opened_image:
                width, height = opened_image.size
                actual_format = opened_image.format
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise MediaValidationError("The image dimensions are too large.") from None
    except (OSError, UnidentifiedImageError):
        raise MediaValidationError("The file is not a valid image.") from None

    if actual_format != expected_format:
        raise MediaValidationError("The declared image type does not match the file.")
    if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
        raise MediaValidationError("The image dimensions must not exceed 4096 pixels.")
    if width * height > MAX_IMAGE_PIXELS:
        raise MediaValidationError("The image contains too many pixels.")

    return ValidatedImage(
        payload=payload,
        mime_type=mime_type,
        file_extension=file_extension,
        width=width,
        height=height,
        checksum_sha256=hashlib.sha256(payload).hexdigest(),
    )


def persist_image(
    media_root: Path,
    original_filename: str,
    validated_image: ValidatedImage,
    *,
    focal_point_x: int = 50,
    focal_point_y: int = 50,
    media_id: UUID | None = None,
) -> StoredImage:
    resolved_id = media_id or uuid4()
    original_relative_path = Path("originals") / (
        f"{resolved_id}.{validated_image.file_extension}"
    )
    thumbnail_relative_path = Path("thumbnails") / f"{resolved_id}.webp"
    original_path = media_root / original_relative_path
    thumbnail_path = media_root / thumbnail_relative_path
    original_path.parent.mkdir(parents=True, exist_ok=True)
    thumbnail_path.parent.mkdir(parents=True, exist_ok=True)

    original_path.write_bytes(validated_image.payload)
    try:
        with Image.open(BytesIO(validated_image.payload)) as opened_image:
            write_thumbnail(
                opened_image,
                thumbnail_path,
                focal_point_x=focal_point_x,
                focal_point_y=focal_point_y,
            )
    except OSError:
        original_path.unlink(missing_ok=True)
        thumbnail_path.unlink(missing_ok=True)
        raise

    return StoredImage(
        id=resolved_id,
        original_path=original_relative_path.as_posix(),
        thumbnail_path=thumbnail_relative_path.as_posix(),
        validated=validated_image,
    )


def remove_stored_image(media_root: Path, stored_image: StoredImage) -> None:
    (media_root / stored_image.original_path).unlink(missing_ok=True)
    (media_root / stored_image.thumbnail_path).unlink(missing_ok=True)


def crop_to_focal_square(
    image: Image.Image, *, focal_point_x: int, focal_point_y: int
) -> Image.Image:
    normalized_image = ImageOps.exif_transpose(image).convert("RGB")
    width, height = normalized_image.size
    side = min(width, height)
    focus_x = width * focal_point_x / 100
    focus_y = height * focal_point_y / 100
    left = min(max(round(focus_x - side / 2), 0), width - side)
    top = min(max(round(focus_y - side / 2), 0), height - side)
    return normalized_image.crop((left, top, left + side, top + side))


def write_thumbnail(
    image: Image.Image,
    thumbnail_path: Path,
    *,
    focal_point_x: int,
    focal_point_y: int,
) -> None:
    thumbnail = crop_to_focal_square(
        image,
        focal_point_x=focal_point_x,
        focal_point_y=focal_point_y,
    )
    thumbnail.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
    temporary_path = thumbnail_path.with_suffix(".tmp")
    try:
        thumbnail.save(temporary_path, format="WEBP", quality=80, method=6)
        temporary_path.replace(thumbnail_path)
    finally:
        temporary_path.unlink(missing_ok=True)


def regenerate_thumbnail(
    media_root: Path,
    *,
    original_path: str,
    thumbnail_path: str,
    focal_point_x: int,
    focal_point_y: int,
) -> None:
    with Image.open(media_root / original_path) as opened_image:
        write_thumbnail(
            opened_image,
            media_root / thumbnail_path,
            focal_point_x=focal_point_x,
            focal_point_y=focal_point_y,
        )


def create_development_seed_image(
    color: tuple[int, int, int], marker: bytes = b""
) -> bytes:
    image = Image.new("RGB", (1200, 800), color)
    for index, value in enumerate(marker[:32]):
        image.putpixel((index, 0), (value, (value + 85) % 256, (value + 170) % 256))
    output = BytesIO()
    image.save(output, format="WEBP", quality=80, method=6)
    return output.getvalue()
