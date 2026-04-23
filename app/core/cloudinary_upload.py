"""Cloudinary media upload helpers for video/image journey content."""

from __future__ import annotations

import os

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


def _resource_type_from_filename(filename: str) -> str:
    ext = os.path.splitext(filename.lower())[1]
    image_exts = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic", ".heif"}
    video_exts = {".mp4", ".mov", ".avi", ".mkv", ".m4v", ".webm"}
    if ext in image_exts:
        return "image"
    if ext in video_exts:
        return "video"
    return "raw"


def upload_media(file_bytes: bytes, player_id: str, filename: str) -> str:
    """Upload a media file and return the secure URL.

    Uses chunked upload for larger files to reduce timeouts.
    """
    _configure()
    resource_type = _resource_type_from_filename(filename)
    result = cloudinary.uploader.upload(
        file_bytes,
        resource_type=resource_type,
        folder=f"kp13/{player_id}",
        use_filename=True,
        unique_filename=True,
        overwrite=False,
        chunk_size=6_000_000,
    )
    return result["secure_url"]


def upload_video(file_bytes: bytes, player_id: str, filename: str) -> str:
    """Backward-compatible alias for existing imports."""
    return upload_media(file_bytes=file_bytes, player_id=player_id, filename=filename)


def is_configured() -> bool:
    return bool(CLOUDINARY_CLOUD_NAME and CLOUDINARY_API_KEY and CLOUDINARY_API_SECRET)
