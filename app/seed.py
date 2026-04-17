"""Seed the database with existing player data from clients/ markdown files."""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from core.database import (
    init_db, upsert_player, save_observation, get_players,
    create_access_token, get_player_token,
)
from core.epm import initialise_player_epm, update_scores_from_observation

def seed():
    init_db()

    existing = {p["id"] for p in get_players()}

    # ---- Sofus ---------------------------------------------------------------
    if "sofus" not in existing:
        print("Seeding Sofus...")
        upsert_player(
            "sofus",
            "Sofus Houmann Larsen",
            age_group="U9",
            position="Midfielder",
            club="AAFA",
            dominant_foot="right",
            started_date="2026-04-05",
            parent_name="Morten",
            notes="Physically strong for age. Struggles at tournaments — gives up when things get hard. Transfer gap from individual to team context.",
        )
        # Initial baseline from coach assessments (2 sessions + observations)
        initialise_player_epm("sofus", baseline={
            "first_touch":     5.5,
            "passing":         6.0,
            "ball_mastery":    6.5,
            "dribbling_speed": 4.5,
            "finishing":       5.0,
            "weak_foot":       4.0,
            "acceleration":    4.5,
            "agility":         5.0,
            "endurance":       6.0,
            "game_reading":    5.0,
            "decision_speed":  4.5,
            "positional_play": 5.0,
            "resilience":      3.5,
            "intensity":       5.5,
            "coachability":    6.5,
            "joy":             6.5,
        })

        # Seed session observations from existing notes
        save_observation(
            obs_date="2026-04-10",
            player_id="sofus",
            session_type="coached",
            theme="Speed & explosiveness",
            coach_notes=(
                "Worked on acceleration mechanics — first 3-5 steps, reaction starts, "
                "change of direction. Then introduced ball: dribbling with speed, 1v1 situations, "
                "finishing after dribble. Also did positional passing/receiving exercises. "
                "Physically fine but speed work needs consistent reps."
            ),
            extracted_scores={
                "acceleration": 4.5,
                "agility": 5.0,
                "dribbling_speed": 4.5,
                "finishing": 5.0,
                "passing": 6.0,
                "first_touch": 5.5,
                "intensity": 6.0,
            },
        )

        save_observation(
            obs_date="2026-04-15",
            player_id="sofus",
            session_type="coached",
            theme="Tactical understanding as central midfielder",
            coach_notes=(
                "Focused on scanning and first-touch-forward. In isolation Sofus understood the concepts "
                "but in team training afterwards he reverted to square body shape, receiving flat-footed "
                "rather than on the half-turn. When pressure came from real defenders, scanning dropped off — "
                "stopped checking shoulder before ball arrived, defaulted to safe backwards passes. "
                "Transfer gap is the main issue. Need more pressure and unpredictability in individual sessions."
            ),
            extracted_scores={
                "first_touch": 5.0,
                "game_reading": 4.5,
                "decision_speed": 4.0,
                "positional_play": 4.5,
                "resilience": 3.5,
                "coachability": 7.0,
            },
        )

        # Apply the observations to update EPM
        update_scores_from_observation("sofus", {
            "acceleration": 4.5, "agility": 5.0, "dribbling_speed": 4.5,
            "finishing": 5.0, "passing": 6.0, "first_touch": 5.5, "intensity": 6.0,
        })
        update_scores_from_observation("sofus", {
            "first_touch": 5.0, "game_reading": 4.5, "decision_speed": 4.0,
            "positional_play": 4.5, "resilience": 3.5, "coachability": 7.0,
        })

    # ---- Felix ---------------------------------------------------------------
    if "felix" not in existing:
        print("Seeding Felix...")
        upsert_player(
            "felix",
            "Felix Kirk Nebel",
            age_group="U9",
            position="Central / Wing",
            club="",
            dominant_foot="right",
            started_date="2026-04-14",
            parent_name="",
            notes="Technically very clean. Excellent passer. Defaults to safe pass even when driving is the better option — confidence/decision issue, not physical.",
        )
        initialise_player_epm("felix", baseline={
            "first_touch":     7.0,
            "passing":         8.0,
            "ball_mastery":    7.5,
            "dribbling_speed": 4.0,
            "finishing":       5.5,
            "weak_foot":       5.0,
            "acceleration":    5.0,
            "agility":         5.5,
            "endurance":       6.0,
            "game_reading":    6.5,
            "decision_speed":  4.0,
            "positional_play": 7.0,
            "resilience":      6.0,
            "intensity":       5.0,
            "coachability":    8.0,
            "joy":             8.5,
        })

        save_observation(
            obs_date="2026-04-14",
            player_id="felix",
            session_type="coached",
            theme="Driving with speed + drive-or-pass decision-making",
            coach_notes=(
                "Felix is technically very clean. Great passing foot, always picks the right pass. "
                "Key development area is dynamism — defaults to safe pass even when driving forward is better. "
                "Needs physical ability to carry ball at speed AND decision-making to recognise when to drive. "
                "Secondary: movement off the ball — how to get free of markers as central player. "
                "Intensity threaded into everything."
            ),
            extracted_scores={
                "passing": 8.0,
                "first_touch": 7.0,
                "ball_mastery": 7.5,
                "dribbling_speed": 4.0,
                "decision_speed": 4.0,
                "positional_play": 7.0,
                "intensity": 5.0,
                "coachability": 8.0,
                "joy": 8.5,
            },
        )

        save_observation(
            obs_date="2026-04-15",
            player_id="felix",
            session_type="team_observation",
            theme="Receiving on the half-turn (team session)",
            coach_notes=(
                "Felix's technique on the half-turn was actually decent — body shape was better than most. "
                "But same pattern: even when he received on the half-turn and had space to drive into, "
                "he chose the safe pass back. 'Drive or pass?' decision-making hasn't transferred yet. "
                "In the directional rondo he played every ball short and sideways — never drove through the middle. "
                "Core issue confirmed: not physical ability to drive, it's the decision/confidence to DO it. "
                "Movement off the ball was passive — stood still waiting instead of checking away from markers."
            ),
            extracted_scores={
                "first_touch": 7.0,
                "dribbling_speed": 3.5,
                "decision_speed": 3.5,
                "positional_play": 5.5,
                "passing": 7.5,
                "resilience": 6.0,
                "intensity": 5.5,
            },
        )

        update_scores_from_observation("felix", {
            "passing": 8.0, "first_touch": 7.0, "ball_mastery": 7.5,
            "dribbling_speed": 4.0, "decision_speed": 4.0, "positional_play": 7.0,
            "intensity": 5.0, "coachability": 8.0, "joy": 8.5,
        })
        update_scores_from_observation("felix", {
            "first_touch": 7.0, "dribbling_speed": 3.5, "decision_speed": 3.5,
            "positional_play": 5.5, "passing": 7.5, "resilience": 6.0, "intensity": 5.5,
        })

    print("Seeding complete!")
    for p in get_players():
        # Ensure every player has an access token
        token = get_player_token(p["id"])
        if not token:
            token = create_access_token(p["id"], role="player")
        print(f"  {p['name']} ({p['id']})  ->  /p/{token}")


if __name__ == "__main__":
    seed()
