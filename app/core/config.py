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
DB_PATH = PROJECT_ROOT / "app" / "data" / "kp13.db"
EXERCISES_DIR = PROJECT_ROOT / "generator" / "exercises"
TEMPLATES_DIR = PROJECT_ROOT / "generator" / "templates"
HISTORY_FILE = PROJECT_ROOT / "generator" / "history" / "log.json"

# --- Claude / Anthropic -------------------------------------------------------
# Support both local .env and Streamlit Cloud secrets
def _get_secret(key: str, default: str = "") -> str:
    """Read from env var first, then fall back to Streamlit secrets."""
    val = os.getenv(key, "")
    if val:
        return val
    try:
        import streamlit as st
        return st.secrets.get(key, default)
    except Exception:
        return default

ANTHROPIC_API_KEY: str = _get_secret("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL: str = _get_secret("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")

# --- EPM tuning ---------------------------------------------------------------
EPM_ALPHA: float = float(os.getenv("EPM_ALPHA", "0.3"))  # EMA learning rate
EPM_MIN_SCORE: float = 1.0
EPM_MAX_SCORE: float = 10.0

# --- App ----------------------------------------------------------------------
APP_TITLE: str = "KP13 Akademi"
