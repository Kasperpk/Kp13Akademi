"""My Development – Player progress view with development stages."""

import sys
from pathlib import Path
from datetime import date, timedelta

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st

from core.config import ANTHROPIC_API_KEY
from core.database import get_players, get_observations, get_epm_history
from core.epm import (
    get_player_profile, identify_gaps, identify_strengths,
    DIMENSIONS, DIM_BY_KEY, CATEGORIES, CATEGORY_DIMS,
)
from core.elm import generate_weekly_summary
from core.theme import (
    apply_theme, dimension_bar, category_header,
    score_to_stage, focus_badge, card,
)

st.set_page_config(page_title="My Development – KP13", layout="wide")
apply_theme()

# ---- player selector ---------------------------------------------------------

players = get_players()
if not players:
    st.info("No players registered yet.")
    st.stop()

player_options = {p["id"]: p["name"] for p in players}
selected_id = st.sidebar.radio(
    "Player",
    options=[p["id"] for p in players],
    format_func=lambda pid: player_options[pid],
)

profile = get_player_profile(selected_id)
if not profile:
    st.error("Player not found.")
    st.stop()

player = profile["player"]
flat = profile["flat_scores"]

# ---- header ------------------------------------------------------------------

st.title(f"{player['name']}")
parts = [player.get("age_group", ""), player.get("position", ""), player.get("club", "")]
subtitle = " · ".join(p for p in parts if p)
if subtitle:
    st.caption(subtitle)

st.markdown("")

# ---- current focus -----------------------------------------------------------

gaps = identify_gaps(selected_id, top_n=3)
strengths = identify_strengths(selected_id, top_n=3)

if gaps:
    st.markdown("### Current Focus")
    bars_html = ""
    for g in gaps:
        bars_html += dimension_bar(g["name"], g["score"])
    st.markdown(card(bars_html, accent=True), unsafe_allow_html=True)

# ---- strengths ---------------------------------------------------------------

if strengths:
    st.markdown("### Strengths")
    bars_html = ""
    for s in strengths:
        bars_html += dimension_bar(s["name"], s["score"])
    st.markdown(card(bars_html), unsafe_allow_html=True)

# ---- all development areas ---------------------------------------------------

st.markdown("### All Development Areas")

CATEGORY_LABELS = {
    "technical": "Technical",
    "physical": "Physical",
    "cognitive": "Game Intelligence",
    "mental": "Mentality",
}

all_bars_html = ""
for cat in CATEGORIES:
    dims = CATEGORY_DIMS[cat]
    all_bars_html += category_header(CATEGORY_LABELS.get(cat, cat.capitalize()))
    for d in dims:
        score = flat.get(d.key, 5.0)
        all_bars_html += dimension_bar(d.name, score)

st.markdown(card(all_bars_html), unsafe_allow_html=True)

# ---- weekly summary ----------------------------------------------------------

st.divider()
st.markdown("### Weekly Report")

today = date.today()
week_start = today - timedelta(days=today.weekday())
all_obs = get_observations(selected_id, limit=100)
week_obs = [obs for obs in all_obs if obs["date"] >= week_start.isoformat()]

st.markdown(f'<p class="kp-muted">Week of {week_start.strftime("%B %d, %Y")} — {len(week_obs)} session(s) logged</p>', unsafe_allow_html=True)

if not ANTHROPIC_API_KEY:
    st.caption("Configure API key in .env to generate weekly reports.")
else:
    if st.button("Generate weekly report", type="primary"):
        with st.spinner("Writing report..."):
            try:
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
                st.error(f"Report generation failed: {e}")
