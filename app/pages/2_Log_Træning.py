"""Log Træning – registrer en træning så den tæller med i samlet træningstid."""

import sys
from pathlib import Path
from datetime import date

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st

from core.auth import require_coach
from core.clients_loader import append_to_ongoing
from core.database import get_players, get_training_stats, save_observation
from core.theme import apply_theme

st.set_page_config(page_title="Log Træning – KP13", layout="wide")
apply_theme()
require_coach()
st.title("Log Træning")
st.caption("Registrér en træning. Den tælles med i spillerens samlede træningstid.")

players = get_players()
if not players:
    st.warning("Ingen spillere registreret. Gå til Spilleranalyse for at tilføje en spiller.")
    st.stop()

player_options = {p["id"]: p["name"] for p in players}
selected_id = st.selectbox(
    "Spiller",
    options=list(player_options.keys()),
    format_func=lambda pid: player_options[pid],
)

# Minutes per session type — must match _SESSION_TYPE_MINUTES in core/database.py.
SESSION_TYPE_MINUTES = {
    "coached": 60,
    "team": 90,
    "match": 90,
    "home": 30,
}
SESSION_TYPE_LABELS = {
    "coached": "Individuel træning (60 min)",
    "team": "Holdtræning (90 min)",
    "match": "Kamp (90 min)",
    "home": "Hjemmetræning (30 min)",
}

with st.form("log_training"):
    col1, col2 = st.columns(2)
    with col1:
        session_date = st.date_input("Dato", value=date.today())
    with col2:
        session_type = st.selectbox(
            "Type",
            options=list(SESSION_TYPE_MINUTES.keys()),
            format_func=lambda t: SESSION_TYPE_LABELS[t],
        )

    theme = st.text_input("Tema (valgfri)", placeholder="Fx. Dribling med fart, første touch")
    notes = st.text_area(
        "Noter (valgfri)",
        height=120,
        placeholder="Kort beskrivelse af hvad der blev arbejdet med.",
    )

    minutes = SESSION_TYPE_MINUTES[session_type]
    st.caption(f"Bidrag til samlet træningstid: **{minutes} min** ({minutes/60:.1f} t)")

    submit = st.form_submit_button("Gem træning", type="primary")

if submit:
    save_observation(
        obs_date=session_date.isoformat(),
        player_id=selected_id,
        session_type=session_type,
        theme=theme,
        coach_notes=notes,
        extracted_scores={},
    )

    if notes.strip() or theme.strip():
        try:
            body_lines = []
            if theme.strip():
                body_lines.append(f"**Tema:** {theme.strip()}")
            if notes.strip():
                body_lines.append(notes.strip())
            append_to_ongoing(
                player_id=selected_id,
                entry_date=session_date,
                title=f"Træning ({SESSION_TYPE_LABELS[session_type].split(' (')[0]})",
                body="\n\n".join(body_lines),
            )
        except Exception:
            pass

    stats = get_training_stats(selected_id)
    total = stats["total"]
    week = stats["week"]
    st.success(f"Træning gemt — {minutes} min lagt til.")
    st.markdown(
        f"**{player_options[selected_id]}** — i alt: "
        f"{total['hours']} t over {total['sessions']} sessioner · "
        f"denne uge: {week['hours']} t"
    )
