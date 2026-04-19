"""Ugentlig Træningsplan — vis plan og log gennemførelse."""

import sys
from pathlib import Path
from datetime import date, timedelta

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st

from core.config import ANTHROPIC_API_KEY
from core.database import (
    get_players, get_observations, get_ugentlig_plan,
    save_ugentlig_plan, update_player_goals,
    mark_session_complete, get_completions,
)
from core.epm import get_player_profile, identify_gaps, identify_strengths
from core.elm import generate_weekly_plan_danish
from core.recommender import recommend_for_gaps
from core.theme import apply_theme, card, focus_badge
from core.auth import player_selector, get_player_id_from_url

st.set_page_config(page_title="Ugentlig Plan – KP13", layout="wide")
apply_theme()

_DAYS = {
    2: ["Mandag", "Torsdag"],
    3: ["Mandag", "Onsdag", "Fredag"],
    4: ["Mandag", "Tirsdag", "Torsdag", "Lørdag"],
}

# ---- player selector ---------------------------------------------------------

players = get_players()
if not players:
    st.info("Ingen spillere registreret endnu.")
    st.stop()

selected_id = player_selector(players)
_, is_player = get_player_id_from_url(players)  # True = spiller/forælder adgang

profile = get_player_profile(selected_id)
if not profile:
    st.error("Spiller ikke fundet.")
    st.stop()

player = profile["player"]
age_raw = player.get("age_group", "U9")
try:
    age_int = int("".join(c for c in age_raw if c.isdigit()) or "9")
except ValueError:
    age_int = 9

# ---- header ------------------------------------------------------------------

st.title("Ugentlig Træningsplan")
st.caption(f"{player['name']} · {age_raw} · {player.get('position', '')} · {player.get('club', '')}")

# ---- week selector -----------------------------------------------------------

today = date.today()
monday = today - timedelta(days=today.weekday())

col1, col2 = st.columns([2, 1])
with col2:
    week_offset = st.selectbox(
        "Uge",
        options=[0, 1, -1],
        format_func=lambda x: {0: "Denne uge", 1: "Næste uge", -1: "Forrige uge"}[x],
    )
week_start = (monday + timedelta(weeks=week_offset)).isoformat()
_d = monday + timedelta(weeks=week_offset)
week_label = f"{_d.day}. {_d.strftime('%B %Y')}"

with col1:
    st.markdown(f"Uge starter: **{week_label}**")

st.markdown("---")

# ---- hent eksisterende plan --------------------------------------------------

plan_data = get_ugentlig_plan(selected_id, week_start)

# ---- TRÆNER-SEKTION: indstillinger og generering ----------------------------

if not is_player:
    col_a, col_b = st.columns([3, 1])
    with col_a:
        existing_goals = player.get("goals", "") or ""
        player_goals = st.text_area(
            "Spillerens mål og fokus",
            value=existing_goals,
            placeholder=f"Fx: {player['name'].split()[0]} vil forbedre sit svage ben og være mere modig i 1v1 situationer...",
            height=90,
        )
        if player_goals != existing_goals:
            update_player_goals(selected_id, player_goals)
    with col_b:
        sessions_per_week = st.selectbox("Sessions pr. uge", options=[2, 3, 4], index=1)

    gaps = identify_gaps(selected_id, top_n=5)
    strengths = identify_strengths(selected_id, top_n=3)

    if gaps:
        badges_html = " ".join(focus_badge(f"{g['name']} {g['score']:.1f}") for g in gaps[:3])
        st.markdown(badges_html, unsafe_allow_html=True)
        st.markdown("")

    if not plan_data:
        if not ANTHROPIC_API_KEY:
            st.warning("Tilføj din Anthropic API-nøgle i .env for at generere planer.")
            st.stop()
        st.markdown(
            card(f"<p style='margin:0'>Ingen plan for denne uge endnu for {player['name']}.</p>"),
            unsafe_allow_html=True,
        )
        if st.button("Generer ugentlig træningsplan", type="primary"):
            with st.spinner("Bygger træningsplan..."):
                try:
                    recent = get_observations(selected_id, limit=5)
                    recommended = recommend_for_gaps(gaps, max_results=20, age=age_int, max_players=2)
                    plan_md = generate_weekly_plan_danish(
                        player=player, gaps=gaps, strengths=strengths,
                        recent_observations=recent, sessions_per_week=sessions_per_week,
                        available_exercises=recommended,
                        player_goals=player.get("goals", ""),
                    )
                    save_ugentlig_plan(selected_id, week_start, plan_md, sessions_per_week)
                    st.rerun()
                except Exception as e:
                    st.error(f"Generering fejlede: {e}")
        st.stop()

    st.markdown("---")

# ---- VIS PLAN ---------------------------------------------------------------

if not plan_data:
    st.info("Kasper har ikke genereret en plan for denne uge endnu. Kom tilbage snart!")
    st.stop()

st.markdown(plan_data["content"])
sessions_per_week_saved = plan_data.get("sessions_per_week") or 3
planned_days = _DAYS.get(sessions_per_week_saved, _DAYS[3])

# ---- GENNEMFØRELSES-TRACKER -------------------------------------------------

st.markdown("---")
st.markdown("### Ugens Træninger")
st.caption("Tryk 'Gennemført' når du har lavet sessionen.")

completions = get_completions(selected_id, week_start)

cols = st.columns(len(planned_days))
for i, day in enumerate(planned_days):
    with cols[i]:
        if day in completions:
            st.success(f"✓ {day}")
            feedback = completions[day]
            if feedback:
                st.caption(feedback)
        else:
            st.markdown(f"**{day}**")
            feedback = st.selectbox(
                "Hvordan gik det?",
                options=["Fantastisk", "Godt", "Hårdt", "Fik ikke gennemført"],
                key=f"fb_{day}",
                label_visibility="collapsed",
            )
            if st.button("Gennemført ✓", key=f"done_{day}", type="primary"):
                mark_session_complete(selected_id, week_start, day, feedback)
                st.rerun()

# ---- TRÆNER: regenerer knap --------------------------------------------------

if not is_player:
    st.markdown("---")
    if st.button("Generer ny plan", help="Overskriver den eksisterende plan for denne uge"):
        save_ugentlig_plan(selected_id, week_start, "", sessions_per_week_saved)
        st.rerun()
