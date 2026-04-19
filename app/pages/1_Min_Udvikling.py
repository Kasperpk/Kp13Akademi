"""Min Udvikling — Spillerens udviklingsview med rubrics, foto og træningsdashboard."""

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
    get_players, get_observations, get_epm_history, get_training_hours,
    update_player_image, get_player_image,
)
from core.epm import (
    get_player_profile, identify_gaps, identify_strengths,
    DIMENSIONS, DIM_BY_KEY, CATEGORIES, CATEGORY_DIMS,
)
from core.elm import generate_weekly_summary
from core.rubrics import RUBRICS
from core.theme import apply_theme, score_to_stage, focus_badge
from core.auth import player_selector, get_player_id_from_url

st.set_page_config(page_title="Min Udvikling – KP13", layout="wide")
apply_theme()

_STAGE_COLORS = {
    "Opdageren":       "#6B7280",
    "Under Udvikling": "#3B82F6",
    "Sikker":          "#10B981",
    "Avanceret":       "#F59E0B",
    "Elite":           "#EF4444",
}

_CATEGORY_LABELS = {
    "technical": "Teknisk",
    "physical":  "Fysisk",
    "cognitive": "Spilforståelse",
    "mental":    "Mentalitet",
}

_CATEGORY_ICONS = {
    "technical": "⚽",
    "physical":  "💪",
    "cognitive": "🧠",
    "mental":    "🔥",
}


def _score_to_rubric_key(score: float) -> str:
    if score <= 2: return "1-2"
    if score <= 5: return "3-5"
    if score <= 7: return "6-7"
    if score <= 9: return "8-9"
    return "10"


def _next_rubric_key(key: str) -> str | None:
    order = ["1-2", "3-5", "6-7", "8-9", "10"]
    try:
        idx = order.index(key)
        return order[idx + 1] if idx < len(order) - 1 else None
    except ValueError:
        return None


def _stage_badge_html(stage: str) -> str:
    color = _STAGE_COLORS.get(stage, "#6B7280")
    return (
        f'<span style="background:{color};color:white;border-radius:4px;'
        f'padding:2px 8px;font-size:0.72rem;font-weight:600;">{stage}</span>'
    )


def _score_bar_html(score: float) -> str:
    pct = (score / 10) * 100
    stage = score_to_stage(score)
    color = _STAGE_COLORS.get(stage, "#3B82F6")
    return (
        f'<div style="background:#1F2937;border-radius:4px;height:6px;margin:4px 0 8px 0;">'
        f'<div style="background:{color};width:{pct:.0f}%;height:100%;border-radius:4px;"></div>'
        f'</div>'
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
flat = profile["flat_scores"]

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

# ---- gaps + strengths --------------------------------------------------------

gaps = identify_gaps(selected_id, top_n=3)
strengths = identify_strengths(selected_id, top_n=3)

col_gaps, col_str = st.columns(2)
with col_gaps:
    if gaps:
        st.markdown("**Fokusområder**")
        badges = " ".join(focus_badge(f"{g['name']} {g['score']:.1f}") for g in gaps)
        st.markdown(badges, unsafe_allow_html=True)
with col_str:
    if strengths:
        st.markdown("**Styrker**")
        badges = " ".join(focus_badge(f"{s['name']} {s['score']:.1f}") for s in strengths)
        st.markdown(badges, unsafe_allow_html=True)

st.markdown("---")

# ---- rubrics view ------------------------------------------------------------

st.markdown("### Dit niveau")
st.caption("Klik på en dimension for at se præcis hvad dit nuværende niveau betyder — og hvad næste trin kræver.")

for cat in CATEGORIES:
    dims = CATEGORY_DIMS[cat]
    icon = _CATEGORY_ICONS.get(cat, "")
    label = _CATEGORY_LABELS.get(cat, cat.capitalize())
    st.markdown(f"#### {icon} {label}")

    cols = st.columns(len(dims))
    for i, d in enumerate(dims):
        score = flat.get(d.key, 5.0)
        stage = score_to_stage(score)
        rubric_key = _score_to_rubric_key(score)
        rubric = RUBRICS.get(d.key, {})
        current_desc = rubric.get(rubric_key, "")
        next_key = _next_rubric_key(rubric_key)
        next_desc = rubric.get(next_key, "") if next_key else ""

        with cols[i]:
            st.markdown(
                f'<div style="background:#1A1D27;border-radius:8px;padding:12px 14px;margin-bottom:6px;">'
                f'<div style="font-size:0.8rem;font-weight:600;color:#E5E7EB;margin-bottom:2px;">{d.name}</div>'
                f'<div style="font-size:1.5rem;font-weight:700;color:#F9FAFB;">{score:.1f}</div>'
                f'{_score_bar_html(score)}'
                f'{_stage_badge_html(stage)}'
                f'</div>',
                unsafe_allow_html=True,
            )
            if current_desc:
                with st.expander("Se niveau"):
                    st.markdown(f"**Nu — {score:.1f}/10**")
                    st.info(current_desc)
                    if next_desc and next_key:
                        st.markdown(f"**Næste trin ({next_key}/10):**")
                        st.success(next_desc)

    st.markdown("")

st.markdown("---")

# ---- training dashboard ------------------------------------------------------

st.markdown("### Trænings-Dashboard")

hours = get_training_hours(selected_id)

c1, c2, c3 = st.columns(3)
c1.metric("Timer i alt", f"{hours['total_hours']} t")
c2.metric("Timer denne måned", f"{hours['month_hours']} t")
c3.metric("Sessions denne uge", hours["week_sessions"])

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
