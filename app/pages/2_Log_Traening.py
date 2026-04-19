"""Log Træning – Registrer observationer og opdater EPM-scores."""

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

st.set_page_config(page_title="Log Træning – KP13", layout="wide")
apply_theme()
st.title("Log Træning")

# ---- player selector ---------------------------------------------------------

players = get_players()
if not players:
    st.warning("Ingen spillere registreret. Gå til Spilleroversigt for at tilføje en spiller.")
    st.stop()

player_options = {p["id"]: p["name"] for p in players}
selected_id = st.selectbox(
    "Spiller",
    options=list(player_options.keys()),
    format_func=lambda pid: player_options[pid],
)

profile = get_player_profile(selected_id)

# ---- session metadata --------------------------------------------------------

col1, col2, col3 = st.columns(3)
with col1:
    session_date = st.date_input("Sessionsdato", value=date.today())
with col2:
    session_type = st.selectbox(
        "Sessionstype",
        ["coached", "team_observation", "match", "home"],
        format_func=lambda x: {
            "coached": "Individuel træning",
            "team_observation": "Holdtræning",
            "match": "Kamp",
            "home": "Hjemmetræning",
        }.get(x, x),
    )
with col3:
    session_theme = st.text_input("Tema", placeholder="Fx. Dribling med fart, Første touch på halvvending")

# ---- transfer check ----------------------------------------------------------

recent = get_observations(selected_id, limit=3)
if recent:
    with st.expander("Transfertjek — Viste tidligere arbejde sig?"):
        st.caption("Overførte færdigheder fra sidste individuelle session til hold/kampsituationen?")
        last_session = recent[0]
        st.markdown(f"**Seneste session:** {last_session['date']} — {last_session.get('theme', 'N/A')}")
        transfer = st.radio(
            "Transfer observeret?",
            options=["Ikke relevant", "Ja — færdigheder overført", "Delvist", "Nej — ikke overført endnu"],
            horizontal=True,
        )
else:
    transfer = "Ikke relevant"

# ---- coach notes -------------------------------------------------------------

st.subheader("Kaspers noter")
st.caption(
    "Skriv dine observationer naturligt. AI'en udtrækker EPM-dimensionscores. "
    "Skriv om hvad du så — teknik, beslutninger, attitude, indsats, specifikke øjeblikke."
)

coach_notes = st.text_area(
    "Sessionsobservationer",
    height=250,
    placeholder=(
        "Eksempel: Felix viste stor forbedring i første touch på halvvending i dag. "
        "Kropsholdning var åben, første touch var fremad. Men da der åbnede sig plads til at drive, "
        "valgte han stadig den sikre aflevering 3 ud af 4 gange. Beslutningen om at drive er ikke automatisk endnu. "
        "Energi og indsats var høj hele vejen. Nød 1v1-afslutningsøvelsen til sidst."
    ),
)

# ---- AI extraction -----------------------------------------------------------

st.divider()
st.subheader("Udviklingsscore")

if "extracted" not in st.session_state:
    st.session_state.extracted = {}
if "extraction_done" not in st.session_state:
    st.session_state.extraction_done = False

col_extract, col_manual = st.columns(2)

with col_extract:
    extract_btn = st.button(
        "Udtræk scores med AI",
        disabled=not coach_notes.strip() or not ANTHROPIC_API_KEY,
        type="primary",
    )
    if not ANTHROPIC_API_KEY:
        st.caption("Tilføj ANTHROPIC_API_KEY i .env for at aktivere AI-udtrækning.")

with col_manual:
    manual_btn = st.button("Score manuelt")

# ---- scoring rubric reference ------------------------------------------------

with st.expander("Scoreguide — hvad ser hvert niveau ud som?"):
    CATEGORY_LABELS = {"technical": "Teknisk", "physical": "Fysisk", "cognitive": "Spilforståelse", "mental": "Mentalitet"}
    for cat in CATEGORIES:
        dims = CATEGORY_DIMS[cat]
        st.markdown(f"**{CATEGORY_LABELS.get(cat, cat.capitalize())}**")
        for d in dims:
            rubric = RUBRICS.get(d.key, {})
            if rubric:
                st.markdown(f"*{d.name}*")
                for level, desc in rubric.items():
                    st.markdown(f"&nbsp;&nbsp;**{level}:** {desc}")
        st.markdown("---")

if extract_btn and coach_notes.strip():
    with st.spinner("Analyserer dine noter..."):
        try:
            extracted = extract_scores_from_notes(
                coach_notes=coach_notes,
                session_theme=session_theme,
                session_type=session_type,
                player_profile=profile,
            )
            st.session_state.extracted = extracted
            st.session_state.extraction_done = True
            st.success(f"Udtrukket {len(extracted)} dimensionscores.")
        except Exception as e:
            st.error(f"Udtrækning fejlede: {e}")
            st.session_state.extraction_done = False

if manual_btn:
    st.session_state.extraction_done = True
    st.session_state.extracted = {}

# ---- review & adjust scores -------------------------------------------------

if st.session_state.extraction_done:
    st.markdown("### Gennemse og justér scores")
    st.caption(
        "Gennemse de AI-udtrukne scores nedenfor. Justér dem der ikke stemmer overens med din vurdering. "
        "Lad dimensioner stå på 0 hvis de ikke blev observeret i denne session."
    )

    extracted = st.session_state.extracted
    adjusted_scores: dict[str, float] = {}
    CATEGORY_LABELS = {"technical": "Teknisk", "physical": "Fysisk", "cognitive": "Spilforståelse", "mental": "Mentalitet"}

    with st.form("review_scores"):
        for cat in CATEGORIES:
            st.markdown(f"**{CATEGORY_LABELS.get(cat, cat.capitalize())}**")
            dims = CATEGORY_DIMS[cat]
            cols = st.columns(len(dims))
            for i, d in enumerate(dims):
                ai_score = extracted.get(d.key, 0.0)
                current_epm = profile["flat_scores"].get(d.key, 5.0)
                help_text = f"Nuværende EPM: {current_epm:.1f}"
                if ai_score > 0:
                    help_text += f" | AI foreslog: {ai_score:.1f}"

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

        if adjusted_scores:
            st.markdown(f"**Scorer {len(adjusted_scores)} dimensioner** fra denne session.")

        coach_adjusted = any(
            adjusted_scores.get(k, 0) != extracted.get(k, 0)
            for k in set(list(adjusted_scores.keys()) + list(extracted.keys()))
        )

        save_btn = st.form_submit_button("Gem session og opdater scores", type="primary")

        if save_btn:
            if not adjusted_scores:
                st.warning("Ingen scores at gemme. Vurder mindst én dimension.")
            else:
                transfer_val = None
                if transfer == "Ja — færdigheder overført":
                    transfer_val = True
                elif transfer == "Nej — ikke overført endnu":
                    transfer_val = False

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

                updates = update_scores_from_observation(selected_id, adjusted_scores)
                st.success("Session gemt og EPM opdateret!")

                st.markdown("### EPM-opdateringer")
                for dim_key, info in updates.items():
                    meta = DIM_BY_KEY[dim_key]
                    delta = info["new_score"] - info["previous"]
                    direction = "+" if delta > 0 else "-" if delta < 0 else "="
                    st.markdown(
                        f"**{meta.name}**: "
                        f"{info['previous']:.1f} → {info['new_score']:.1f} ({direction}{abs(delta):.2f}) "
                        f"*observeret: {info['observed']:.1f}, {info['confidence']}, "
                        f"{info['observations']} obs i alt*"
                    )

                st.session_state.extracted = {}
                st.session_state.extraction_done = False
