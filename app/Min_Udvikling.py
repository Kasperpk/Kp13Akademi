"""Min udvikling — landing. Træningstimer + dagens AI-genererede session."""

from __future__ import annotations

import re
import sys
import base64
from pathlib import Path
from datetime import date

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st

from core.config import APP_TITLE, ANTHROPIC_API_KEY, AUTO_SEED_ON_EMPTY_DB
from core.database import (
    init_db, get_players, get_observations, get_training_stats,
    update_player_image, get_player_image,
    get_daily_plan, save_daily_plan, mark_plan_completed,
)
from core.epm import (
    get_player_profile, identify_gaps, identify_strengths, DIM_BY_KEY,
)
from core.elm import generate_daily_plan
from core.recommender import recommend_for_gaps
from core.theme import apply_theme, focus_badge, card, completed_badge
from core.auth import player_selector, get_player_id_from_url

# ---- page config (entry point only) -----------------------------------------

st.set_page_config(
    page_title="Min udvikling – KP13",
    layout="wide",
    initial_sidebar_state="expanded",
)

init_db()

if AUTO_SEED_ON_EMPTY_DB and not get_players():
    from seed import seed
    seed()

apply_theme()

# ---- sidebar ----------------------------------------------------------------

st.sidebar.title(APP_TITLE)
st.sidebar.caption("Spillerudviklings-system")
st.sidebar.divider()

players = get_players()
if not players:
    st.title("KP13 Akademi")
    st.info("Ingen spillere registreret endnu. Tilføj din første spiller fra spilleroversigten.")
    st.stop()

selected_id = player_selector(players)
_, _is_player = get_player_id_from_url(players)

profile = get_player_profile(selected_id)
if not profile:
    st.error("Spiller ikke fundet.")
    st.stop()

player = profile["player"]


# ---- helpers ----------------------------------------------------------------

_DK_MONTHS = {
    1: "januar", 2: "februar", 3: "marts", 4: "april", 5: "maj", 6: "juni",
    7: "juli", 8: "august", 9: "september", 10: "oktober", 11: "november", 12: "december",
}


def _fmt_hours(hours: float) -> str:
    return f"{hours:.1f} t" if hours >= 0.05 else "0 t"


def _fmt_delta(now: int, prev: int, *, unit: str = "") -> str | None:
    if now == prev:
        return None
    diff = now - prev
    sign = "+" if diff > 0 else "−"
    return f"{sign}{abs(diff)}{unit}"


def _fmt_hour_delta(now: float, prev: float) -> str | None:
    if abs(now - prev) < 0.05:
        return None
    diff = now - prev
    sign = "+" if diff > 0 else "−"
    return f"{sign}{abs(diff):.1f}t"


def _format_date_danish(d: date) -> str:
    return f"{d.day}. {_DK_MONTHS[d.month]} {d.year}"


def _strip_ai_title_and_date(md: str) -> str:
    if not md:
        return md
    lines = md.splitlines()
    while lines and not lines[0].strip():
        lines.pop(0)
    if lines and re.match(r"^#{1,6}\s+", lines[0].strip()):
        lines.pop(0)
    while lines and not lines[0].strip():
        lines.pop(0)
    if lines and re.match(r"^(dato|date)\s*:\s*", lines[0].strip(), flags=re.IGNORECASE):
        lines.pop(0)
    while lines and not lines[0].strip():
        lines.pop(0)
    return "\n".join(lines)


# ---- header with profile photo ----------------------------------------------

img_b64 = get_player_image(selected_id)

header_col, photo_col = st.columns([5, 1])
with header_col:
    st.title(player["name"])
    parts = [player.get("age_group", ""), player.get("position", ""), player.get("club", "")]
    subtitle = " · ".join(p for p in parts if p)
    if subtitle:
        st.caption(subtitle)

with photo_col:
    if img_b64:
        st.markdown(
            f'<img src="data:image/jpeg;base64,{img_b64}" '
            f'style="width:90px;height:90px;border-radius:50%;border:3px solid #3B82F6;object-fit:cover;" />',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div style="width:90px;height:90px;border-radius:50%;background:#1A1D27;'
            'border:3px solid #374151;display:flex;align-items:center;justify-content:center;'
            'font-size:2.5rem;text-align:center;">⚽</div>',
            unsafe_allow_html=True,
        )
    with st.expander("📷"):
        up = st.file_uploader("Profilbillede", type=["jpg", "jpeg", "png"], label_visibility="collapsed")
        if up:
            b64 = base64.b64encode(up.read()).decode()
            update_player_image(selected_id, b64)
            st.rerun()

