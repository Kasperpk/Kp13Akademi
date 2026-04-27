"""ELM (Entity Language Model) – Claude integration for coaching intelligence."""

from __future__ import annotations

import json
from typing import Any, Generator

import anthropic

from .config import ANTHROPIC_API_KEY, ANTHROPIC_MODEL
from .epm import DIMENSIONS, DIM_BY_KEY, CATEGORIES, CATEGORY_DIMS
from .rubrics import all_rubrics_text, rubric_for_dimension
from .skill_loader import load_reference, load_skill

# ---- client ------------------------------------------------------------------

def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


# ---- system prompt -----------------------------------------------------------

def _build_system_prompt(player_profile: dict[str, Any] | None = None) -> str:
    parts = [load_reference("session-design", "academy_context")]

    # List all dimensions
    for cat in CATEGORIES:
        dims = CATEGORY_DIMS[cat]
        parts.append(f"\n{cat.upper()}:")
        for d in dims:
            parts.append(f"  - {d.name} ({d.key}): {d.description}")

    if player_profile:
        p = player_profile["player"]
        parts.append(f"\n\nCURRENT PLAYER: {p['name']}")
        parts.append(f"Age group: {p.get('age_group', 'N/A')}")
        parts.append(f"Position: {p.get('position', 'N/A')}")
        parts.append(f"Dominant foot: {p.get('dominant_foot', 'N/A')}")
        parts.append(f"Club: {p.get('club', 'N/A')}")

        parts.append("\nEPM SCORES:")
        for cat, dims in player_profile["scores"].items():
            parts.append(f"  {cat.upper()}:")
            for d in dims:
                conf_tag = f" [{d['confidence']}]" if d["confidence"] != "high" else ""
                parts.append(f"    {d['name']}: {d['score']:.1f}/10{conf_tag}")

    return "\n".join(parts)


# ---- tool definitions for structured extraction ------------------------------

_EXTRACT_TOOL = {
    "name": "record_session_scores",
    "description": (
        "Extract EPM dimension scores (1-10) from coaching session notes. "
        "Only score dimensions that were clearly observed in the session. "
        "Use null for dimensions not observed or not applicable."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            d.key: {
                "type": ["number", "null"],
                "description": f"{d.name}: {d.description}. Score 1-10 or null if not observed.",
            }
            for d in DIMENSIONS
        },
        "required": [],
    },
}


# ---- extraction from coach notes --------------------------------------------

def extract_scores_from_notes(
    coach_notes: str,
    session_theme: str,
    session_type: str,
    player_profile: dict[str, Any],
    player_context: str = "",
) -> dict[str, float]:
    """Use Claude tool_use to extract structured EPM scores from free-text notes.

    `player_context` is the narrative material from the player's markdown files
    (profile + ongoing notes + recent session observations). When provided, the
    AI calibrates against the player's history rather than scoring in a vacuum.

    Returns dict of {dimension_key: score} for observed dimensions only.
    """
    client = _client()
    system = _build_system_prompt(player_profile)
    if player_context.strip():
        system += "\n\n=== PLAYER NARRATIVE CONTEXT ===\n" + player_context.strip()

    user_msg = f"""\
Session type: {session_type}
Session theme: {session_theme}

Coach notes (today's session):
{coach_notes}

SCORING RUBRIC — use these observable behaviours to calibrate your scores:
{all_rubrics_text()}

Score the player based on TODAY'S coach notes, calibrated against the player's \
narrative context (profile, ongoing notes, recent session observations) provided \
in the system prompt. The narrative tells you the player's baseline and trajectory; \
today's notes tell you what changed.

Only score dimensions where today's notes provide clear behavioural evidence. \
Match what you read to the rubric levels. Use the record_session_scores tool."""

    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=1024,
        system=system,
        tools=[_EXTRACT_TOOL],
        tool_choice={"type": "tool", "name": "record_session_scores"},
        messages=[{"role": "user", "content": user_msg}],
    )

    # Parse tool_use response
    for block in response.content:
        if block.type == "tool_use" and block.name == "record_session_scores":
            raw = block.input
            return {k: float(v) for k, v in raw.items() if v is not None}
    return {}


