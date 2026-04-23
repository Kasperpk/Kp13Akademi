"""Onboarding & Baseline workflow for new and existing players."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st

from core.auth import require_coach
from core.database import (
    get_epm_history,
    get_players,
    save_player_assessment,
    get_player_assessments,
    set_epm_score,
)
from core.epm import DIM_BY_KEY, get_player_profile
from core.onboarding import key_metrics_snapshot, suggest_epm_from_measurements
from core.clients_loader import append_to_ongoing
from core.charts import multi_trend
from core.theme import apply_theme, score_to_stage

st.set_page_config(page_title="Onboarding & Baseline – KP13", layout="wide")
apply_theme()
require_coach()

st.title("Onboarding & Baseline")
st.caption(
    "Struktureret onboarding med målbare tests + dyb spillerforståelse. "
    "Brug samme flow til re-tests for at holde baseline opdateret."
)

players = get_players()
if not players:
    st.info("Ingen spillere registreret endnu.")
    st.stop()

player_options = {p["id"]: p["name"] for p in players}
player_id = st.selectbox(
    "Spiller",
    options=list(player_options.keys()),
    format_func=lambda pid: player_options[pid],
)

if not player_id:
    st.info("Vælg en spiller for at fortsætte.")
    st.stop()

profile = get_player_profile(player_id)
if not profile:
    st.error("Spiller ikke fundet.")
    st.stop()

player = profile["player"]

st.markdown(
    f"**{player['name']}** · {player.get('age_group', '')} · {player.get('position', '')}"
)

onboarding_tab, questions_tab, overview_tab = st.tabs(
    ["1) Målbar Baseline", "2) Dybde-Spørgsmål", "3) Udviklingsoverblik"]
)

with onboarding_tab:
    st.subheader("Første testpakke")
    st.caption(
        "Registrer objective målinger. Appen foreslår baseline-scores, som du kan justere "
        "og anvende direkte i EPM."
    )

    with st.form("onboarding_metrics"):
        c1, c2, c3 = st.columns(3)
        with c1:
            sprint_10m = st.number_input("10m sprint (sek)", min_value=1.0, max_value=8.0, value=2.6, step=0.01)
            dribble_10m = st.number_input("10m dribling (sek)", min_value=1.2, max_value=10.0, value=3.2, step=0.01)
            t_drill = st.number_input("T-drill (sek)", min_value=6.0, max_value=20.0, value=11.0, step=0.01)
        with c2:
            decision_pct = st.number_input("Decision intelligence (%)", min_value=0.0, max_value=100.0, value=50.0, step=1.0)
            shots_on_target = st.number_input("Afslutninger på mål /10", min_value=0.0, max_value=10.0, value=4.0, step=1.0)
        with c3:
            wall_right = st.number_input("Vægpasninger højre /30s", min_value=0.0, max_value=60.0, value=18.0, step=1.0)
            wall_left = st.number_input("Vægpasninger venstre /30s", min_value=0.0, max_value=60.0, value=12.0, step=1.0)

        assessment_date = st.date_input("Dato", value=date.today())
        assessment_type = st.selectbox(
            "Type",
            options=["onboarding_initial", "retest"],
            format_func=lambda t: "Første onboarding" if t == "onboarding_initial" else "Re-test",
        )
        notes = st.text_area("Noter", placeholder="Kontekst: underlag, træthed, motivation, forhold som påvirker testen")
        apply_to_epm = st.checkbox("Anvend foreslåede scores i EPM nu", value=True)

        submit_metrics = st.form_submit_button("Gem baseline-test", type="primary")

    measurements = {
        "sprint_10m_seconds": sprint_10m,
        "dribble_10m_seconds": dribble_10m,
        "t_drill_seconds": t_drill,
        "decision_intelligence_pct": decision_pct,
        "shots_on_target_10": shots_on_target,
        "wall_passes_right_30s": wall_right,
        "wall_passes_left_30s": wall_left,
    }
    suggested = suggest_epm_from_measurements(measurements)

    if suggested:
        st.markdown("### Foreslået baseline")
        for dim_key, score in sorted(suggested.items()):
            dim_name = DIM_BY_KEY[dim_key].name if dim_key in DIM_BY_KEY else dim_key
            stage = score_to_stage(score)
            st.markdown(f"- **{dim_name}**: {score:.1f}/10 ({stage})")

    if submit_metrics:
        applied_scores: dict[str, float] = {}
        if apply_to_epm:
            obs_map = {
                d["key"]: d.get("observations", 0)
                for cat in profile["scores"].values()
                for d in cat
            }
            for dim_key, score in suggested.items():
                set_epm_score(player_id, dim_key, score, confidence="manual", observation_count=obs_map.get(dim_key, 0))
                applied_scores[dim_key] = score

        save_player_assessment(
            player_id=player_id,
            assessment_date=assessment_date.isoformat(),
            assessment_type=assessment_type,
            metrics=measurements,
            suggested_scores=suggested,
            applied_scores=applied_scores,
            notes=notes,
        )

        try:
            summary_lines = [
                "Målbar baseline-test gemt.",
                "",
                f"10m sprint: {sprint_10m:.2f}s",
                f"10m dribling: {dribble_10m:.2f}s",
                f"Decision intelligence: {decision_pct:.0f}%",
                f"T-drill: {t_drill:.2f}s",
            ]
            if notes.strip():
                summary_lines.extend(["", f"Noter: {notes.strip()}"])
            append_to_ongoing(
                player_id=player_id,
                entry_date=assessment_date,
                title="Onboarding baseline",
                body="\n".join(summary_lines),
            )
        except Exception:
            # Markdown append errors should not block DB save.
            pass

        st.success("Baseline-test gemt.")
        if apply_to_epm and suggested:
            st.info("Foreslåede scores er anvendt i EPM.")
        st.rerun()

with questions_tab:
    st.subheader("Dybde-spørgsmål")
    st.caption(
        "Disse svar giver kontekst til baseline: motivation, læringsstil, pres-triggere og miljø. "
        "Gemmes som assessment-data og kan bruges i spillerprofil, forældrekommunikation og planlægning."
    )

    with st.form("onboarding_questions"):
        q1 = st.text_area("Hvad elsker spilleren mest ved fodbold?")
        q2 = st.text_area("Hvornår falder niveauet typisk (stress, tempo, efter fejl)?")
        q3 = st.text_area("Hvordan lærer spilleren bedst (vise, forklaring, repetition, konkurrence)?")
        q4 = st.text_area("Hvilke mål har spilleren selv de næste 3 måneder?")
        q5 = st.text_area("Hvad ønsker forældre mest støtte til i hverdagen?")
        q_notes = st.text_area("Ekstra noter")
        q_date = st.date_input("Dato for spørgsmål", value=date.today(), key="q_date")
        save_questions = st.form_submit_button("Gem dybde-spørgsmål", type="primary")

    if save_questions:
        questionnaire = {
            "love_of_game": q1.strip(),
            "performance_drop_triggers": q2.strip(),
            "learning_style": q3.strip(),
            "three_month_player_goal": q4.strip(),
            "parent_support_need": q5.strip(),
        }
        save_player_assessment(
            player_id=player_id,
            assessment_date=q_date.isoformat(),
            assessment_type="onboarding_deep_questions",
            questionnaire=questionnaire,
            notes=q_notes.strip(),
        )

        try:
            answer_lines = [
                "Dybde-spørgsmål gennemført.",
                "",
                f"Spillerens motivation: {q1.strip() or '-'}",
                f"Trigger for fald: {q2.strip() or '-'}",
                f"Læringsstil: {q3.strip() or '-'}",
                f"3-måneders mål: {q4.strip() or '-'}",
                f"Forældrebehov: {q5.strip() or '-'}",
            ]
            if q_notes.strip():
                answer_lines.extend(["", f"Noter: {q_notes.strip()}"])
            append_to_ongoing(
                player_id=player_id,
                entry_date=q_date,
                title="Onboarding dybde-spørgsmål",
                body="\n".join(answer_lines),
            )
        except Exception:
            pass

        st.success("Dybde-spørgsmål gemt.")
        st.rerun()

with overview_tab:
    st.subheader("Udvikling af key metrics")

    assessments = get_player_assessments(player_id, limit=30)
    if assessments:
        rows = []
        for a in assessments:
            metrics = key_metrics_snapshot(a.get("metrics_json", {}))
            rows.append(
                {
                    "dato": a["assessment_date"],
                    "type": a["assessment_type"],
                    "sprint_10m": metrics.get("sprint_10m_seconds"),
                    "dribble_10m": metrics.get("dribble_10m_seconds"),
                    "decision_%": metrics.get("decision_intelligence_pct"),
                }
            )
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("Ingen assessments endnu.")

    st.markdown("### EPM-udvikling i nøgleområder")
    tracked_dims = ["acceleration", "dribbling_speed", "decision_speed", "game_reading"]
    history_by_dim = {k: get_epm_history(player_id, k, limit=50) for k in tracked_dims}
    fig = multi_trend(history_by_dim, title=f"{player['name']} — onboarding til progression")
    st.plotly_chart(fig, use_container_width=True)