st.markdown("")

# ---- training metrics hero --------------------------------------------------

stats = get_training_stats(selected_id)
wk, pwk = stats["week"], stats["prev_week"]
mn, pmn = stats["month"], stats["prev_month"]
tot = stats["total"]

st.markdown("### Din træning")

c1, c2, c3 = st.columns(3)

with c1:
    st.metric(
        "Denne uge",
        _fmt_hours(wk["hours"]),
        delta=_fmt_hour_delta(wk["hours"], pwk["hours"]),
        delta_color="normal",
    )
    sess_delta = _fmt_delta(wk["sessions"], pwk["sessions"], unit=" sess.")
    sub = f"{wk['sessions']} session(er)"
    if sess_delta:
        sub += f"  ·  {sess_delta} vs sidste uge"
    st.caption(sub)

with c2:
    st.metric(
        "Denne måned",
        _fmt_hours(mn["hours"]),
        delta=_fmt_hour_delta(mn["hours"], pmn["hours"]),
        delta_color="normal",
    )
    sess_delta = _fmt_delta(mn["sessions"], pmn["sessions"], unit=" sess.")
    sub = f"{mn['sessions']} session(er)"
    if sess_delta:
        sub += f"  ·  {sess_delta} vs sidste måned"
    st.caption(sub)

with c3:
    st.metric("I alt", _fmt_hours(tot["hours"]))
    st.caption(f"{tot['sessions']} session(er) siden start")

st.markdown("---")

# ---- today's training session ----------------------------------------------

today_iso = date.today().isoformat()
gaps = identify_gaps(selected_id, top_n=3)
strengths = identify_strengths(selected_id, top_n=3)

st.markdown("### Dagens træning")

if gaps:
    badges_html = " ".join(focus_badge(g["name"]) for g in gaps[:2])
    st.markdown(f"Dagens fokus &nbsp; {badges_html}", unsafe_allow_html=True)

existing_plan = get_daily_plan(selected_id, today_iso)

if existing_plan and existing_plan.get("plan_content"):
    plan_content = existing_plan["plan_content"]
    plan_md = plan_content.get("markdown", plan_content) if isinstance(plan_content, dict) else plan_content
    clean_plan_md = _strip_ai_title_and_date(plan_md)

    st.markdown(f"**Dato:** {_format_date_danish(date.fromisoformat(today_iso))}")
    st.markdown("")

    if existing_plan.get("completed"):
        st.markdown(completed_badge(), unsafe_allow_html=True)
        st.markdown("")

    st.markdown(clean_plan_md)

    if not existing_plan.get("completed"):
        st.markdown("#### Hvordan gik det?")
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
    elif existing_plan.get("player_feedback"):
        st.markdown(
            f'<p class="kp-muted">Feedback: {existing_plan["player_feedback"]}</p>',
            unsafe_allow_html=True,
        )

else:
    st.markdown(
        card(
            "<h4 style='margin:0 0 0.5rem 0;color:#F9FAFB'>Ingen session planlagt for i dag</h4>"
            "<p style='color:#9CA3AF;margin:0'>Generer en personlig træningssession baseret på dine udviklingsområder.</p>",
        ),
        unsafe_allow_html=True,
    )

    if not ANTHROPIC_API_KEY:
        st.caption("Tilføj API-nøgle i .env for at generere træningsplaner.")
    elif st.button("Generer dagens session", type="primary"):
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
                plan_md = _strip_ai_title_and_date(plan_md)

                focus_dim = gaps[0]["key"] if gaps else "general"
                save_daily_plan(
                    plan_date=today_iso,
                    player_id=selected_id,
                    focus_dimension=focus_dim,
                    plan_content={"markdown": plan_md},
                )
                st.rerun()
            except Exception as e:
                st.error(f"Generering fejlede: {e}")

if gaps:
    with st.expander("Hvorfor dette er fokus"):
        for g in gaps[:2]:
            meta = DIM_BY_KEY[g["key"]]
            st.markdown(f"**{meta.name}** — {meta.description}")
