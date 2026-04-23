"""Browser-direct Cloudinary upload widget — Streamlit custom component."""

from __future__ import annotations

import os

import streamlit.components.v1 as components

_FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")

_component_func = components.declare_component(
    "cloudinary_uploader",
    path=_FRONTEND_DIR,
)


def cloudinary_uploader(
    cloud_name: str,
    api_key: str,
    signature: str,
    timestamp: int,
    folder: str,
    key: str | None = None,
) -> str | None:
    """Render the Cloudinary Upload Widget inside a Streamlit component iframe.

    The file travels directly from the user's browser to Cloudinary —
    it never passes through Streamlit's server or nginx, so there is no
    upload-size limit imposed by the hosting environment.

    Returns the ``secure_url`` of the uploaded asset once complete, or
    ``None`` if no upload has finished yet.
    """
    return _component_func(
        cloud_name=cloud_name,
        api_key=api_key,
        signature=signature,
        timestamp=timestamp,
        folder=folder,
        key=key,
        default=None,
    )
