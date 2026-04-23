"""Application settings loaded from environment / .env file."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root
_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(_ENV_PATH)

# --- Paths -------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXERCISES_DIR = PROJECT_ROOT / "generator" / "exercises"
TEMPLATES_DIR = PROJECT_ROOT / "generator" / "templates"
HISTORY_FILE = PROJECT_ROOT / "generator" / "history" / "log.json"


# --- Secrets helper (env var first, Streamlit secrets fallback) --------------
def _get_secret(key: str, default: str = "") -> str:
    val = os.getenv(key, "")
    if val:
        return val
    try:
        import streamlit as st
        return st.secrets.get(key, default)
    except Exception:
        return default


# --- Database ----------------------------------------------------------------
# Postgres connection string. Required. Example:
#   postgresql://user:pass@host.neon.tech/dbname?sslmode=require
DATABASE_URL: str = _get_secret("DATABASE_URL")

# Auto-seed the DB on first run when players table is empty.
AUTO_SEED_ON_EMPTY_DB: bool = _get_secret("AUTO_SEED_ON_EMPTY_DB", "false").lower() in {
    "1", "true", "yes", "on"
}

# --- Claude / Anthropic -------------------------------------------------------

ANTHROPIC_API_KEY: str = _get_secret("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL: str = _get_secret("ANTHROPIC_MODEL", "claude-sonnet-4-6")
COACH_PASSWORD: str = _get_secret("COACH_PASSWORD", "kp13")

CLOUDINARY_CLOUD_NAME: str = _get_secret("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY: str = _get_secret("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET: str = _get_secret("CLOUDINARY_API_SECRET")
CLOUDINARY_UPLOAD_PRESET: str = _get_secret("CLOUDINARY_UPLOAD_PRESET")

# --- EPM tuning ---------------------------------------------------------------
EPM_ALPHA: float = float(os.getenv("EPM_ALPHA", "0.3"))  # EMA learning rate
EPM_MIN_SCORE: float = 1.0
EPM_MAX_SCORE: float = 10.0

# --- App ----------------------------------------------------------------------
APP_TITLE: str = "KP13 Akademi"
