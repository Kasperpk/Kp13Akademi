"""Plotly chart builders for EPM visualisation."""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

from .epm import DIMENSIONS, DIM_BY_KEY, CATEGORIES, CATEGORY_DIMS


# ---- colour palette ----------------------------------------------------------

CAT_COLOURS = {
    "technical": "#3B82F6",   # blue
    "physical":  "#10B981",   # green
    "cognitive": "#F59E0B",   # amber
    "mental":    "#8B5CF6",   # purple
}


# ---- radar chart -------------------------------------------------------------

def epm_radar(flat_scores: dict[str, float], player_name: str = "") -> go.Figure:
    """Full 16-dimension radar chart."""
    labels = [DIM_BY_KEY[d.key].name for d in DIMENSIONS]
    values = [flat_scores.get(d.key, 5.0) for d in DIMENSIONS]
    colours = [CAT_COLOURS[d.category] for d in DIMENSIONS]

    # Close the polygon
    labels_closed = labels + [labels[0]]
    values_closed = values + [values[0]]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values_closed,
        theta=labels_closed,
        fill="toself",
        fillcolor="rgba(59,130,246,0.15)",
        line=dict(color="#3B82F6", width=2),
        name=player_name or "EPM",
    ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 10], tickvals=[2, 4, 6, 8, 10],
                           tickfont=dict(color="#6B7280"), gridcolor="#2A2D3A"),
            angularaxis=dict(tickfont=dict(color="#D1D5DB"), gridcolor="#2A2D3A"),
            bgcolor="#0F1116",
        ),
        showlegend=False,
        margin=dict(l=60, r=60, t=40, b=40),
        height=450,
        paper_bgcolor="#0F1116",
        plot_bgcolor="#0F1116",
        font=dict(color="#E5E7EB"),
        title=dict(text=f"{player_name} — Development Profile" if player_name else "Development Profile"),
    )
    return fig


# ---- category bar chart ------------------------------------------------------

def category_bars(flat_scores: dict[str, float]) -> go.Figure:
    """Horizontal bar chart grouped by category."""
    fig = go.Figure()

    for cat in reversed(CATEGORIES):
        dims = CATEGORY_DIMS[cat]
        names = [d.name for d in dims]
        scores = [flat_scores.get(d.key, 5.0) for d in dims]
        fig.add_trace(go.Bar(
            y=names,
            x=scores,
            orientation="h",
            marker_color=CAT_COLOURS[cat],
            name=cat.capitalize(),
        ))

    fig.update_layout(
        barmode="stack" if False else "group",
        xaxis=dict(range=[0, 10], title="Score", gridcolor="#2A2D3A", tickfont=dict(color="#9CA3AF")),
        yaxis=dict(autorange="reversed", tickfont=dict(color="#D1D5DB")),
        height=500,
        margin=dict(l=120, r=20, t=20, b=40),
        showlegend=True,
        legend=dict(orientation="h", y=-0.15, font=dict(color="#D1D5DB")),
        paper_bgcolor="#0F1116",
        plot_bgcolor="#0F1116",
        font=dict(color="#E5E7EB"),
    )
    return fig


# ---- score trend line --------------------------------------------------------

def score_trend(
    history: list[dict[str, Any]],
    dimension_key: str,
) -> go.Figure:
    """Line chart showing score over time for one dimension."""
    meta = DIM_BY_KEY.get(dimension_key)
    dates = [h["recorded_at"] for h in reversed(history)]
    scores = [h["score"] for h in reversed(history)]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates,
        y=scores,
        mode="lines+markers",
        line=dict(color=CAT_COLOURS.get(meta.category if meta else "technical", "#3B82F6"), width=2),
        marker=dict(size=6),
        name=meta.name if meta else dimension_key,
    ))
    fig.update_layout(
        yaxis=dict(range=[0, 10], title="Score", gridcolor="#2A2D3A", tickfont=dict(color="#9CA3AF")),
        xaxis=dict(title="Date", gridcolor="#2A2D3A", tickfont=dict(color="#9CA3AF")),
        height=300,
        margin=dict(l=40, r=20, t=30, b=40),
        title=dict(text=meta.name if meta else dimension_key),
        paper_bgcolor="#0F1116",
        plot_bgcolor="#0F1116",
        font=dict(color="#E5E7EB"),
    )
    return fig


# ---- multi-dimension trend ---------------------------------------------------

def multi_trend(
    history_by_dim: dict[str, list[dict[str, Any]]],
    title: str = "Development Over Time",
) -> go.Figure:
    """Overlay multiple dimensions on one time-series chart."""
    fig = go.Figure()

    for dim_key, hist in history_by_dim.items():
        if not hist:
            continue
        meta = DIM_BY_KEY.get(dim_key)
        dates = [h["recorded_at"] for h in reversed(hist)]
        scores = [h["score"] for h in reversed(hist)]
        fig.add_trace(go.Scatter(
            x=dates,
            y=scores,
            mode="lines+markers",
            name=meta.name if meta else dim_key,
            line=dict(width=2),
            marker=dict(size=5),
        ))

    fig.update_layout(
        yaxis=dict(range=[0, 10], title="Score", gridcolor="#2A2D3A", tickfont=dict(color="#9CA3AF")),
        xaxis=dict(title="", gridcolor="#2A2D3A", tickfont=dict(color="#9CA3AF")),
        height=400,
        margin=dict(l=40, r=20, t=40, b=40),
        title=dict(text=title),
        legend=dict(orientation="h", y=-0.2, font=dict(color="#D1D5DB")),
        paper_bgcolor="#0F1116",
        plot_bgcolor="#0F1116",
        font=dict(color="#E5E7EB"),
    )
    return fig
