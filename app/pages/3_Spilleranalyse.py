"""Spilleranalyse — samlet oversigt, baseline-måling, dybde-spørgsmål og 10-ugers review."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st

from core.auth import player_selector, require_coach
from core.charts import category_bars, epm_radar, multi_trend
from core.clients_loader import append_to_ongoing
from core.database import (
    get_epm_history,
    get_observations,
    get_player_assessments,
    get_players,
    save_player_assessment,
    set_epm_score,
    upsert_player,
)
from core.epm import (
    CATEGORIES,
    CATEGORY_DIMS,
    DIM_BY_KEY,
    DIMENSIONS,
    get_player_profile,
    identify_gaps,
    identify_strengths,
    initialise_player_epm,
)
from core.onboarding import key_metrics_snapshot, suggest_epm_from_measurements
from core.review import current_and_next
from core.theme import apply_theme, score_to_stage

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

st.set_page_config(page_title="Spilleranalyse – KP13", layout="wide")
apply_theme()
require_coach()

st.title("Spilleranalyse")

# ---- sidebar: player selector + add player ---------------------------------

players = get_players()

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

if not players:
    st.info("Tilføj en spiller fra sidepanelet for at komme i gang.")
    st.stop()

player_id = player_selector(players)
profile = get_player_profile(player_id)
if not profile:
    st.error("Spiller ikke fundet.")
    st.stop()

player = profile["player"]
flat = profile["flat_scores"]

# ---- header ----------------------------------------------------------------

gaps = identify_gaps(player_id, top_n=3)
strengths = identify_strengths(player_id, top_n=3)

h1, h2, h3 = st.columns([2, 1, 1])
with h1:
    st.header(player["name"])
    sub_parts = [player.get("age_group", ""), player.get("position", ""), player.get("club", "")]
    sub = " · ".join(p for p in sub_parts if p)
    if sub:
        st.caption(sub)
with h2:
    st.markdown("**Top huller**")
    if gaps:
        for g in gaps:
            st.markdown(f"- {g['name']}: **{g['score']:.1f}**")
    else:
        st.caption("_ingen data_")
with h3:
    st.markdown("**Styrker**")
    if strengths:
        for s in strengths:
            st.markdown(f"- {s['name']}: **{s['score']:.1f}**")
    else:
        st.caption("_ingen data_")

st.divider()

overview_tab, sessions_tab, baseline_tab, questions_tab, review_tab = st.tabs(
    ["Overblik", "Sessionshistorik", "Baseline-måling", "Dybde-spørgsmål", "10-ugers Review"]
)

# ---- tab: overblik ---------------------------------------------------------

with overview_tab:
    st.subheader("EPM Radar")
    st.plotly_chart(epm_radar(flat, player["name"]), use_container_width=True)

    st.subheader("Scoreoversigt")
    st.plotly_chart(category_bars(flat), use_container_width=True)

    for cat in CATEGORIES:
        dims = CATEGORY_DIMS[cat]
        st.markdown(f"**{_CATEGORY_LABELS.get(cat, cat.capitalize())}**")
        for d in dims:
            score = flat.get(d.key, 5.0)
            scores_data = profile["scores"].get(cat, [])
            dim_data = next((x for x in scores_data if x["key"] == d.key), {})
            conf = dim_data.get("confidence", "low")
            obs_count = dim_data.get("observations", 0)
            st.markdown(
                f"**{d.name}**: {score:.1f}/10 *[{conf}, {obs_count} obs]*"
            )

    st.divider()
    st.subheader("Udviklingsforløb")
    selected_dims = st.multiselect(
        "Vælg dimensioner at følge",
        options=[d.key for d in DIMENSIONS],
        default=[g["key"] for g in gaps[:3]],
        format_func=lambda k: DIM_BY_KEY[k].name,
        key="trend_dims",
    )
    if selected_dims:
        history_by_dim = {dk: get_epm_history(player_id, dk, limit=50) for dk in selected_dims}
        st.plotly_chart(
            multi_trend(history_by_dim, f"{player['name']} — Udviklingsforløb"),
            use_container_width=True,
        )
    else:
        st.info("Vælg dimensioner ovenfor for at se udviklingsforløb.")

    st.divider()
    st.subheader("Baseline-historik")
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
                    "long_jump_cm": metrics.get("long_jump_cm"),
                    "turn_sprint_no_ball": metrics.get("turn_sprint_no_ball_seconds"),
                    "turn_sprint_with_ball": metrics.get("turn_sprint_with_ball_seconds"),
                    "juggling_alt": metrics.get("juggling_alt_count"),
                    "taps_right": metrics.get("taps_right_15s"),
                    "taps_left": metrics.get("taps_left_15s"),
                    "first_touch_/10": metrics.get("first_touch_clean_10"),
                    "pass_right_/10": metrics.get("passing_right_5m_10"),
                    "pass_left_/10": metrics.get("passing_left_5m_10"),
                    "shots_/10": metrics.get("finishing_on_target_10"),
                }
            )
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        st.info("Ingen baseline-tests endnu — gå til **Baseline-måling**.")

    st.divider()
    with st.expander("Rediger EPM-scores manuelt"):
        st.caption("Justér scores direkte. Bruges til korrektioner uden for de regulære input-flows.")
        with st.form("manual_baseline"):
            new_scores: dict[str, float] = {}
            for cat in CATEGORIES:
                st.markdown(f"**{_CATEGORY_LABELS.get(cat, cat.capitalize())}**")
                cols = st.columns(len(CATEGORY_DIMS[cat]))
                for i, d in enumerate(CATEGORY_DIMS[cat]):
                    current = flat.get(d.key, 5.0)
                    new_scores[d.key] = cols[i].number_input(
                        f"{d.name}",
                        min_value=1.0, max_value=10.0,
                        value=current, step=0.5,
                        key=f"manual_{d.key}",
                    )
            save_manual = st.form_submit_button("Gem manuelle scores")
            if save_manual:
                for dim_key, score in new_scores.items():
                    obs_count = 0
                    for cat_dims in profile["scores"].values():
                        for dd in cat_dims:
                            if dd["key"] == dim_key:
                                obs_count = dd["observations"]
                                break
                    set_epm_score(player_id, dim_key, score, "manual", obs_count)
                st.success("Scores opdateret.")
                st.rerun()

# ---- tab: sessionshistorik ------------------------------------------------

with sessions_tab:
    st.subheader("Sessionshistorik")
    observations = get_observations(player_id, limit=20)
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
        st.info("Ingen sessioner logget endnu. Gå til **Log Træning** for at registrere.")

# ---- tab: baseline-måling --------------------------------------------------

with baseline_tab:
    st.subheader("Baseline-test")
    st.caption(
        "Registrér objektive målinger. Appen foreslår baseline-scores for de testbare "
        "EPM-dimensioner — kognitive og mentale dimensioner dækkes af 10-ugers reviewet."
    )

    with st.form("baseline_metrics"):
        st.markdown("**Atletisk grundlag**")
        c1, c2 = st.columns(2)
        with c1:
            sprint_10m = st.number_input(
                "10m sprint (sek)", min_value=1.0, max_value=8.0, value=2.6, step=0.01
            )
        with c2:
            long_jump_cm = st.number_input(
                "Stående længdespring (cm)", min_value=30, max_value=300, value=140, step=1
            )

        st.markdown("**Tempo med og uden bold** (2m ud / 2m hjem / 10m ud / 10m hjem)")
        c3, c4 = st.columns(2)
        with c3:
            turn_sprint_no_ball = st.number_input(
                "Vendings-sprint uden bold (sek)",
                min_value=3.0, max_value=20.0, value=7.0, step=0.01,
            )
        with c4:
            turn_sprint_with_ball = st.number_input(
                "Vendings-sprint med bold (sek)",
                min_value=3.0, max_value=20.0, value=8.0, step=0.01,
            )

        ball_tax = max(0.0, turn_sprint_with_ball - turn_sprint_no_ball)
        st.caption(f"Bold-skat (delta): **{ball_tax:.2f} s**")

        st.markdown("**Boldfærdighed**")
        c5, c6, c7 = st.columns(3)
        with c5:
            juggling_alt = st.number_input(
                "Jonglering, begge fødder (max af 3)",
                min_value=0, max_value=500, value=10, step=1,
            )
        with c6:
            taps_right = st.number_input(
                "Inde-ude tæt højre, 15 s (antal)",
                min_value=0, max_value=200, value=30, step=1,
            )
        with c7:
            taps_left = st.number_input(
                "Inde-ude tæt venstre, 15 s (antal)",
                min_value=0, max_value=200, value=25, step=1,
            )

        st.markdown("**Tekniske tests** (10 forsøg pr. test)")
        st.caption(
            "First touch: trænerpas fra 8 m, kontrol indenfor 1,5 m cirkel /10. "
            "Pasninger: 5 m kegle-mål, 10 forsøg pr. fod. "
            "Afslutninger: skud på mål med kegler /10."
        )
        c8, c9, c10, c11 = st.columns(4)
        with c8:
            first_touch_clean = st.number_input(
                "First touch /10", min_value=0, max_value=10, value=5, step=1,
            )
        with c9:
            passing_right = st.number_input(
                "Pasning højre /10", min_value=0, max_value=10, value=5, step=1,
            )
        with c10:
            passing_left = st.number_input(
                "Pasning venstre /10", min_value=0, max_value=10, value=3, step=1,
            )
        with c11:
            finishing = st.number_input(
                "Afslutning /10", min_value=0, max_value=10, value=4, step=1,
            )

        st.markdown("**Selv-vurdering** (1–10)")
        c12, c13, c14 = st.columns(3)
        with c12:
            self_confidence_1v1 = st.slider("Selvtillid i 1v1", 1, 10, 5)
        with c13:
            self_weak_foot_comfort = st.slider("Komfort med svagt ben", 1, 10, 5)
        with c14:
            self_focus_training = st.slider("Fokus i træning", 1, 10, 5)

        assessment_date = st.date_input("Dato", value=date.today())
        assessment_type = st.selectbox(
            "Type",
            options=["onboarding_initial", "retest"],
            format_func=lambda t: "Første onboarding" if t == "onboarding_initial" else "Re-test",
        )
        notes = st.text_area(
            "Noter",
            placeholder="Kontekst: underlag, træthed, motivation, forhold som påvirker testen",
        )
        apply_to_epm = st.checkbox("Anvend foreslåede scores i EPM nu", value=True)

        submit_metrics = st.form_submit_button("Gem baseline-test", type="primary")

    measurements = {
        "sprint_10m_seconds": sprint_10m,
        "long_jump_cm": float(long_jump_cm),
        "turn_sprint_no_ball_seconds": turn_sprint_no_ball,
        "turn_sprint_with_ball_seconds": turn_sprint_with_ball,
        "ball_tax_seconds": ball_tax,
        "juggling_alt_count": float(juggling_alt),
        "taps_right_15s": float(taps_right),
        "taps_left_15s": float(taps_left),
        "first_touch_clean_10": float(first_touch_clean),
        "passing_right_5m_10": float(passing_right),
        "passing_left_5m_10": float(passing_left),
        "finishing_on_target_10": float(finishing),
        "self_confidence_1v1": float(self_confidence_1v1),
        "self_weak_foot_comfort": float(self_weak_foot_comfort),
        "self_focus_training": float(self_focus_training),
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
                "Baseline-test gemt.",
                "",
                f"10m sprint: {sprint_10m:.2f} s",
                f"Stående længdespring: {long_jump_cm} cm",
                f"Vendings-sprint uden bold: {turn_sprint_no_ball:.2f} s",
                f"Vendings-sprint med bold: {turn_sprint_with_ball:.2f} s",
                f"Bold-skat: {ball_tax:.2f} s",
                f"Jonglering (alt.): {juggling_alt}",
                f"Inde-ude højre 15s: {taps_right}",
                f"Inde-ude venstre 15s: {taps_left}",
                f"First touch /10: {first_touch_clean}",
                f"Pasning højre /10: {passing_right}",
                f"Pasning venstre /10: {passing_left}",
                f"Afslutning /10: {finishing}",
                "",
                f"Selvtillid 1v1: {self_confidence_1v1}/10",
                f"Komfort svagt ben: {self_weak_foot_comfort}/10",
                f"Fokus i træning: {self_focus_training}/10",
            ]
            if notes.strip():
                summary_lines.extend(["", f"Noter: {notes.strip()}"])
            append_to_ongoing(
                player_id=player_id,
                entry_date=assessment_date,
                title="Baseline-test",
                body="\n".join(summary_lines),
            )
        except Exception:
            pass

        st.success("Baseline-test gemt.")
        if apply_to_epm and suggested:
            st.info("Foreslåede scores er anvendt i EPM.")
        st.rerun()

# ---- tab: dybde-spørgsmål --------------------------------------------------

with questions_tab:
    st.subheader("Dybde-spørgsmål")
    st.caption(
        "Disse svar giver kontekst til baseline: motivation, læringsstil, pres-triggere og miljø. "
        "Gemmes som assessment-data og kan bruges i spillerprofil, forældrekommunikation og planlægning."
    )

    with st.form("deep_questions"):
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
                title="Dybde-spørgsmål",
                body="\n".join(answer_lines),
            )
        except Exception:
            pass

        st.success("Dybde-spørgsmål gemt.")
        st.rerun()

# ---- tab: 10-ugers review --------------------------------------------------

with review_tab:
    st.subheader("10-ugers Review")
    st.caption(
        f"Gennemgang af **{player['name']}**'s færdighedsniveauer. Tag tid til hver dimension — "
        "fortæl spilleren hvor de står nu, og hvad næste niveau ser ud som."
    )

    review_date = st.date_input("Review-dato", value=date.today(), key="review_date")

    _state_key_prefix = f"review::{player_id}::{review_date.isoformat()}"
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

    st.markdown("### Fokus de næste 10 uger")
    st.caption("Vælg 1–3 dimensioner spilleren primært arbejder med frem til næste review.")

    dim_options = {d.key: d.name for d in DIMENSIONS}
    focus = st.multiselect(
        "Fokusområder",
        options=list(dim_options.keys()),
        default=st.session_state[focus_key],
        format_func=lambda k: dim_options[k],
        max_selections=3,
        key=f"focus_select_{review_date.isoformat()}",
    )
    st.session_state[focus_key] = focus

    review_summary = st.text_area(
        "Samlet kommentar til spilleren (med i markdown-output)",
        placeholder="Hvad er den ene ting du vil have spilleren tager med sig fra denne samtale?",
        height=120,
        key=f"review_summary_{review_date.isoformat()}",
    )

    def _build_review_markdown() -> str:
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

    col_save, col_preview = st.columns([1, 1])

    if col_save.button("💾 Gem review", type="primary", key="save_review"):
        try:
            out_dir = _CLIENTS_DIR / player_id / "reviews"
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / f"{review_date.isoformat()}.md"
            out_path.write_text(_build_review_markdown(), encoding="utf-8")
            st.success(f"Gemt: `{out_path.relative_to(_ROOT)}`")
        except Exception as e:
            st.error(f"Kunne ikke gemme: {e}")

    with col_preview.expander("📄 Forhåndsvis markdown"):
        st.code(_build_review_markdown(), language="markdown")
