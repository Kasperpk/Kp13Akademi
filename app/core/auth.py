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

    Tjekker først URL-parameteret ?player=felix, derefter session_state.
    Når en spiller er låst gemmes det i session_state så det overlever sideskift.
    """
    param = st.query_params.get("player", "")

    if param:
        for p in players:
            if p["id"] == param or p["name"].split()[0].lower() == param.lower():
                # Gem i session_state så det huskes ved sideskift
                st.session_state["locked_player_id"] = p["id"]
                return p["id"], True
        st.error(f"Spiller '{param}' ikke fundet. Kontakt Kasper.")
        st.stop()

    # Ingen URL-param — tjek session_state
    if "locked_player_id" in st.session_state:
        locked_id = st.session_state["locked_player_id"]
        if any(p["id"] == locked_id for p in players):
            return locked_id, True

    return None, False


def player_selector(players: list[dict]) -> str:
    """Vis spillervælger tilpasset adgangsniveau.

    - Låst (URL-parameter eller session): vis kun spillerens navn, ingen vælger.
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
