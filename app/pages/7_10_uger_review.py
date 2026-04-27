"""10-ugers review — coach-led skill-niveau gennemgang.

Walks through each EPM dimension, shows current rubric level + next step,
captures coach commentary and the 1-3 focus dimensions for the next 10 weeks.
Saves a markdown artifact to ``clients/{player_id}/reviews/YYYY-MM-DD.md``.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st

from core.database import get_players
from core.epm import (
    DIMENSIONS, DIM_BY_KEY, CATEGORIES, CATEGORY_DIMS, get_player_profile,
)
from core.review import current_and_next, RUBRIC_LEVELS, LEVEL_STAGE
from core.theme import apply_theme
from core.auth import player_selector

st.set_page_config(page_title="10-ugers Review – KP13", layout="wide")
apply_theme()

_CLIENTS_DIR = _ROOT / "clients"
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

# ---- header -----------------------------------------------------------------

st.title("10-ugers Review")
st.caption(
    f"Gennemgang af **{player['name']}**'s færdighedsniveauer. Tag tid til hver dimension — "
    "fortæl spilleren hvor de står nu, og hvad næste niveau ser ud som."
)

review_date = st.date_input("Review-dato", value=date.today())

st.divider()

# ---- per-dimension review ---------------------------------------------------

# Persistent notes & focus picks live in session_state keyed by player+date
_state_key_prefix = f"review::{selected_id}::{review_date.isoformat()}"
notes_key = f"{_state_key_prefix}::notes"
focus_key = f"{_state_key_prefix}::focus"

if notes_key not in st.session_state:
    st.session_state[notes_key] = {d.key: "" for d in DIMENSIONS}
if focus_key not in st.session_state:
    st.session_state[focus_key] = []

for cat in CATEGORIES:
    icon = _CATEGORY_ICONS.get(cat, "")
    label = _CATEGORY_LABELS.get(cat, cat.capitalize())
    st.markdown(f"### {icon} {label}")

    for d in CATEGORY_DIMS[cat]:
        score = flat.get(d.key, 5.0)
        cn = current_and_next(score, d.key)

        with st.container(border=True):
            head = st.columns([3, 1])
            with head[0]:
                st.markdown(f"**{d.name}** — *{d.description}*")
            with head[1]:
                st.markdown(
                    f"<div style='text-align:right;font-size:1.4rem;font-weight:700;'>"
                    f"{score:.1f}<span style='font-size:0.8rem;color:#9CA3AF;'>/10</span></div>",
                    unsafe_allow_html=True,
                )

            cols = st.columns(2) if cn["next"] else st.columns(1)

            with cols[0]:
                st.markdown(
                    f"**Nu — {cn['current']['stage']} ({cn['current']['key']}/10)**"
                )
                st.info(cn["current"]["description"] or "_Ingen beskrivelse._")

            if cn["next"] and len(cols) > 1:
                with cols[1]:
                    st.markdown(
                        f"**Næste — {cn['next']['stage']} ({cn['next']['key']}/10)**"
                    )
                    st.success(cn["next"]["description"] or "_Ingen beskrivelse._")

            st.session_state[notes_key][d.key] = st.text_area(
                "Coach-noter",
                value=st.session_state[notes_key].get(d.key, ""),
                key=f"note_{d.key}_{review_date.isoformat()}",
                placeholder="Hvad så vi i de sidste 10 uger? Hvad skal der til for næste skridt?",
                height=80,
            )

st.divider()

# ---- focus picks for next 10 weeks ------------------------------------------

st.markdown("### Fokus de næste 10 uger")
st.caption("Vælg 1–3 dimensioner spilleren primært arbejder med frem til næste review.")

dim_options = {d.key: d.name for d in DIMENSIONS}
focus = st.multiselect(
    "Fokusområder",
    options=list(dim_options.keys()),
    default=st.session_state[focus_key],
    format_func=lambda k: dim_options[k],
    max_selections=3,
)
st.session_state[focus_key] = focus

review_summary = st.text_area(
    "Samlet kommentar til spilleren (med i markdown-output)",
    placeholder="Hvad er den ene ting du vil have spilleren tager med sig fra denne samtale?",
    height=120,
)

st.divider()

# ---- save ------------------------------------------------------------------


def _build_markdown() -> str:
    lines: list[str] = []
    lines.append(f"# 10-ugers Review — {player['name']}")
    lines.append("")
    lines.append(f"**Dato:** {review_date.isoformat()}  ")
    lines.append(f"**Aldersgruppe:** {player.get('age_group', '')}  ")
    parts = [player.get("position", ""), player.get("club", "")]
    sub = " · ".join(p for p in parts if p)
    if sub:
        lines.append(f"**Position:** {sub}  ")
    lines.append("")

    if focus:
        lines.append("## Fokus næste 10 uger")
        for k in focus:
            lines.append(f"- **{dim_options[k]}**")
        lines.append("")

    if review_summary.strip():
        lines.append("## Samlet kommentar")
        lines.append(review_summary.strip())
        lines.append("")

    lines.append("## Niveauer")
    for cat in CATEGORIES:
        label = _CATEGORY_LABELS.get(cat, cat.capitalize())
        lines.append(f"### {label}")
        lines.append("")
        for d in CATEGORY_DIMS[cat]:
            score = flat.get(d.key, 5.0)
            cn = current_and_next(score, d.key)
            lines.append(f"#### {d.name} — {score:.1f}/10 ({cn['current']['stage']})")
            lines.append("")
            lines.append(f"**Nu ({cn['current']['key']}/10):** {cn['current']['description']}")
            lines.append("")
            if cn["next"]:
                lines.append(f"**Næste ({cn['next']['key']}/10):** {cn['next']['description']}")
                lines.append("")
            note = (st.session_state[notes_key].get(d.key) or "").strip()
            if note:
                lines.append(f"**Coach-noter:** {note}")
                lines.append("")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _save() -> Path:
    out_dir = _CLIENTS_DIR / selected_id / "reviews"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{review_date.isoformat()}.md"
    out_path.write_text(_build_markdown(), encoding="utf-8")
    return out_path


col_save, col_preview = st.columns([1, 1])

if col_save.button("💾 Gem review", type="primary"):
    try:
        path = _save()
        st.success(f"Gemt: `{path.relative_to(_ROOT)}`")
    except Exception as e:
        st.error(f"Kunne ikke gemme: {e}")

with col_preview.expander("📄 Forhåndsvis markdown"):
    st.code(_build_markdown(), language="markdown")
