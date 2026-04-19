"""KP13 Akademi – Today's Training."""

import sys
from pathlib import Path
from datetime import date

# Ensure project root is on path for generator imports
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st

from core.config import APP_TITLE, ANTHROPIC_API_KEY
from core.database import init_db, get_players, get_observations, get_daily_plan, save_daily_plan, mark_plan_completed
from core.epm import get_player_profile, identify_gaps, identify_strengths, DIM_BY_KEY
from core.elm import generate_daily_plan
from core.recommender import recommend_for_gaps
from core.theme import apply_theme, focus_badge, card, completed_badge

# ---- page config -------------------------------------------------------------

st.set_page_config(
    page_title=APP_TITLE,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---- initialise database on first run ----------------------------------------

init_db()

# Auto-seed if database is empty (first run / fresh deploy)
from core.database import get_players as _check_players
if not _check_players():
    from seed import seed
    seed()

# ---- theme -------------------------------------------------------------------

apply_theme()

# ---- sidebar: player selector -----------------------------------------------

st.sidebar.title(APP_TITLE)
st.sidebar.caption("Spillerudviklings-system")
st.sidebar.divider()

players = get_players()
if not players:
    st.title("KP13 Akademi")
    st.info("Ingen spillere registreret endnu. Tilføj din første spiller fra spilleroversigten.")
    st.stop()

player_options = {p["id"]: p["name"] for p in players}
selected_id = st.sidebar.radio(
    "Spiller",
    options=[p["id"] for p in players],
    format_func=lambda pid: player_options[pid],
)

profile = get_player_profile(selected_id)
if not profile:
    st.error("Player not found.")
    st.stop()

player = profile["player"]
today = date.today().isoformat()

# ---- greeting ----------------------------------------------------------------

import datetime
hour = datetime.datetime.now().hour
if hour < 12:
    greeting = "Godmorgen"
elif hour < 17:
    greeting = "Godeftermiddag"
else:
    greeting = "Godaften"

st.title(f"{greeting}, {player['name']}")

# ---- current focus -----------------------------------------------------------

gaps = identify_gaps(selected_id, top_n=3)
strengths = identify_strengths(selected_id, top_n=3)

if gaps:
    badges_html = " ".join(focus_badge(g["name"]) for g in gaps[:2])
    st.markdown(f"Dagens fokus &nbsp; {badges_html}", unsafe_allow_html=True)

st.markdown("")

# ---- today's plan ------------------------------------------------------------

existing_plan = get_daily_plan(selected_id, today)

if existing_plan and existing_plan.get("plan_content"):
    plan_content = existing_plan["plan_content"]
    plan_md = plan_content.get("markdown", plan_content) if isinstance(plan_content, dict) else plan_content

    if existing_plan.get("completed"):
        st.markdown(completed_badge(), unsafe_allow_html=True)
        st.markdown("")

    # Render the plan
    st.markdown(plan_md)

    st.divider()

    # Completion tracking
    if not existing_plan.get("completed"):
        st.markdown("### Hvordan gik det?")
        feedback_option = st.radio(
            "Vurder din session",
            options=["Fantastisk", "Godt", "Hårdt", "Fik ikke gennemført"],
            horizontal=True,
            label_visibility="collapsed",
        )
        feedback_text = st.text_input(
            "Noget at tilføje?",
            placeholder="Valgfrit — hvad var nemt, hvad var svært",
        )
        if st.button("Marker session som gennemført", type="primary"):
            full_feedback = feedback_option
            if feedback_text:
                full_feedback += f" — {feedback_text}"
            mark_plan_completed(existing_plan["id"], full_feedback)
            st.rerun()
    else:
        if existing_plan.get("player_feedback"):
            st.markdown(f'<p class="kp-muted">Feedback: {existing_plan["player_feedback"]}</p>', unsafe_allow_html=True)

else:
    # No plan yet — offer to generate
    st.markdown(
        card(
            "<h3 style='margin:0 0 0.5rem 0;color:#F9FAFB'>Ingen session planlagt for i dag</h3>"
            "<p style='color:#9CA3AF;margin:0'>Generer en personlig træningssession baseret på din aktuelle udviklingsprofil.</p>",
        ),
        unsafe_allow_html=True,
    )

    if not ANTHROPIC_API_KEY:
        st.warning("Tilføj din API-nøgle i .env for at generere træningsplaner.")
        st.stop()

    if st.button("Generer dagens session", type="primary"):
        with st.spinner("Bygger din session..."):
            try:
                recent = get_observations(selected_id, limit=5)
                recommended = recommend_for_gaps(gaps, max_results=8, age=9, max_players=2)

                plan_md = generate_daily_plan(
                    player_profile=profile,
                    gaps=gaps,
                    strengths=strengths,
                    recent_sessions=recent,
                    available_exercises=recommended,
                )

                focus_dim = gaps[0]["key"] if gaps else "general"
                save_daily_plan(
                    plan_date=today,
                    player_id=selected_id,
                    focus_dimension=focus_dim,
                    plan_content={"markdown": plan_md},
                )
                st.rerun()
            except Exception as e:
                st.error(f"Generering fejlede: {e}")

# ---- why this matters (connects today to development) ------------------------

if gaps:
    st.divider()
    st.markdown("### Hvorfor dette er vigtigt")
    for g in gaps[:2]:
        meta = DIM_BY_KEY[g["key"]]
        st.markdown(f"**{meta.name}** — {meta.description}")

