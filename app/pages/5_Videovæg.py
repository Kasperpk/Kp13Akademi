"""Videovæg — spillere poster træningsvideoer, Kasper giver feedback."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st

from core.database import (
    get_players, get_videos, add_video,
    update_video_coach_notes, delete_video,
)
from core.cloudinary_upload import upload_video as cloudinary_upload, is_configured
from core.theme import apply_theme
from core.auth import player_selector, get_player_id_from_url

st.set_page_config(page_title="Videovæg – KP13", layout="wide")
apply_theme()

_VIDEO_TYPE_LABELS = {
    "player_training":  "Min træning",
    "coach_reference":  "Kaspers reference",
    "target_video":     "Sådan skal det se ud",
}

_VIDEO_TYPE_COLORS = {
    "player_training":  "#3B82F6",
    "coach_reference":  "#10B981",
    "target_video":     "#F59E0B",
}


def _youtube_id(url: str) -> str | None:
    """Extract YouTube video ID from various URL formats."""
    import re
    patterns = [
        r"(?:v=|youtu\.be/|embed/)([A-Za-z0-9_-]{11})",
        r"^([A-Za-z0-9_-]{11})$",
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return None


def _render_video(url: str) -> None:
    vid_id = _youtube_id(url)
    if vid_id:
        st.markdown(
            f'<iframe width="100%" height="280" '
            f'src="https://www.youtube-nocookie.com/embed/{vid_id}" '
            f'frameborder="0" allowfullscreen style="border-radius:8px;"></iframe>',
            unsafe_allow_html=True,
        )
    else:
        # Cloudinary or direct video URL
        st.video(url)


# ---- player selector ---------------------------------------------------------

players = get_players()
if not players:
    st.info("Ingen spillere registreret endnu.")
    st.stop()

selected_id = player_selector(players)
_, is_player = get_player_id_from_url(players)

player_name = next(p["name"] for p in players if p["id"] == selected_id).split()[0]

st.title(f"Videovæg — {player_name}")
st.caption("Her kan du se dine træningsvideoer, Kaspers referencevideoer og feedback.")

st.markdown("---")

# ---- post new video ----------------------------------------------------------

with st.expander("＋ Del en træningsvideo" if is_player else "＋ Tilføj video"):
    if not is_player:
        new_type = st.selectbox(
            "Type",
            options=list(_VIDEO_TYPE_LABELS.keys()),
            format_func=lambda k: _VIDEO_TYPE_LABELS[k],
        )
    else:
        new_type = "player_training"

    new_title = st.text_input(
        "Titel",
        placeholder="Fx: Sole rolls med venstre ben — uge 17",
    )
    new_desc = st.text_area(
        "Beskrivelse (valgfrit)",
        placeholder="Fx: Fokus på at holde bolden tæt og skifte retning hurtigt",
        height=70,
    )

    tab_upload, tab_youtube = st.tabs(["⬆️ Upload direkte", "🔗 YouTube-link"])

    with tab_upload:
        if is_configured():
            uploaded_file = st.file_uploader(
                "Vælg videofil",
                type=["mp4", "mov", "avi", "mkv"],
                label_visibility="collapsed",
            )
            if st.button("Upload video", type="primary", key="btn_upload"):
                if not new_title.strip():
                    st.error("Giv videoen en titel.")
                elif not uploaded_file:
                    st.error("Vælg en videofil.")
                else:
                    with st.spinner("Uploader video..."):
                        try:
                            url = cloudinary_upload(
                                uploaded_file.read(),
                                player_id=selected_id,
                                filename=uploaded_file.name,
                            )
                            add_video(
                                player_id=selected_id,
                                title=new_title.strip(),
                                video_url=url,
                                posted_by="player" if is_player else "coach",
                                video_type=new_type,
                                description=new_desc.strip(),
                            )
                            st.success("Video uploadet!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Upload fejlede: {e}")
        else:
            st.warning("Cloudinary er ikke konfigureret. Tilføj CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY og CLOUDINARY_API_SECRET i secrets.")

    with tab_youtube:
        new_url = st.text_input(
            "YouTube-link",
            placeholder="https://www.youtube.com/watch?v=...",
        )
        if st.button("Tilføj video", type="primary", key="btn_youtube"):
            if not new_title.strip():
                st.error("Giv videoen en titel.")
            elif not new_url.strip():
                st.error("Indsæt et YouTube-link.")
            else:
                add_video(
                    player_id=selected_id,
                    title=new_title.strip(),
                    video_url=new_url.strip(),
                    posted_by="player" if is_player else "coach",
                    video_type=new_type,
                    description=new_desc.strip(),
                )
                st.success("Video tilføjet!")
                st.rerun()

st.markdown("---")

# ---- video feed --------------------------------------------------------------

videos = get_videos(selected_id)

if not videos:
    st.info("Ingen videoer endnu. Del din første træningsvideo herover!")
    st.stop()

# Group by type: coach reference / target first, then player training
coach_vids = [v for v in videos if v["video_type"] in ("coach_reference", "target_video")]
player_vids = [v for v in videos if v["video_type"] == "player_training"]

# ---- Coach reference / target videos ----------------------------------------

if coach_vids:
    st.markdown("### Fra Kasper")
    for v in coach_vids:
        color = _VIDEO_TYPE_COLORS.get(v["video_type"], "#6B7280")
        label = _VIDEO_TYPE_LABELS.get(v["video_type"], v["video_type"])
        st.markdown(
            f'<span style="background:{color};color:white;border-radius:4px;'
            f'padding:2px 8px;font-size:0.75rem;">{label}</span>',
            unsafe_allow_html=True,
        )
        st.markdown(f"**{v['title']}**")
        if v.get("description"):
            st.caption(v["description"])
        _render_video(v["video_url"])

        if v.get("coach_notes"):
            st.markdown(
                f'<div style="background:#1A1D27;border-left:3px solid #3B82F6;'
                f'padding:10px 14px;border-radius:0 6px 6px 0;margin:8px 0;">'
                f'<span style="font-size:0.8rem;color:#9CA3AF;">Kaspers note</span><br>'
                f'{v["coach_notes"]}</div>',
                unsafe_allow_html=True,
            )

        if not is_player:
            with st.expander("Rediger note"):
                new_note = st.text_area(
                    "Kaspers feedback",
                    value=v.get("coach_notes", ""),
                    key=f"note_{v['id']}",
                    height=80,
                )
                c1, c2 = st.columns(2)
                if c1.button("Gem note", key=f"savenote_{v['id']}"):
                    update_video_coach_notes(v["id"], new_note)
                    st.rerun()
                if c2.button("Slet video", key=f"del_{v['id']}"):
                    delete_video(v["id"])
                    st.rerun()

        st.markdown("---")

# ---- Player training videos --------------------------------------------------

if player_vids:
    st.markdown("### Træningsvideoer")
    for v in player_vids:
        posted = "dig" if v["posted_by"] == "player" else "Kasper"
        st.markdown(
            f'<span style="background:#3B82F6;color:white;border-radius:4px;'
            f'padding:2px 8px;font-size:0.75rem;">Min træning</span>',
            unsafe_allow_html=True,
        )
        st.markdown(f"**{v['title']}**")
        st.caption(f"Delt af {posted} · {v['created_at'][:10]}")
        if v.get("description"):
            st.caption(v["description"])
        _render_video(v["video_url"])

        if v.get("coach_notes"):
            st.markdown(
                f'<div style="background:#1A1D27;border-left:3px solid #10B981;'
                f'padding:10px 14px;border-radius:0 6px 6px 0;margin:8px 0;">'
                f'<span style="font-size:0.8rem;color:#9CA3AF;">Kaspers feedback</span><br>'
                f'{v["coach_notes"]}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.caption("_Ingen feedback endnu_")

        # Coach: add/edit feedback + delete
        if not is_player:
            with st.expander("Giv feedback / slet"):
                new_note = st.text_area(
                    "Feedback til spilleren",
                    value=v.get("coach_notes", ""),
                    key=f"pnote_{v['id']}",
                    height=100,
                    placeholder="Fx: God rytme på sole rolls! Prøv at holde bolden endnu tættere på foden — max 20 cm afstand...",
                )
                c1, c2 = st.columns(2)
                if c1.button("Gem feedback", key=f"psave_{v['id']}", type="primary"):
                    update_video_coach_notes(v["id"], new_note)
                    st.rerun()
                if c2.button("Slet video", key=f"pdel_{v['id']}"):
                    delete_video(v["id"])
                    st.rerun()

        st.markdown("---")