# ---- daily plan generation ---------------------------------------------------

def generate_daily_plan(
    player_profile: dict[str, Any],
    gaps: list[dict[str, Any]],
    strengths: list[dict[str, Any]],
    recent_sessions: list[dict[str, Any]],
    available_exercises: list[dict[str, Any]],
) -> str:
    """Generate a personalised daily home-training plan in Danish."""
    client = _client()
    system = _build_system_prompt(player_profile)
    player_name = player_profile["player"]["name"]

    def _fallback_daily_plan() -> str:
        chosen = available_exercises[:3]
        if not chosen:
            return (
                f"## Dagens træning for {player_name}\n\n"
                "### FOKUS\n"
                "Vi arbejder med førsteberøring, orientering og tempo i boldbehandling, så det bliver nemmere at spille fremad i kamp.\n\n"
                "### OPVARMNING (4 min)\n"
                "- 2 x 45 sek toe taps + 15 sek pause\n"
                "- 2 x 45 sek inside-outside touches + 15 sek pause\n\n"
                "### HOVEDBLOK (14 min)\n"
                "- 3 runder: 90 sek arbejde / 30 sek pause\n"
                "- Fokus: første touch væk fra pres, hovedet oppe før hver aktion\n\n"
                "### NEDKØLING (3 min)\n"
                "- Let jonglering og rolig mobilitet for ankler/hofter\n\n"
                "### KASPERS BESKED\n"
                f"{player_name}, gør det i kampfart i korte perioder - kvalitet først, så tempo.\n"
            )

        lines: list[str] = [
            f"## Dagens træning for {player_name}",
            "",
            "### FOKUS",
            "Vi træner konkrete kamphandlinger med høj kvalitet i førsteberøring, orientering og beslutning i fart.",
            "",
            "### OPVARMNING (4-5 min)",
            "- 2 x 45 sek let boldarbejde (inside/outside, toe taps) + 15 sek pause",
            "",
            "### HOVEDBLOK (12-15 min)",
        ]

        for idx, ex in enumerate(chosen, start=1):
            coaching_points = ex.get("coaching_points") or []
            cp_preview = "; ".join(coaching_points[:2]) if coaching_points else "Fokus pa timing, kontrol og retning i første touch"
            video_line = ex.get("video_url") or ex.get("video_search_url") or ""
            lines.extend([
                f"{idx}. **{ex.get('name', 'Øvelse')}** ({ex.get('duration_min', 5)} min)",
                f"   - Hvorfor: {ex.get('description', '')}",
                f"   - Setup: {ex.get('setup') or 'Lav en enkel bane med kegler og 1 bold'}",
                f"   - Coaching: {cp_preview}",
            ])
            if video_line:
                lines.append(f"   - Video: {video_line}")

        lines.extend([
            "",
            "### NEDKØLING (2-3 min)",
            "- Let udstrækning og 30-50 rolige jongleringer",
            "",
            "### KASPERS BESKED",
            f"{player_name}, hold kvaliteten i alle berøringer - det er sådan træning flytter sig til kamp.",
        ])
        return "\n".join(lines)

    recent_text = ""
    for s in recent_sessions[:5]:
        recent_text += f"\n- {s['date']} ({s['session_type']}): {s.get('theme', 'N/A')}"
        if s.get("coach_notes"):
            notes_preview = s["coach_notes"][:200]
            recent_text += f"\n  Notes: {notes_preview}"

    gaps_text = ", ".join(f"{g['name']} ({g['score']:.1f})" for g in gaps)
    strengths_text = ", ".join(f"{s['name']} ({s['score']:.1f})" for s in strengths)

    exercises_text = ""
    for ex in available_exercises[:20]:
        cp = ex.get("coaching_points") or []
        cp_text = "; ".join(cp[:3]) if cp else ""
        setup_text = ex.get("setup") or ""
        video_line = ex.get("video_url") or ex.get("video_search_url") or ""
        exercises_text += (
            f"\n- {ex['name']}: {ex['description']} ({ex['duration_min']}min, {ex['intensity']})"
            f"\n  Setup: {setup_text}"
            f"\n  Coaching points: {cp_text}"
            f"\n  Video: {video_line}"
        )

    user_msg = f"""\
Lav en hjemmetræningssession for i dag (15-25 minutter) for {player_profile['player']['name']}.

STØRSTE UDVIKLINGSOMRÅDER: {gaps_text}
STYRKER AT BYGGE VIDERE PÅ: {strengths_text}

SENESTE SESSIONER: {recent_text}

TILGÆNGELIGE ØVELSER:
{exercises_text}

Følg principperne og output-formatet i player-daily-plan skill'en (system prompt)."""

    system_with_skill = system + "\n\n" + load_skill("player-daily-plan")

    try:
        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=2048,
            system=system_with_skill,
            messages=[{"role": "user", "content": user_msg}],
        )
        return response.content[0].text
    except Exception:
        # Fallback keeps the app usable even if LLM provider/network is unavailable.
        return _fallback_daily_plan()


