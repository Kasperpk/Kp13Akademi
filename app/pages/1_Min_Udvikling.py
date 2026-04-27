"""Min Udvikling — træningstimer som primær metrik. Niveau-gennemgang flyttet til 10-ugers review."""

from __future__ import annotations

import sys
import base64
from pathlib import Path
from datetime import date, timedelta

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st

from core.config import ANTHROPIC_API_KEY
from core.database import (
    get_players, get_observations, get_epm_history,
    get_training_hours, get_weekly_activity, get_recent_sessions,
    update_player_image, get_player_image,
)
from core.epm import (
    get_player_profile, identify_gaps, identify_strengths, DIMENSIONS,
)
from core.elm import generate_weekly_summary
from core.theme import apply_theme
from core.auth import player_selector, get_player_id_from_url

st.set_page_config(page_title="Min Udvikling – KP13", layout="wide")
apply_theme()


def _fmt_min(m: int) -> str:
    return f"{m // 60}t {m % 60}m" if m >= 60 else f"{m}m"


def _activity_color(sessions: int) -> str:
    if sessions <= 0:
        return "#1F2937"
    if sessions == 1:
        return "#1E3A8A"
    if sessions == 2:
        return "#1D4ED8"
    if sessions == 3:
        return "#3B82F6"
    return "#60A5FA"


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

# ---- header with profile photo -----------------------------------------------

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

# ---- training hours hero -----------------------------------------------------

hours = get_training_hours(selected_id)
week_min = hours.get("week_minutes", 0)
week_sessions = hours.get("week_sessions", 0)

st.markdown("### Din træning")

c1, c2, c3 = st.columns(3)
if week_min:
    c1.metric("Denne uge", _fmt_min(week_min), help=f"{week_sessions} session(er)")
else:
    c1.metric("Denne uge", f"{week_sessions} sessions" if week_sessions else "0")
c2.metric("Denne måned", f"{hours['month_hours']} t")
c3.metric("I alt", f"{hours['total_hours']} t")

# ---- activity grid -----------------------------------------------------------

weekly = get_weekly_activity(selected_id, weeks=12)
active_weeks = sum(1 for w in weekly if w["sessions"] > 0)

st.markdown(
    f'<p style="color:#9CA3AF;font-size:0.85rem;margin-top:1rem;margin-bottom:0.5rem;">'
    f'Sidste 12 uger — {active_weeks}/{len(weekly)} uger trænet</p>',
    unsafe_allow_html=True,
)

cells = []
for w in weekly:
    color = _activity_color(w["sessions"])
    cells.append(
        f'<div title="Uge {w["week_start"]} · {w["sessions"]} session(er)" '
        f'style="aspect-ratio:1;background:{color};border-radius:3px;'
        f'border:1px solid #2A2D3A;"></div>'
    )
st.markdown(
    f'<div style="display:grid;grid-template-columns:repeat(12,1fr);gap:6px;'
    f'max-width:520px;">{ "".join(cells) }</div>',
    unsafe_allow_html=True,
)

# ---- recent sessions ---------------------------------------------------------

recent = get_recent_sessions(selected_id, limit=8)
if recent:
    st.markdown("##### Seneste træninger")
    for s in recent:
        cols = st.columns([4, 1, 1])
        cols[0].markdown(f"**{s['label']}**  \n<span style='color:#9CA3AF;font-size:0.78rem'>{s['date']} · {s['minutes']} min</span>", unsafe_allow_html=True)
        cols[1].markdown(f"<span style='color:#9CA3AF;font-size:0.78rem'>{s['kind']}</span>", unsafe_allow_html=True)

st.markdown("---")

# ---- 10-week review entry point ---------------------------------------------

st.markdown("### Niveau-gennemgang")
st.caption(
    "Færdighedsniveauer (første touch, pasning, osv.) gennemgår vi i en samlet samtale "
    "ca. hver 10. uge — ikke som en daglig score, men som en grundig samtale om hvor du står "
    "og hvad du arbejder hen imod de næste 10 uger."
)
st.page_link(
    "pages/7_10_uger_review.py",
    label="Start 10-ugers review →",
    icon="🎯",
)

st.markdown("---")

# ---- weekly AI summary -------------------------------------------------------

st.markdown("### Ugentlig Rapport")

today = date.today()
week_start = today - timedelta(days=today.weekday())
all_obs = get_observations(selected_id, limit=100)
week_obs = [obs for obs in all_obs if obs["date"] >= week_start.isoformat()]

st.markdown(
    f'<p style="color:#9CA3AF;font-size:0.85rem;">Uge der starter {week_start.day}. '
    f'{week_start.strftime("%B %Y")} — {len(week_obs)} session(er) logget</p>',
    unsafe_allow_html=True,
)

if not ANTHROPIC_API_KEY:
    st.caption("Tilføj API-nøgle i .env for at generere ugentlige rapporter.")
else:
    if st.button("Generer ugentlig rapport", type="primary"):
        with st.spinner("Skriver rapport..."):
            try:
                gaps = identify_gaps(selected_id, top_n=3)
                strengths = identify_strengths(selected_id, top_n=3)
                epm_hist = []
                for d in DIMENSIONS:
                    epm_hist.extend(get_epm_history(selected_id, d.key, limit=10))

                summary = generate_weekly_summary(
                    player_profile=profile,
                    week_observations=week_obs,
                    epm_history=epm_hist,
                    gaps=gaps,
                    strengths=strengths,
                )
                st.markdown(summary)
            except Exception as e:
                st.error(f"Rapport-generering fejlede: {e}")
