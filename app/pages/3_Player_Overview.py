"""Player Overview – Coach view with full EPM profiles and development data."""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st

from core.database import get_players, get_player, get_observations, get_epm_history, upsert_player
from core.epm import (
    get_player_profile, identify_gaps, identify_strengths,
    initialise_player_epm, DIMENSIONS, DIM_BY_KEY, CATEGORIES, CATEGORY_DIMS,
)
from core.charts import epm_radar, category_bars, multi_trend
from core.theme import apply_theme

st.set_page_config(page_title="Player Overview – KP13", layout="wide")
apply_theme()
st.title("Player Overview")

# ---- sidebar: player selector ------------------------------------------------

players = get_players()
player_names = {p["id"]: p["name"] for p in players}

st.sidebar.header("Players")

if players:
    selected_id = st.sidebar.radio(
        "Select player",
        options=[p["id"] for p in players],
        format_func=lambda pid: player_names[pid],
    )
else:
    selected_id = None
    st.sidebar.info("No players yet.")

# ---- add new player ----------------------------------------------------------

with st.sidebar.expander("Add New Player"):
    with st.form("add_player"):
        new_id = st.text_input("Player ID (lowercase, no spaces)", placeholder="felix")
        new_name = st.text_input("Full Name", placeholder="Felix Kirk Nebel")
        new_age = st.text_input("Age Group", placeholder="U9")
        new_pos = st.text_input("Position", placeholder="Central midfielder")
        new_club = st.text_input("Club", placeholder="")
        new_foot = st.selectbox("Dominant Foot", ["right", "left", "both"])
        new_parent = st.text_input("Parent Contact Name", placeholder="")
        submitted = st.form_submit_button("Create Player")
        if submitted and new_id and new_name:
            upsert_player(
                new_id, new_name,
                age_group=new_age, position=new_pos, club=new_club,
                dominant_foot=new_foot, parent_name=new_parent,
            )
            initialise_player_epm(new_id)
            st.success(f"Created {new_name}!")
            st.rerun()

# ---- main content: player profile -------------------------------------------

if not selected_id:
    st.info("Add a player to get started.")
    st.stop()

profile = get_player_profile(selected_id)
if not profile:
    st.error("Player not found.")
    st.stop()

player = profile["player"]
flat = profile["flat_scores"]

# Header
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    st.header(f"{player['name']}")
    st.caption(f"{player.get('age_group', '')} · {player.get('position', '')} · {player.get('club', '')}")
with col2:
    gaps = identify_gaps(selected_id, top_n=3)
    st.markdown("**Top Gaps**")
    for g in gaps:
        st.markdown(f"- {g['name']}: **{g['score']:.1f}**")
with col3:
    strengths = identify_strengths(selected_id, top_n=3)
    st.markdown("**Strengths**")
    for s in strengths:
        st.markdown(f"- {s['name']}: **{s['score']:.1f}**")

st.divider()

# ---- EPM radar chart ---------------------------------------------------------

tab_radar, tab_bars, tab_trend, tab_sessions = st.tabs(
    ["🎯 EPM Radar", "📊 Score Breakdown", "📈 Development Trend", "📝 Session History"]
)

with tab_radar:
    fig = epm_radar(flat, player["name"])
    st.plotly_chart(fig, use_container_width=True)

with tab_bars:
    fig = category_bars(flat)
    st.plotly_chart(fig, use_container_width=True)

    # Detail table
    for cat in CATEGORIES:
        dims = CATEGORY_DIMS[cat]
        st.markdown(f"**{cat.capitalize()}**")
        for d in dims:
            score = flat.get(d.key, 5.0)
            scores_data = profile["scores"].get(cat, [])
            dim_data = next((x for x in scores_data if x["key"] == d.key), {})
            conf = dim_data.get("confidence", "low")
            obs_count = dim_data.get("observations", 0)
            st.markdown(
                f"**{d.name}**: {score:.1f}/10 "
                f"*[{conf}, {obs_count} obs]*"
            )

with tab_trend:
    # Let user pick dimensions to visualise
    selected_dims = st.multiselect(
        "Select dimensions to track",
        options=[d.key for d in DIMENSIONS],
        default=[g["key"] for g in gaps[:3]],
        format_func=lambda k: DIM_BY_KEY[k].name,
    )
    if selected_dims:
        history_by_dim = {}
        for dk in selected_dims:
            history_by_dim[dk] = get_epm_history(selected_id, dk, limit=50)
        fig = multi_trend(history_by_dim, f"{player['name']} — Development")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Select dimensions above to see trends.")

with tab_sessions:
    observations = get_observations(selected_id, limit=20)
    if observations:
        for obs in observations:
            with st.expander(f"{obs['date']} — {obs['session_type']}: {obs.get('theme', 'N/A')}"):
                if obs.get("coach_notes"):
                    st.markdown(obs["coach_notes"])
                if obs.get("extracted_scores"):
                    st.markdown("**Extracted Scores:**")
                    for dim_key, score in obs["extracted_scores"].items():
                        meta = DIM_BY_KEY.get(dim_key)
                        name = meta.name if meta else dim_key
                        st.markdown(f"- {name}: {score:.1f}")
    else:
        st.info("No sessions logged yet. Go to **Log Session** to record your first observation.")

# ---- baseline editor (for initial setup) -------------------------------------

with st.expander("Edit Baseline Scores"):
    st.caption("Manually adjust EPM scores. Use this for initial assessment or corrections.")
    with st.form("baseline_editor"):
        new_scores = {}
        for cat in CATEGORIES:
            st.markdown(f"**{cat.capitalize()}**")
            cols = st.columns(len(CATEGORY_DIMS[cat]))
            for i, d in enumerate(CATEGORY_DIMS[cat]):
                current = flat.get(d.key, 5.0)
                new_scores[d.key] = cols[i].number_input(
                    f"{d.name}",
                    min_value=1.0, max_value=10.0,
                    value=current, step=0.5,
                    key=f"baseline_{d.key}",
                )

        save_baseline = st.form_submit_button("Save Baseline")
        if save_baseline:
            from core.database import set_epm_score
            for dim_key, score in new_scores.items():
                current_data = profile["scores"]
                # Find current observation count
                obs_count = 0
                for cat_dims in current_data.values():
                    for dd in cat_dims:
                        if dd["key"] == dim_key:
                            obs_count = dd["observations"]
                            break
                set_epm_score(selected_id, dim_key, score, "manual", obs_count)
            st.success("Baseline updated!")
            st.rerun()