# ---- weekly parent summary ---------------------------------------------------

def generate_weekly_summary(
    player_profile: dict[str, Any],
    week_observations: list[dict[str, Any]],
    epm_history: list[dict[str, Any]],
    gaps: list[dict[str, Any]],
    strengths: list[dict[str, Any]],
) -> str:
    """Generate a natural-language weekly summary for parents."""
    client = _client()
    system = _build_system_prompt(player_profile)

    obs_text = ""
    for obs in week_observations:
        obs_text += f"\n### {obs['date']} — {obs['session_type']}: {obs.get('theme', 'N/A')}"
        if obs.get("coach_notes"):
            obs_text += f"\n{obs['coach_notes']}"
        if obs.get("extracted_scores"):
            scores_str = ", ".join(f"{k}: {v}" for k, v in obs["extracted_scores"].items())
            obs_text += f"\nScores: {scores_str}"

    gaps_text = ", ".join(f"{g['name']} ({g['score']:.1f})" for g in gaps)
    strengths_text = ", ".join(f"{s['name']} ({s['score']:.1f})" for s in strengths)

    player_name = player_profile["player"]["name"].split()[0]
    user_msg = f"""\
Skriv den ugentlige forældrebesked for {player_name} ({player_profile['player']['name']}).

UGENS SESSIONER:
{obs_text if obs_text else "Ingen sessioner registreret i denne uge."}

NUVÆRENDE STYRKER: {strengths_text}
NUVÆRENDE UDVIKLINGSOMRÅDER: {gaps_text}

Følg principperne, registret og strukturen i parent-comms skill'en (system prompt)."""

    system_with_skill = system + "\n\n" + load_skill("parent-comms")

    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=1500,
        system=system_with_skill,
        messages=[{"role": "user", "content": user_msg}],
    )
    return response.content[0].text


# ---- weekly schedule generation ---------------------------------------------
# Moved to app.core.agents.session_designer. Use `design_week(player_id, week_start)`
# from that module — it self-loads context and returns a Pydantic WeeklySchedule.

# ---- Danish weekly training plan ---------------------------------------------

