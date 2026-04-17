"""Log Session – Record coaching observations and update EPM scores."""

import sys
from pathlib import Path
from datetime import date

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st

from core.config import ANTHROPIC_API_KEY
from core.database import get_players, save_observation, get_observations
from core.epm import (
    get_player_profile, update_scores_from_observation,
    DIMENSIONS, DIM_BY_KEY, CATEGORIES, CATEGORY_DIMS,
)
from core.elm import extract_scores_from_notes
from core.theme import apply_theme
from core.rubrics import RUBRICS

st.set_page_config(page_title="Log Session – KP13", layout="wide")
apply_theme()
st.title("Log Session")

# ---- player selector ---------------------------------------------------------

players = get_players()
if not players:
    st.warning("No players registered. Go to Dashboard to add a player first.")
    st.stop()

player_options = {p["id"]: p["name"] for p in players}
selected_id = st.selectbox(
    "Player",
    options=list(player_options.keys()),
    format_func=lambda pid: player_options[pid],
)

profile = get_player_profile(selected_id)

# ---- session metadata --------------------------------------------------------

col1, col2, col3 = st.columns(3)
with col1:
    session_date = st.date_input("Session Date", value=date.today())
with col2:
    session_type = st.selectbox("Session Type", ["coached", "team_observation", "match", "home"])
with col3:
    session_theme = st.text_input("Theme", placeholder="e.g. Driving with speed, Receiving on the half-turn")

# ---- transfer check (if previous sessions exist) ----------------------------

recent = get_observations(selected_id, limit=3)
if recent:
    with st.expander("Transfer Check — Did previous work show up?"):
        st.caption("Did skills from the last individual session transfer to the team/match context?")
        last_session = recent[0]
        st.markdown(f"**Last session:** {last_session['date']} — {last_session.get('theme', 'N/A')}")
        transfer = st.radio(
            "Transfer observed?",
            options=["Not applicable", "Yes — skills transferred", "Partially", "No — didn't transfer yet"],
            horizontal=True,
        )
else:
    transfer = "Not applicable"

# ---- coach notes -------------------------------------------------------------

st.subheader("Coach Notes")
st.caption(
    "Write your observations naturally. The AI will extract EPM dimension scores. "
    "Write about what you saw — technique, decisions, attitude, effort, specific moments."
)

coach_notes = st.text_area(
    "Session observations",
    height=250,
    placeholder=(
        "Example: Felix showed great improvement in his half-turn receiving today. "
        "Body shape was open, first touch was forward. But when space opened up to drive, "
        "he still chose the safe pass 3 out of 4 times. The decision to drive isn't automatic yet. "
        "Energy and effort were high throughout. Enjoyed the 1v1 finishing drill at the end."
    ),
)

# ---- AI extraction -----------------------------------------------------------

st.divider()
st.subheader("Development Scores")

if "extracted" not in st.session_state:
    st.session_state.extracted = {}
if "extraction_done" not in st.session_state:
    st.session_state.extraction_done = False

col_extract, col_manual = st.columns(2)

with col_extract:
    extract_btn = st.button(
        "Extract Scores with AI",
        disabled=not coach_notes.strip() or not ANTHROPIC_API_KEY,
        type="primary",
    )
    if not ANTHROPIC_API_KEY:
        st.caption("Set ANTHROPIC_API_KEY in .env to enable AI extraction.")

with col_manual:
    manual_btn = st.button("Score Manually")

# ---- scoring rubric reference ------------------------------------------------

with st.expander("Scoring guide — what does each level look like?"):
    for cat in CATEGORIES:
        dims = CATEGORY_DIMS[cat]
        st.markdown(f"**{cat.capitalize()}**")
        for d in dims:
            rubric = RUBRICS.get(d.key, {})
            if rubric:
                st.markdown(f"*{d.name}*")
                for level, desc in rubric.items():
                    st.markdown(f"&nbsp;&nbsp;**{level}:** {desc}")
        st.markdown("---")

if extract_btn and coach_notes.strip():
    with st.spinner("Analysing your notes..."):
        try:
            extracted = extract_scores_from_notes(
                coach_notes=coach_notes,
                session_theme=session_theme,
                session_type=session_type,
                player_profile=profile,
            )
            st.session_state.extracted = extracted
            st.session_state.extraction_done = True
            st.success(f"Extracted {len(extracted)} dimension scores.")
        except Exception as e:
            st.error(f"Extraction failed: {e}")
            st.session_state.extraction_done = False

if manual_btn:
    st.session_state.extraction_done = True
    st.session_state.extracted = {}

# ---- review & adjust scores -------------------------------------------------

if st.session_state.extraction_done:
    st.markdown("### Review & Adjust Scores")
    st.caption(
        "Review the AI-extracted scores below. Adjust any that don't match your assessment. "
        "Leave dimensions at 0 if they weren't observed in this session."
    )

    extracted = st.session_state.extracted
    adjusted_scores: dict[str, float] = {}

    with st.form("review_scores"):
        for cat in CATEGORIES:
            st.markdown(f"**{cat.capitalize()}**")
            dims = CATEGORY_DIMS[cat]
            cols = st.columns(len(dims))
            for i, d in enumerate(dims):
                ai_score = extracted.get(d.key, 0.0)
                current_epm = profile["flat_scores"].get(d.key, 5.0)
                help_text = f"Current EPM: {current_epm:.1f}"
                if ai_score > 0:
                    help_text += f" | AI suggested: {ai_score:.1f}"

                val = cols[i].number_input(
                    f"{d.name}",
                    min_value=0.0, max_value=10.0,
                    value=round(ai_score, 1),
                    step=0.5,
                    help=help_text,
                    key=f"score_{d.key}",
                )
                if val > 0:
                    adjusted_scores[d.key] = val

        st.divider()

        # Summary before save
        if adjusted_scores:
            st.markdown(f"**Scoring {len(adjusted_scores)} dimensions** from this session.")

        coach_adjusted = any(
            adjusted_scores.get(k, 0) != extracted.get(k, 0)
            for k in set(list(adjusted_scores.keys()) + list(extracted.keys()))
        )

        save_btn = st.form_submit_button("Save Session & Update Scores", type="primary")

        if save_btn:
            if not adjusted_scores:
                st.warning("No scores to save. Rate at least one dimension.")
            else:
                # Map transfer radio to db value
                transfer_val = None
                if transfer == "Yes — skills transferred":
                    transfer_val = True
                elif transfer == "No — didn't transfer yet":
                    transfer_val = False

                # Save observation
                save_observation(
                    obs_date=session_date.isoformat(),
                    player_id=selected_id,
                    session_type=session_type,
                    theme=session_theme,
                    coach_notes=coach_notes,
                    extracted_scores=adjusted_scores,
                    coach_adjusted=coach_adjusted,
                    transfer_observed=transfer_val,
                )

                # Update EPM via EMA
                updates = update_scores_from_observation(selected_id, adjusted_scores)

                st.success("Session saved and EPM updated!")

                # Show what changed
                st.markdown("### EPM Updates")
                for dim_key, info in updates.items():
                    meta = DIM_BY_KEY[dim_key]
                    delta = info["new_score"] - info["previous"]
                    direction = "+" if delta > 0 else "-" if delta < 0 else "="
                    st.markdown(
                        f"**{meta.name}**: "
                        f"{info['previous']:.1f} → {info['new_score']:.1f} ({direction}) "
                        f"*observed: {info['observed']:.1f}, {info['confidence']}, "
                        f"{info['observations']} total obs*"
                    )

                # Reset state
                st.session_state.extracted = {}
                st.session_state.extraction_done = False
