"""Football-themed UI: dark theme CSS, stage labels, and reusable components."""

from __future__ import annotations

import streamlit as st

# ---- development stages (replace raw scores in player-facing UI) -----------

_STAGES = [
    (0.0, "Discovering"),
    (3.0, "Developing"),
    (5.5, "Confident"),
    (7.5, "Advanced"),
    (9.0, "Elite"),
]

STAGE_COLOURS = {
    "Discovering": "#6B7280",
    "Developing":  "#3B82F6",
    "Confident":   "#10B981",
    "Advanced":    "#F59E0B",
    "Elite":       "#EF4444",
}


def score_to_stage(score: float) -> str:
    stage = "Discovering"
    for threshold, label in _STAGES:
        if score >= threshold:
            stage = label
    return stage


# ---- CSS injection -----------------------------------------------------------

_CSS = """
<style>
    /* --- dark football theme --- */
    .stApp {
        background-color: #0F1116;
        color: #E5E7EB;
    }
    [data-testid="stSidebar"] {
        background-color: #161920;
    }
    [data-testid="stSidebar"] .stMarkdown {
        color: #D1D5DB;
    }

    /* headers */
    h1, h2, h3, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        color: #F9FAFB !important;
        font-weight: 600;
    }

    /* cards */
    .kp-card {
        background: #1A1D27;
        border: 1px solid #2A2D3A;
        border-radius: 10px;
        padding: 1.25rem;
        margin-bottom: 0.75rem;
    }
    .kp-card-accent {
        background: linear-gradient(135deg, #1A1D27 0%, #1E2433 100%);
        border: 1px solid #3B82F6;
        border-radius: 10px;
        padding: 1.25rem;
        margin-bottom: 0.75rem;
    }

    /* dimension bar */
    .dim-bar-row {
        display: flex;
        align-items: center;
        margin: 0.35rem 0;
        gap: 0.75rem;
    }
    .dim-bar-label {
        min-width: 140px;
        font-size: 0.92rem;
        color: #D1D5DB;
    }
    .dim-bar-track {
        flex: 1;
        height: 8px;
        background: #2A2D3A;
        border-radius: 4px;
        overflow: hidden;
    }
    .dim-bar-fill {
        height: 100%;
        border-radius: 4px;
        transition: width 0.3s;
    }
    .dim-bar-stage {
        min-width: 90px;
        text-align: right;
        font-size: 0.82rem;
        font-weight: 600;
    }

    /* focus badge */
    .focus-badge {
        display: inline-block;
        background: #1E293B;
        border: 1px solid #3B82F6;
        border-radius: 6px;
        padding: 0.3rem 0.75rem;
        font-size: 0.85rem;
        color: #93C5FD;
        font-weight: 500;
    }

    /* session block inside daily plan */
    .session-block {
        background: #1A1D27;
        border-left: 3px solid #3B82F6;
        border-radius: 0 8px 8px 0;
        padding: 1rem 1.25rem;
        margin: 0.5rem 0;
    }

    /* category header */
    .cat-header {
        font-size: 0.78rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #9CA3AF;
        margin: 1rem 0 0.4rem 0;
    }

    /* muted helper text */
    .kp-muted {
        color: #6B7280;
        font-size: 0.85rem;
    }

    /* completed badge */
    .completed-badge {
        display: inline-block;
        background: #065F46;
        color: #A7F3D0;
        border-radius: 6px;
        padding: 0.25rem 0.6rem;
        font-size: 0.82rem;
        font-weight: 500;
    }

    /* hide default streamlit footer / hamburger */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
"""


def apply_theme() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


# ---- reusable HTML components ------------------------------------------------

def dimension_bar(name: str, score: float, show_score: bool = False) -> str:
    stage = score_to_stage(score)
    colour = STAGE_COLOURS[stage]
    pct = min(score / 10.0 * 100, 100)
    score_text = f" ({score:.1f})" if show_score else ""
    return (
        f'<div class="dim-bar-row">'
        f'  <span class="dim-bar-label">{name}{score_text}</span>'
        f'  <div class="dim-bar-track">'
        f'    <div class="dim-bar-fill" style="width:{pct:.0f}%;background:{colour}"></div>'
        f'  </div>'
        f'  <span class="dim-bar-stage" style="color:{colour}">{stage}</span>'
        f'</div>'
    )


def focus_badge(text: str) -> str:
    return f'<span class="focus-badge">{text}</span>'


def card(content: str, accent: bool = False) -> str:
    cls = "kp-card-accent" if accent else "kp-card"
    return f'<div class="{cls}">{content}</div>'


def completed_badge() -> str:
    return '<span class="completed-badge">Completed</span>'


def category_header(name: str) -> str:
    return f'<div class="cat-header">{name}</div>'