# Age-group dimension priorities: higher weight = more important at this stage
_AGE_DIM_WEIGHTS: dict[str, dict[str, float]] = {
    "U7": {"ball_mastery": 2.0, "first_touch": 2.0, "weak_foot": 2.0, "joy": 2.0, "agility": 1.5},
    "U8": {"ball_mastery": 2.0, "first_touch": 2.0, "weak_foot": 2.0, "joy": 2.0, "agility": 1.5},
    "U9": {"ball_mastery": 2.0, "first_touch": 2.0, "weak_foot": 2.0, "joy": 1.5, "dribbling_speed": 1.5, "agility": 1.5},
    "U10": {"ball_mastery": 1.8, "first_touch": 1.8, "weak_foot": 1.8, "dribbling_speed": 1.5, "passing": 1.3},
    "U11": {"first_touch": 1.5, "passing": 1.5, "game_reading": 1.5, "decision_speed": 1.5, "ball_mastery": 1.3},
    "U12": {"passing": 1.5, "game_reading": 1.5, "decision_speed": 1.5, "positional_play": 1.3, "finishing": 1.3},
    "U13": {"game_reading": 1.5, "decision_speed": 1.5, "positional_play": 1.5, "passing": 1.3, "finishing": 1.3},
    "U14": {"game_reading": 1.5, "positional_play": 1.5, "finishing": 1.5, "resilience": 1.3, "intensity": 1.3},
    "U15": {"positional_play": 1.5, "game_reading": 1.5, "resilience": 1.5, "intensity": 1.5, "finishing": 1.3},
}


def _age_weighted_gaps(gaps: list[dict[str, Any]], age_group: str) -> list[dict[str, Any]]:
    """Re-rank gaps by multiplying gap size by age-group developmental weight."""
    weights = _AGE_DIM_WEIGHTS.get(age_group, {})
    scored = []
    for g in gaps:
        w = weights.get(g["key"], 1.0)
        scored.append((g, (10.0 - g["score"]) * w))
    scored.sort(key=lambda x: x[1], reverse=True)
    return [g for g, _ in scored]


def _load_la_masia() -> str:
    try:
        return load_reference("session-design", "la_masia")
    except FileNotFoundError:
        return ""


def _load_kp13_methodology() -> str:
    try:
        return load_reference("session-design", "kp13_methodology")
    except FileNotFoundError:
        return ""


