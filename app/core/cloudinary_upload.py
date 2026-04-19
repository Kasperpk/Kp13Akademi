"""Cloudinary video/image upload helper."""

from __future__ import annotations

import cloudinary
import cloudinary.uploader

from .config import CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET


def _configure() -> None:
    cloudinary.config(
        cloud_name=CLOUDINARY_CLOUD_NAME,
        api_key=CLOUDINARY_API_KEY,
        api_secret=CLOUDINARY_API_SECRET,
        secure=True,
    )


def upload_video(file_bytes: bytes, player_id: str, filename: str) -> str:
    """Upload a video file and return the secure URL."""
    _configure()
    result = cloudinary.uploader.upload(
        file_bytes,
        resource_type="video",
        folder=f"kp13/{player_id}",
        use_filename=True,
        unique_filename=True,
        overwrite=False,
    )
    return result["secure_url"]


def is_configured() -> bool:
    return bool(CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET)
