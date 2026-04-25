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
    add_player_session, get_player_sessions, delete_player_session,
    get_preferred_days, set_preferred_days, get_week_training_minutes,
)
from core.epm import get_player_profile, identify_gaps, identify_strengths
from core.elm import generate_weekly_plan_danish
from core.recommender import recommend_for_gaps
from core.theme import apply_theme, card, focus_badge
from core.auth import player_selector, get_player_id_from_url

st.set_page_config(page_title="Ugentlig Plan – KP13", layout="wide")
apply_theme()

_ALL_DAYS = ["Mandag", "Tirsdag", "Onsdag", "Torsdag", "Fredag", "Lørdag", "Søndag"]
_SHORT_DAYS = ["Man", "Tir", "Ons", "Tor", "Fre", "Lør", "Søn"]

_DAYS = {
    2: ["Mandag", "Torsdag"],
    3: ["Mandag", "Onsdag", "Fredag"],
    4: ["Mandag", "Tirsdag", "Torsdag", "Lørdag"],
}

_SESSION_TYPES = [
    "Hold Træning",
    "Individuel Træning KP13 Akademi",
    "Styrke Træning",
    "Teknisk Træning",
    "Taktisk Træning",
    "Agilty Træning",
    "Løb / Kondition",
    "Kamp",
    "Andet",
]

_SESSION_COLORS = {
    "Hold Træning":    "#93C5FD",
    "1-mod-1 (KP13)": "#3B82F6",
    "Individuel Træning KP13 Akademi": "#3B82F6",
    "Styrke Træning":  "#FCA5A5",
    "Teknisk Træning": "#C4B5FD",
    "Taktisk Træning": "#6EE7B7",
    "Agilty Træning":  "#FDE68A",
    "Løb / Kondition": "#A5F3FC",
    "Kamp":            "#FBB6CE",
    "Andet":           "#D1D5DB",
}

_AKADEMI_COLOR      = "#3B82F6"
_AKADEMI_DONE_COLOR = "#10B981"


def _day_card(
    label: str,
    color: str,
    extra: str = "",
    added_by: str = "coach",
    duration_min: int | None = None,
    badge: str = "",
) -> str:
    text_color = "#1a1a1a" if color not in ("#3B82F6", "#10B981") else "#ffffff"
    # Coach sessions: solid left accent border; player sessions: dashed border
    if added_by == "coach":
        border = f"border-left:3px solid rgba(0,0,0,0.25);"
        tag = '<span style="font-size:0.6rem;background:rgba(0,0,0,0.18);border-radius:3px;padding:1px 4px;margin-left:4px;">KP13</span>' if not badge else f'<span style="font-size:0.6rem;background:rgba(0,0,0,0.18);border-radius:3px;padding:1px 4px;margin-left:4px;">{badge}</span>'
    else:
        border = "border:1px dashed rgba(0,0,0,0.3);"
        tag = '<span style="font-size:0.6rem;background:rgba(0,0,0,0.12);border-radius:3px;padding:1px 4px;margin-left:4px;">Selv</span>'
    dur = f'<span style="font-size:0.6rem;opacity:0.8;"> · {duration_min} min</span>' if duration_min else ""
    return (
        f'<div style="background:{color};border-radius:6px;padding:5px 7px;'
        f'margin-bottom:5px;font-size:0.72rem;color:{text_color};line-height:1.4;{border}">'
        f'{label}{tag}{dur}{extra}</div>'
    )


# ---- player selector ---------------------------------------------------------

players = get_players()
if not players:
    st.info("Ingen spillere registreret endnu.")
    st.stop()

selected_id = player_selector(players)
_, is_player = get_player_id_from_url(players)

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
sessions_per_week_saved = (plan_data.get("sessions_per_week") or 3) if plan_data else 3
planned_days = get_preferred_days(selected_id, fallback_sessions=sessions_per_week_saved)

# ---- TRÆNER-SEKTION: indstillinger og generering ----------------------------

if not is_player:
    col_a, col_b = st.columns([3, 1])
    with col_a:
        existing_goals = player.get("goals", "") or ""
        player_goals = st.text_area(
            "Spillerens mål og fokus",
            value=existing_goals,
            placeholder=f"Fx: {player['name'].split()[0]} vil forbedre sit svage ben og være mere modig i 1v1 situationer...",
            height=80,
        )
        if player_goals != existing_goals:
            update_player_goals(selected_id, player_goals)
    with col_b:
        st.markdown("**Træningsdage**")
        chosen_days = []
        for day in _ALL_DAYS:
            default = day in planned_days
            if st.checkbox(day[:3], value=default, key=f"day_{day}"):
                chosen_days.append(day)
        if not chosen_days:
            st.warning("Vælg mindst én dag.")
        elif chosen_days != planned_days:
            set_preferred_days(selected_id, chosen_days)
            planned_days = chosen_days

    gaps = identify_gaps(selected_id, top_n=5)
    strengths = identify_strengths(selected_id, top_n=3)

    if gaps:
        badges_html = " ".join(focus_badge(f"{g['name']} {g['score']:.1f}") for g in gaps[:3])
        st.markdown(badges_html, unsafe_allow_html=True)
        st.markdown("")

    if not plan_data or not plan_data.get("content"):
        if not ANTHROPIC_API_KEY:
            st.warning("Tilføj din Anthropic API-nøgle i .env for at generere planer.")
            st.stop()
        st.markdown(
            card(f"<p style='margin:0'>Ingen plan for denne uge endnu for {player['name']}.</p>"),
            unsafe_allow_html=True,
        )
        if st.button("Generer ugentlig træningsplan", type="primary"):
            if not chosen_days:
                st.error("Vælg mindst én træningsdag.")
                st.stop()
            with st.spinner("Bygger træningsplan..."):
                try:
                    recent = get_observations(selected_id, limit=5)
                    recommended = recommend_for_gaps(gaps, max_results=20, age=age_int, max_players=2)
                    plan_md = generate_weekly_plan_danish(
                        player=player, gaps=gaps, strengths=strengths,
                        recent_observations=recent, chosen_days=chosen_days,
                        available_exercises=recommended,
                        player_goals=player.get("goals", ""),
                    )
                    save_ugentlig_plan(selected_id, week_start, plan_md, len(chosen_days))
                    st.rerun()
                except Exception as e:
                    st.error(f"Generering fejlede: {e}")
        st.stop()

    st.markdown("---")