def generate_weekly_plan_danish(
    player: dict[str, Any],
    gaps: list[dict[str, Any]],
    strengths: list[dict[str, Any]],
    recent_observations: list[dict[str, Any]],
    chosen_days: list[str],
    available_exercises: list[dict[str, Any]],
    player_goals: str = "",
    sessions_per_week: int | None = None,
) -> str:
    """Generate a full weekly training plan in Danish.

    Priority for focus selection:
    1. Coach notes from recent sessions (explicit flags override everything)
    2. Age-weighted EPM gaps (most impactful dimension to improve right now)
    3. Player goals if they align with EPM data
    """
    client = _client()

    age_group = player.get("age_group", "U9")
    player_name = player["name"].split()[0]
    dominant_foot = player.get("dominant_foot", "højre")
    position = player.get("position", "N/A")
    coach_notes_on_player = player.get("notes", "")

    # Age-weighted gap priority
    prioritized_gaps = _age_weighted_gaps(gaps, age_group)
    focus_dims = prioritized_gaps[:2]

    # Build rubric blocks for the top focus dimensions
    rubric_blocks = ""
    for g in focus_dims:
        rubric_blocks += f"\n\n### {g['name']} (nuværende score: {g['score']:.1f}/10)\n"
        rubric_blocks += rubric_for_dimension(g["key"])

    # Build recent session text
    recent_text = ""
    for obs in recent_observations[:3]:
        recent_text += f"\n- {obs['date']} ({obs.get('session_type', 'N/A')}): {obs.get('theme', 'N/A')}"
        if obs.get("coach_notes"):
            recent_text += f"\n  Kaspers noter: {obs['coach_notes'][:300]}"

    # Exercise library for the prompt — IDs kept for reference only, never shown in output
    exercises_text = ""
    for ex in available_exercises[:25]:
        exercises_text += f"\n• {ex['name']} ({ex['duration_min']} min, {ex['intensity']}): {ex['description']}"
        if ex.get("setup"):
            exercises_text += f"\n  Setup: {ex['setup']}"
        if ex.get("coaching_points"):
            cps = ex["coaching_points"]
            if isinstance(cps, list):
                exercises_text += f"\n  Fokuspunkter: {' / '.join(cps[:3])}"

    la_masia = _load_la_masia()
    kp13_methodology = _load_kp13_methodology()

    day_names = {2: "Mandag og Torsdag", 3: "Mandag, Onsdag og Fredag", 4: "Mandag, Tirsdag, Torsdag og Lørdag"}
    sessions_count = len(chosen_days) if chosen_days else (sessions_per_week or 3)
    if chosen_days:
        if len(chosen_days) == 1:
            days_label = chosen_days[0]
        elif len(chosen_days) == 2:
            days_label = f"{chosen_days[0]} og {chosen_days[1]}"
        else:
            days_label = ", ".join(chosen_days[:-1]) + f" og {chosen_days[-1]}"
    else:
        days_label = day_names.get(sessions_count, f"{sessions_count} gange om ugen")

    system = f"""\
Du er KP13 Akademiets AI-træningsmester. Du designer ugentlige HJEMMETRÆNINGSPLANER \
som {player_name} laver ALENE i løbet af ugen.

{load_skill("weekly-progression")}

━━━ KP13 TRÆNINGSFILOSOFI (fuld reference) ━━━━━━━━━━━━━━━━
{kp13_methodology}

━━━ LA MASIA PRINCIPPER ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{la_masia[:800]}

━━━ EVALUERINGSRUBRIKER FOR FOKUSOMRÅDER ━━━━━━━━━━━━━━━━━━
{rubric_blocks}

━━━ DANSK STEMMEFØRING (vigtigt) ━━━━━━━━━━━━━━━━━━━━━━━━━
Skriv naturligt dansk — ikke oversat engelsk. Mange AI-modeller falder i \
den fælde at oversætte engelske trænings-idiomer direkte. Det lyder altid forkert.

REGLER:
1. Hvis du mærker en engelsk sætningsstruktur i hovedet, skriv om fra bunden \
   på dansk. Brug ikke metaforer, ordsprog eller motivations-floskler \
   oversat fra engelsk.
2. Skriv som en dansk ungdomstræner taler med en 9-årig: konkret, roligt, \
   uden opstyltet sportssprog.
3. Hvis du er i tvivl om en sætning lyder dansk — vælg den enkleste, mest \
   direkte formulering.

EKSEMPLER:
 ✗ "Turneringen kan ikke slå dig ned"          → engelsk idiom, findes ikke på dansk
 ✓ "Lad ikke kampen stresse dig"               → naturligt dansk
 ✗ "Du har magten når du har begge ben"        → for pompøst
 ✓ "Med begge ben kan ingen forudsige dig"     → konkret og direkte
 ✗ "Tag dit spil til næste niveau"             → oversat floskel
 ✓ "Gør det lidt hurtigere end sidste gang"    → konkret handling
"""

    user_msg = f"""\
Lav en komplet ugentlig træningsplan for {player_name}.

SPILLER-PROFIL:
  Navn: {player["name"]}
  Aldersgruppe: {age_group}
  Position: {position}
  Dominerende fod: {dominant_foot}
  Kaspers noter om spilleren: {coach_notes_on_player or "Ingen specifikke noter."}

SPILLERENS MÅL:
{player_goals or "Ingen specifikke mål angivet — brug EPM-data til at sætte fokus."}

AKTUELLE EPM-HULLER (prioriteret efter alder og vigtighed):
{chr(10).join(f"  - {g['name']}: {g['score']:.1f}/10" for g in prioritized_gaps[:4])}

STYRKER (byg videre på disse):
{chr(10).join(f"  - {s['name']}: {s['score']:.1f}/10" for s in strengths[:3])}

SENESTE SESSIONER:
{recent_text if recent_text else "  Ingen tidligere sessioner registreret — dette er en frisk start."}

TILGÆNGELIGE ØVELSER:
{exercises_text}

PLAN-FORMAT:
Lav {sessions_count} sessioner ({days_label}). Skriv planen som en sammenhængende, letlæselig tekst \
henvendt direkte til {player_name} og hans forælder. Brug "du" til {player_name}.

For HVER session:

---
## [UGEDAG] — [Fokusområde] · ca. [X] min

**Hvorfor denne session?**
1-2 sætninger til {player_name}: hvad træner du i dag, og hvad betyder det for din næste kamp?

**Opvarmning** (5 min)
Beskriv 1-2 øvelser direkte til {player_name}. Angiv præcis setup (afstande, antal kegler) og reps/tid. \
Skriv klart og konkret — hans forælder skal kunne sætte det op uden fodbolderfaring.

**Hoveddel** (10-15 min)
2 øvelser beskrevet på samme måde. Hvert øvelse på 3-5 sætninger.
Afslut hver øvelse med: *Forældre: hold øje med [konkret, observerbar handling der viser {player_name} gør det rigtigt]*

**Nedvarmning** (2-3 min)
Én kort aktivitet der runder sessionen af med ro og kontrol.

**Sådan gør eliten:**
2-3 sætninger om hvad de dygtigste U9-spillere konkret gør anderledes. \
Beskriv observerbare handlinger — ikke abstrakte egenskaber som "mentalitet" \
eller "vilje". Undgå motiverende klichéer.

**Fodboldkoncept: [Navn på konceptet]**
4-5 sætninger direkte til {player_name} i alderstilpasset sprog. \
Forklar HVORFOR dette koncept gør ham sværere at stoppe i kampen.

*Kaspers besked til {player_name}: "[Én sætning der knytter dagens træning \
til en konkret handling i hans næste kamp. FORBUDT: metaforer, engelsk-klingende \
idiomer, generelle motivations-floskler. PÅKRÆVET: navngiv en konkret situation \
fra kampen og hvad han skal gøre. Eksempel: 'Sofus, når du modtager bolden midt \
på banen i søndags-kampen — sæt foden ovenpå først, så kig op.'"]*

---

OUTPUT-SPECIFIKKE REGLER:
- Skriv ALT på dansk, henvendt direkte til {player_name} ("du") og hans forælder hvor relevant.
- ALDRIG brug øvelses-ID'er (koder som 'bm_sole_taps') — brug kun det rigtige øvelsesnavn.
- Vær hyper-specifik: ikke "øv first touch" men "modtag bolden og lad den rulle 45 grader fra dig".
- Max 420 ord per session.

(Hårde principper — solo-træning, Persian Ball-intensitet, begge fødder, ball-mastery foundation, \
KP13-vokabular, tre-sessioners progression — er beskrevet i weekly-progression skill'en ovenfor.)
"""

    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=6000,
        system=system,
        messages=[{"role": "user", "content": user_msg}],
    )
    return response.content[0].text


