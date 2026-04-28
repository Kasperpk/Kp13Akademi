"""KP13 Akademi — Min Udvikling (landing). Træningstimer & sessioner som primær metrik."""

from __future__ import annotations

import sys
import base64
from pathlib import Path
from datetime import date, timedelta

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st

from core.config import APP_TITLE, ANTHROPIC_API_KEY, AUTO_SEED_ON_EMPTY_DB
from core.database import (
    init_db, get_players, get_observations, get_epm_history,
    get_training_stats, update_player_image, get_player_image,
)
from core.epm import (
    get_player_profile, identify_gaps, identify_strengths, DIMENSIONS,
)
from core.elm import generate_weekly_summary
from core.theme import apply_theme
from core.auth import player_selector, get_player_id_from_url

# ---- page config (entry point only) -----------------------------------------

st.set_page_config(
    page_title=APP_TITLE,
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

# ---- 10-week review entry point ---------------------------------------------

st.markdown("### Niveau-gennemgang")
st.caption(
    "Færdighedsniveauer (første touch, pasning, osv.) gennemgår vi i en samlet samtale "
    "ca. hver 10. uge — ikke som en daglig score, men som en grundig samtale om hvor du står "
    "og hvad du arbejder hen imod de næste 10 uger."
)
st.page_link("pages/7_10_uger_review.py", label="Start 10-ugers review →", icon="🎯")

st.markdown("---")

# ---- weekly AI summary ------------------------------------------------------

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
