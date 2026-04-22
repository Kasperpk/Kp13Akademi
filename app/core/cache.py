"""Streamlit-side cache wrappers for hot reads.

Only imported by Streamlit pages — no FastAPI side-effects. The wrappers
take a TTL because the underlying data does change (coach edits scores,
new sessions get logged); short TTLs keep the data fresh while killing
the per-rerun re-fetch storm.

After a coach action that mutates a player's data, call the matching
``.clear()`` method (e.g. ``cached_player_profile.clear()``) so the next
read sees the new value.
"""

from __future__ import annotations

import streamlit as st

from . import database as db
from .epm import get_player_profile, identify_gaps, identify_strengths


@st.cache_data(ttl=300)
def cached_players() -> list[dict]:
    return db.get_players()


@st.cache_data(ttl=60)
def cached_player_profile(player_id: str) -> dict:
    return get_player_profile(player_id)


@st.cache_data(ttl=60)
def cached_gaps(player_id: str, top_n: int = 3) -> list[dict]:
    return identify_gaps(player_id, top_n=top_n)


@st.cache_data(ttl=60)
def cached_strengths(player_id: str, top_n: int = 3) -> list[dict]:
    return identify_strengths(player_id, top_n=top_n)


def invalidate_player(player_id: str) -> None:
    """Clear all per-player caches after a mutation. Call from save handlers."""
    cached_player_profile.clear()
    cached_gaps.clear()
    cached_strengths.clear()
