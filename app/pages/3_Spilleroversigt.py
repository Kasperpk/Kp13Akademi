"""Spilleroversigt – Træneroversigt med EPM-profiler og udviklingsdata."""

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
from core.auth import require_coach

st.set_page_config(page_title="Spilleroversigt – KP13", layout="wide")
apply_theme()
require_coach()
st.title("Spilleroversigt")

# ---- sidebar: player selector ------------------------------------------------

players = get_players()
player_names = {p["id"]: p["name"] for p in players}

st.sidebar.header("Spillere")

if players:
    selected_id = st.sidebar.radio(
        "Vælg spiller",
        options=[p["id"] for p in players],
        format_func=lambda pid: player_names[pid],
    )
else:
    selected_id = None
    st.sidebar.info("Ingen spillere endnu.")

# ---- add new player ----------------------------------------------------------

with st.sidebar.expander("Tilføj ny spiller"):
    with st.form("add_player"):
        new_id = st.text_input("Spiller-ID (små bogstaver, ingen mellemrum)", placeholder="felix")
        new_name = st.text_input("Fuldt navn", placeholder="Felix Kirk Nebel")
        new_age = st.text_input("Aldersgruppe", placeholder="U9")
        new_pos = st.text_input("Position", placeholder="Central midtbane")
        new_club = st.text_input("Klub", placeholder="")
        new_foot = st.selectbox("Dominerende fod", ["højre", "venstre", "begge"])
        new_parent = st.text_input("Forældrekontakt", placeholder="")
        submitted = st.form_submit_button("Opret spiller")
        if submitted and new_id and new_name:
            upsert_player(
                new_id, new_name,
                age_group=new_age, position=new_pos, club=new_club,
                dominant_foot=new_foot, parent_name=new_parent,
            )
            initialise_player_epm(new_id)
            st.success(f"Oprettet {new_name}!")
            st.rerun()

# ---- main content: player profile -------------------------------------------

if not selected_id:
    st.info("Tilføj en spiller for at komme i gang.")
    st.stop()

profile = get_player_profile(selected_id)
if not profile:
    st.error("Spiller ikke fundet.")
    st.stop()

player = profile["player"]
flat = profile["flat_scores"]

CATEGORY_LABELS = {
    "technical": "Teknisk",
    "physical": "Fysisk",
    "cognitive": "Spilforståelse",
    "mental": "Mentalitet",
}

# Header
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    st.header(f"{player['name']}")
    st.caption(f"{player.get('age_group', '')} · {player.get('position', '')} · {player.get('club', '')}")
with col2:
    gaps = identify_gaps(selected_id, top_n=3)
    st.markdown("**Top huller**")
    for g in gaps:
        st.markdown(f"- {g['name']}: **{g['score']:.1f}**")
with col3:
    strengths = identify_strengths(selected_id, top_n=3)
    st.markdown("**Styrker**")
    for s in strengths:
        st.markdown(f"- {s['name']}: **{s['score']:.1f}**")

st.divider()

# ---- EPM tabs ----------------------------------------------------------------

tab_radar, tab_bars, tab_trend, tab_sessions = st.tabs(
    ["🎯 EPM Radar", "📊 Scoreoversigt", "📈 Udviklingsforløb", "📝 Sessionshistorik"]
)

with tab_radar:
    fig = epm_radar(flat, player["name"])
    st.plotly_chart(fig, use_container_width=True)

with tab_bars:
    fig = category_bars(flat)
    st.plotly_chart(fig, use_container_width=True)

    for cat in CATEGORIES:
        dims = CATEGORY_DIMS[cat]
        st.markdown(f"**{CATEGORY_LABELS.get(cat, cat.capitalize())}**")
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
    selected_dims = st.multiselect(
        "Vælg dimensioner at følge",
        options=[d.key for d in DIMENSIONS],
        default=[g["key"] for g in gaps[:3]],
        format_func=lambda k: DIM_BY_KEY[k].name,
    )
    if selected_dims:
        history_by_dim = {}
        for dk in selected_dims:
            history_by_dim[dk] = get_epm_history(selected_id, dk, limit=50)
        fig = multi_trend(history_by_dim, f"{player['name']} — Udviklingsforløb")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Vælg dimensioner ovenfor for at se udviklingsforløb.")

with tab_sessions:
    observations = get_observations(selected_id, limit=20)
    if observations:
        for obs in observations:
            with st.expander(f"{obs['date']} — {obs['session_type']}: {obs.get('theme', 'N/A')}"):
                if obs.get("coach_notes"):
                    st.markdown(obs["coach_notes"])
                if obs.get("extracted_scores"):
                    st.markdown("**Registrerede scores:**")
                    for dim_key, score in obs["extracted_scores"].items():
                        meta = DIM_BY_KEY.get(dim_key)
                        name = meta.name if meta else dim_key
                        st.markdown(f"- {name}: {score:.1f}")
    else:
        st.info("Ingen sessioner logget endnu. Gå til **Log Træning** for at registrere din første observation.")

# ---- baseline editor ---------------------------------------------------------

with st.expander("Rediger baseline-scores"):
    st.caption("Justér EPM-scores manuelt. Brug til første vurdering eller korrektioner.")
    with st.form("baseline_editor"):
        new_scores = {}
        for cat in CATEGORIES:
            st.markdown(f"**{CATEGORY_LABELS.get(cat, cat.capitalize())}**")
            cols = st.columns(len(CATEGORY_DIMS[cat]))
            for i, d in enumerate(CATEGORY_DIMS[cat]):
                current = flat.get(d.key, 5.0)
                new_scores[d.key] = cols[i].number_input(
                    f"{d.name}",
                    min_value=1.0, max_value=10.0,
                    value=current, step=0.5,
                    key=f"baseline_{d.key}",
                )

        save_baseline = st.form_submit_button("Gem baseline")
        if save_baseline:
            from core.database import set_epm_score
            for dim_key, score in new_scores.items():
                current_data = profile["scores"]
                obs_count = 0
                for cat_dims in current_data.values():
                    for dd in cat_dims:
                        if dd["key"] == dim_key:
                            obs_count = dd["observations"]
                            break
                set_epm_score(selected_id, dim_key, score, "manual", obs_count)
            st.success("Baseline opdateret!")
            st.rerun()