# ---- ingen plan for spiller --------------------------------------------------

if not plan_data or not plan_data.get("content"):
    st.info("Kasper har ikke genereret en plan for denne uge endnu. Kom tilbage snart!")
    st.stop()

# ---- UGENTLIG KALENDER -------------------------------------------------------

st.markdown("### Ugens Kalender")
st.markdown("""
<style>
div[data-testid="column"] div[data-testid="stButton"] > button[data-testid="baseButton-primary"] {
    font-size: 0.7rem !important;
    padding: 3px 6px !important;
    line-height: 1.3 !important;
}
</style>
""", unsafe_allow_html=True)

completions = get_completions(selected_id, week_start)
player_sessions_by_day = get_player_sessions(selected_id, week_start)
training_mins = get_week_training_minutes(selected_id, week_start)

cols = st.columns(7)
for i, (day, short) in enumerate(zip(_ALL_DAYS, _SHORT_DAYS)):
    with cols[i]:
        st.markdown(f"**{short}**")

        # Akademi session block
        if day in planned_days:
            if day in completions:
                st.markdown(_day_card("✓ Akademi", _AKADEMI_DONE_COLOR, badge="KP13"), unsafe_allow_html=True)
            else:
                st.markdown(_day_card("📚 Akademi", _AKADEMI_COLOR, badge="KP13"), unsafe_allow_html=True)
                if st.button("Gennemført ✓", key=f"done_{day}", use_container_width=True,
                             help="Marker akademi-session som gennemført",
                             type="primary"):
                    mark_session_complete(selected_id, week_start, day, "")
                    st.rerun()

        # Coach- and player-added sessions
        for sess in player_sessions_by_day.get(day, []):
            color = _SESSION_COLORS.get(sess["session_type"], "#D1D5DB")
            label = sess["session_type"]
            time_str = f"<br><span style='font-size:0.6rem'>{sess['time_start']}</span>" if sess.get("time_start") else ""
            st.markdown(
                _day_card(label, color, time_str,
                          added_by=sess.get("added_by", "coach"),
                          duration_min=sess.get("duration_min")),
                unsafe_allow_html=True,
            )
            if st.button("Fjern", key=f"del_{sess['id']}", use_container_width=True,
                         help="Fjern denne træning"):
                delete_player_session(sess["id"])
                st.rerun()

# ---- UGENTLIG TRÆNINGSTIMER --------------------------------------------------

total = training_mins["total"]
coach_min = training_mins["coach"]
player_min = training_mins["player"]
if total > 0:
    def _fmt(m: int) -> str:
        return f"{m // 60}t {m % 60}m" if m >= 60 else f"{m}m"
    cols_summary = st.columns(3)
    with cols_summary[0]:
        st.metric("Total denne uge", _fmt(total))
    with cols_summary[1]:
        st.metric("KP13-sessioner", _fmt(coach_min))
    with cols_summary[2]:
        st.metric("Ekstra (selvtræning)", _fmt(player_min))

# ---- TILFØJ TRÆNING ----------------------------------------------------------

st.markdown("")
with st.expander("＋ Tilføj træning til ugen"):
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        add_day = st.selectbox("Dag", _ALL_DAYS, key="add_day")
    with c2:
        add_type = st.selectbox("Type", _SESSION_TYPES, key="add_type")
    with c3:
        add_time = st.text_input("Tidspunkt", placeholder="14:00", key="add_time")
    with c4:
        add_duration = st.number_input("Minutter", min_value=0, max_value=300, step=5, value=60, key="add_duration")
    add_notes = st.text_input("Noter (valgfrit)", placeholder="Fx: 1-mod-1 i Randers Idrætspark", key="add_notes")
    add_by_coach = not is_player  # Streamlit = coach; player view shouldn't show this normally
    if st.button("Tilføj træning", type="primary", key="add_session_btn"):
        add_player_session(
            selected_id, week_start, add_day, add_type,
            add_time.strip(), add_notes.strip(),
            duration_min=int(add_duration) if add_duration else None,
            added_by="coach" if add_by_coach else "player",
        )
        st.rerun()

# ---- PLAN DETALJER -----------------------------------------------------------

st.markdown("---")
with st.expander("📋 Ugens træningsplan (detaljer)", expanded=True):
    st.markdown(plan_data["content"])

# ---- TRÆNER: regenerer knap --------------------------------------------------

if not is_player:
    st.markdown("---")
    if st.button("Generer ny plan", help="Overskriver den eksisterende plan for denne uge"):
        save_ugentlig_plan(selected_id, week_start, "", len(planned_days))
        st.rerun()
