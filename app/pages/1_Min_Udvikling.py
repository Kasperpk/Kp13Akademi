"""My Development – Player progress view with development stages."""

import sys
from pathlib import Path
from datetime import date, timedelta

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st

from core.config import ANTHROPIC_API_KEY
from core.database import get_players, get_observations, get_epm_history, get_training_hours
from core.epm import (
    get_player_profile, identify_gaps, identify_strengths,
    DIMENSIONS, DIM_BY_KEY, CATEGORIES, CATEGORY_DIMS,
)
from core.elm import generate_weekly_summary
from core.theme import (
    apply_theme, dimension_bar, category_header,
    score_to_stage, focus_badge, card,
)
from core.auth import player_selector

st.set_page_config(page_title="Min Udvikling – KP13", layout="wide")
apply_theme()

# ---- player selector ---------------------------------------------------------

players = get_players()
if not players:
    st.info("Ingen spillere registreret endnu.")
    st.stop()

selected_id = player_selector(players)

profile = get_player_profile(selected_id)
if not profile:
    st.error("Spiller ikke fundet.")
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
    st.markdown("### Aktuelle Fokusområder")
    bars_html = ""
    for g in gaps:
        bars_html += dimension_bar(g["name"], g["score"])
    st.markdown(card(bars_html, accent=True), unsafe_allow_html=True)

# ---- strengths ---------------------------------------------------------------

if strengths:
    st.markdown("### Styrker")
    bars_html = ""
    for s in strengths:
        bars_html += dimension_bar(s["name"], s["score"])
    st.markdown(card(bars_html), unsafe_allow_html=True)

# ---- all development areas ---------------------------------------------------

st.markdown("### Alle Udviklingsområder")

CATEGORY_LABELS = {
    "technical": "Teknisk",
    "physical": "Fysisk",
    "cognitive": "Spilforståelse",
    "mental": "Mentalitet",
}

all_bars_html = ""
for cat in CATEGORIES:
    dims = CATEGORY_DIMS[cat]
    all_bars_html += category_header(CATEGORY_LABELS.get(cat, cat.capitalize()))
    for d in dims:
        score = flat.get(d.key, 5.0)
        all_bars_html += dimension_bar(d.name, score)

st.markdown(card(all_bars_html), unsafe_allow_html=True)

# ---- training dashboard ------------------------------------------------------

st.divider()
st.markdown("### Trænings-Dashboard")

hours = get_training_hours(selected_id)

dash_col1, dash_col2, dash_col3 = st.columns(3)
with dash_col1:
    st.metric("Timer i alt", f"{hours['total_hours']} t")
with dash_col2:
    st.metric("Timer denne måned", f"{hours['month_hours']} t")
with dash_col3:
    st.metric("Sessions denne uge", hours["week_sessions"])

# Progress toward top EPM goals
if gaps:
    st.markdown("**Mål at nå**")
    for g in gaps[:3]:
        target = 5.0 if g["score"] < 5 else (7.5 if g["score"] < 7.5 else 9.0)
        progress = min((g["score"] - 1.0) / (target - 1.0), 1.0)
        stage_target = score_to_stage(target)
        goal_label = f"{g['name']}: {g['score']:.1f} → {target:.0f} ({stage_target})"
        st.progress(max(0.0, progress), text=goal_label)

# ---- weekly summary ----------------------------------------------------------

st.divider()
st.markdown("### Ugentlig Rapport")

today = date.today()
week_start = today - timedelta(days=today.weekday())
all_obs = get_observations(selected_id, limit=100)
week_obs = [obs for obs in all_obs if obs["date"] >= week_start.isoformat()]

st.markdown(f'<p class="kp-muted">Uge der starter {week_start.day}. {week_start.strftime("%B %Y")} — {len(week_obs)} session(er) logget</p>', unsafe_allow_html=True)

if not ANTHROPIC_API_KEY:
    st.caption("Tilføj API-nøgle i .env for at generere ugentlige rapporter.")
else:
    if st.button("Generer ugentlig rapport", type="primary"):
        with st.spinner("Skriver rapport..."):
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
                st.error(f"Rapport-generering fejlede: {e}")
