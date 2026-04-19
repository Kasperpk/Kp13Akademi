"""Adgangskontrol — træner-password og spiller-URL."""

from __future__ import annotations

import streamlit as st

from .config import COACH_PASSWORD


def require_coach() -> None:
    """Stop siden og vis password-felt hvis træneren ikke er logget ind."""
    if st.session_state.get("coach_auth"):
        return

    st.markdown("### Træner-login")
    pwd = st.text_input("Password", type="password", key="coach_pwd_input")
    if st.button("Log ind", type="primary"):
        if pwd == COACH_PASSWORD:
            st.session_state.coach_auth = True
            st.rerun()
        else:
            st.error("Forkert password.")
    st.stop()


def get_player_id_from_url(players: list[dict]) -> tuple[str | None, bool]:
    """Returner (player_id, locked).

    Hvis ?player=felix er i URL'en, låses visningen til den spiller (locked=True).
    Ellers returneres None og locked=False (træner-tilstand med fri vælger).
    """
    param = st.query_params.get("player", "")
    if param:
        # Find matching player by id or by first name (lowercase)
        for p in players:
            if p["id"] == param or p["name"].split()[0].lower() == param.lower():
                return p["id"], True
        st.error(f"Spiller '{param}' ikke fundet. Kontakt Kasper.")
        st.stop()
    return None, False


def player_selector(players: list[dict]) -> str:
    """Vis spillervælger tilpasset adgangsniveau.

    - Låst (URL-parameter): vis kun spillerens navn, ingen vælger.
    - Fri (træner): vis radio-vælger med alle spillere.
    """
    player_id, locked = get_player_id_from_url(players)

    if locked:
        player = next(p for p in players if p["id"] == player_id)
        st.sidebar.markdown(f"**{player['name']}**")
        return player_id

    # Træner-tilstand: vis alle spillere
    player_options = {p["id"]: p["name"] for p in players}
    return st.sidebar.radio(
        "Spiller",
        options=[p["id"] for p in players],
        format_func=lambda pid: player_options[pid],
    )