# ---- coach session prep ------------------------------------------------------

def generate_session_prep(
    player_profile: dict[str, Any],
    gaps: list[dict[str, Any]],
    recent_sessions: list[dict[str, Any]],
    available_exercises: list[dict[str, Any]],
) -> str:
    """Generate a session preparation brief for the coach."""
    client = _client()
    system = _build_system_prompt(player_profile)

    recent_text = ""
    for s in recent_sessions[:5]:
        recent_text += f"\n- {s['date']} ({s['session_type']}): {s.get('theme', 'N/A')}"
        if s.get("coach_notes"):
            notes_preview = s["coach_notes"][:300]
            recent_text += f"\n  {notes_preview}"

    gaps_text = ", ".join(f"{g['name']} ({g['score']:.1f})" for g in gaps)

    user_msg = f"""\
Prepare a coaching brief for the next individual session.

DEVELOPMENT GAPS: {gaps_text}

RECENT SESSIONS:
{recent_text}

Suggest:
1. SESSION THEME — one clear red thread for the session
2. KEY FOCUS — the #1 thing to develop today and why (link to causal model)
3. WATCH FOR — what to observe that indicates progress or continued struggle
4. TRANSFER CHECK — what to look for in the next team session to see if today's work sticks
5. SUGGESTED EXERCISES — 3-4 exercises from the library that target today's theme

Be direct and coaching-focused. This is for the coach, not the parent."""

    response = client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=1500,
        system=system,
        messages=[{"role": "user", "content": user_msg}],
    )
    return response.content[0].text
