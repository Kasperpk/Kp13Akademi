"""Scoring rubrics — observable behaviours that define each score level.

Each dimension has concrete indicators for U8-U10 players so that scoring
is consistent across sessions and the AI extracts calibrated ratings.

Stages map to score ranges:
  1-2  Discovering  — Still learning the basics, frequent breakdowns
  3-5  Developing   — Shows understanding, inconsistent execution
  6-7  Confident    — Reliable in training, starting to show in games
  8-9  Advanced     — Consistently strong, stands out in age group
  10   Elite        — Exceptional for age, could play up
"""

from __future__ import annotations

RUBRICS: dict[str, dict[str, str]] = {

    # ── TECHNICAL ─────────────────────────────────────────────────────────

    "first_touch": {
        "1-2": (
            "Ball bounces off foot regularly. No body shape preparation. "
            "Cannot receive on the move — has to stop to control."
        ),
        "3-5": (
            "Can cushion a pass when standing still. Sometimes turns with the ball "
            "but often takes 2-3 touches. Loses the ball when pressed during receiving."
        ),
        "6-7": (
            "Opens body on the half-turn before receiving. Controls into space with "
            "first touch most of the time. Can receive with both feet in unpressured situations."
        ),
        "8-9": (
            "Consistently receives on the half-turn under pressure. First touch sets up "
            "the next action (pass, drive, turn). Chooses the right surface for the situation."
        ),
        "10": (
            "First touch is a weapon — kills the ball dead or accelerates away in one motion. "
            "Receives with back to goal and turns past opponents. Looks like a different age group."
        ),
    },

    "passing": {
        "1-2": (
            "Passes rarely reach the target. No weight control — too hard or too soft. "
            "Doesn't look up before passing."
        ),
        "3-5": (
            "Can make simple 5-10m passes along the ground. Struggles with longer passes. "
            "Sometimes plays the right pass but weight is off. Defaults to nearest teammate."
        ),
        "6-7": (
            "Good weight on short passes. Starting to play through lines occasionally. "
            "Can switch play with a longer pass when given time. Picks the right option most of the time."
        ),
        "8-9": (
            "Plays forward passes through lines consistently. Good weight at all distances. "
            "Sees the switch before it opens. Can play one-touch when needed."
        ),
        "10": (
            "Dictates tempo with passing. Plays disguised or weighted through-balls that "
            "break defensive lines. Both feet equally reliable. Vision well beyond age group."
        ),
    },

    "ball_mastery": {
        "1-2": (
            "Ball gets away from feet regularly. Limited to one move or no moves at all. "
            "Cannot keep the ball under control while changing direction."
        ),
        "3-5": (
            "Can do basic moves (drag-back, step-over) in isolation but loses the ball "
            "when trying them in games. Comfortable on the ball only when unpressed."
        ),
        "6-7": (
            "Has 3-4 moves and uses them in game situations. Comfortable receiving "
            "and turning under moderate pressure. Keeps the ball close in tight spaces."
        ),
        "8-9": (
            "Wide repertoire of moves, uses the right one for the situation. "
            "Comfortable in 1v1 spaces, can manipulate the defender. "
            "Ball looks glued to feet when dribbling in traffic."
        ),
        "10": (
            "Exceptional close control — plays in phone-booth spaces. "
            "Invents solutions under pressure. Can juggle, flick, and manipulate the ball "
            "in ways that create time and space out of nothing."
        ),
    },

    "dribbling_speed": {
        "1-2": (
            "Cannot run with the ball at any pace. Ball runs away or gets stuck under feet. "
            "Has to look down at the ball constantly."
        ),
        "3-5": (
            "Can push the ball forward and run but loses control at pace. "
            "Tends to step on the ball rather than push it into space. "
            "Defenders catch up easily."
        ),
        "6-7": (
            "Drives the ball at a good pace in open space. Uses the laces to push forward. "
            "Can carry the ball 15-20m without losing control. Starting to use the push-and-go."
        ),
        "8-9": (
            "Dynamic ball carrying — accelerates with the ball, changes direction at pace. "
            "Defenders cannot catch up when space opens. Knows when to drive vs. when to pass."
        ),
        "10": (
            "Carries the ball as fast as they run without it. "
            "Explosive push-and-go beats defenders consistently. "
            "Can drive through multiple opponents at pace."
        ),
    },

    "finishing": {
        "1-2": (
            "Shots have no power or direction. Misses the target from close range. "
            "No technique — toe-pokes or swings wildly."
        ),
        "3-5": (
            "Can strike the ball cleanly sometimes. Scores from close range "
            "but struggles with power or placement from distance. Gets nervous in front of goal."
        ),
        "6-7": (
            "Reliable from inside the box. Uses the instep for power. "
            "Can place the ball when given time. Starting to finish with composure."
        ),
        "8-9": (
            "Clinical finisher — picks corners, varies technique (instep, side-foot, chip). "
            "Stays composed 1v1 with the keeper. Scores regularly."
        ),
        "10": (
            "Scores from anywhere. Finishes first time, on the volley, with either foot. "
            "Ice cold composure. Technique and decision-making in the box are exceptional."
        ),
    },

    "weak_foot": {
        "1-2": (
            "Avoids using the weak foot entirely. Will turn onto the strong foot "
            "even when the weak foot is the obvious choice. Cannot pass or control with it."
        ),
        "3-5": (
            "Can make a simple pass with the weak foot. Cannot receive or shoot with it. "
            "Turns onto strong foot under any pressure."
        ),
        "6-7": (
            "Comfortable passing with the weak foot. Can receive and control. "
            "Starting to use it in games when the situation demands it."
        ),
        "8-9": (
            "Reliable with the weak foot for passing, receiving, and shooting. "
            "Opponents cannot force them onto one side. "
            "Doesn't hesitate when the weak foot is the right option."
        ),
        "10": (
            "Genuinely two-footed — you cannot tell which is dominant. "
            "Shoots, passes, and dribbles with both feet equally."
        ),
    },

    # ── PHYSICAL ──────────────────────────────────────────────────────────

    "acceleration": {
        "1-2": (
            "Slow to react to the ball or opponent. Gets beaten to every loose ball. "
            "No explosive first step."
        ),
        "3-5": (
            "Average speed off the mark. Can sprint in a straight line but slow to react "
            "to cues (ball movement, opponent's first touch)."
        ),
        "6-7": (
            "Good first 3-5 steps. Reacts quickly to loose balls. "
            "Can beat an opponent in a foot race over short distances."
        ),
        "8-9": (
            "Explosive starts — first to every ball. "
            "Quick off the mark in multiple directions. "
            "Speed advantage is noticeable against peers."
        ),
        "10": (
            "Exceptional burst — like a different gear. "
            "Wins every sprint duel. Reactive speed matches physical speed."
        ),
    },

    "agility": {
        "1-2": (
            "Stiff movement, falls over when changing direction. "
            "Cannot shift weight quickly. Poor body control."
        ),
        "3-5": (
            "Can change direction at moderate pace. Looks awkward when moving laterally. "
            "Balance breaks down under pressure or at speed."
        ),
        "6-7": (
            "Good change of direction. Can feint and shift weight to beat an opponent. "
            "Balanced when turning. Moves well in small spaces."
        ),
        "8-9": (
            "Sharp, quick direction changes. Low centre of gravity. "
            "Excellent body control — can jink past opponents and stay on their feet."
        ),
        "10": (
            "Cat-like agility — impossible to predict. Changes direction without losing speed. "
            "Body control is exceptional for any age."
        ),
    },

    "endurance": {
        "1-2": (
            "Drops off significantly after 10-15 minutes. Stops running, walks during play. "
            "Cannot sustain any intensity."
        ),
        "3-5": (
            "Can sustain effort for a half but noticeably fades. "
            "Intensity drops after high-effort bursts. "
            "Still running but not pressing or sprinting in the last quarter."
        ),
        "6-7": (
            "Maintains intensity for a full session or match. "
            "Can recover between sprints. Same effort in minute 1 and minute 40."
        ),
        "8-9": (
            "Engine — consistently high work rate throughout. "
            "Still pressing and sprinting when others have faded. "
            "Recovers quickly between high-intensity efforts."
        ),
        "10": (
            "Relentless. Outworks every player on the pitch from first to last minute. "
            "Never looks tired. Sets the tempo for the team."
        ),
    },

    # ── COGNITIVE ─────────────────────────────────────────────────────────

    "game_reading": {
        "1-2": (
            "Ball-watches — no awareness of teammates or opponents around them. "
            "Doesn't scan. Gets surprised by passes or pressure. "
            "Stands still when not on the ball."
        ),
        "3-5": (
            "Starting to look around occasionally. Knows where the ball is "
            "but not where the space is. Reacts to what happens rather than anticipating."
        ),
        "6-7": (
            "Scans before receiving. Aware of nearby opponents and teammates. "
            "Starting to anticipate where the ball will go next. "
            "Can intercept or cut passing lanes sometimes."
        ),
        "8-9": (
            "Reads the game ahead — positions themselves before the ball arrives. "
            "Consistently scans and adjusts. Intercepts passes, anticipates transitions."
        ),
        "10": (
            "Sees the game like a player 3-4 years older. "
            "Always in the right position. Reads the opponent's intentions before they act. "
            "Organises teammates and points out space."
        ),
    },

    "decision_speed": {
        "1-2": (
            "Holds the ball too long, doesn't know what to do. "
            "Freezes under pressure. Makes the wrong choice consistently."
        ),
        "3-5": (
            "Knows the right option after the moment has passed. "
            "Can decide correctly when given time but panics under pressure. "
            "Often defaults to the safe option."
        ),
        "6-7": (
            "Makes good decisions at a reasonable speed. Picks the right pass or action "
            "most of the time. Sometimes takes one touch too many before deciding."
        ),
        "8-9": (
            "Decides quickly and correctly under pressure. One-touch play, quick combinations. "
            "Rarely picks the wrong option. Plays at a tempo that stretches opponents."
        ),
        "10": (
            "Thinks faster than everyone on the pitch. "
            "Already knows what to do before the ball arrives. "
            "Plays first-time passes that others wouldn't even see."
        ),
    },

    "positional_play": {
        "1-2": (
            "No sense of where to be. Chases the ball regardless of position. "
            "Bunches with other players. Doesn't understand shape or spacing."
        ),
        "3-5": (
            "Stays roughly in their zone when reminded. "
            "Drifts out of position when the ball is far away. "
            "Doesn't move to create passing angles."
        ),
        "6-7": (
            "Understands their role in the team shape. "
            "Creates passing angles, offers width or depth. "
            "Moves off the ball to make themselves available."
        ),
        "8-9": (
            "Excellent off-the-ball movement. Creates and exploits space. "
            "Understands when to hold position vs. when to move. "
            "Makes runs that pull defenders out of shape."
        ),
        "10": (
            "Positional intelligence beyond their years. "
            "Manipulates space — drags defenders, creates overloads. "
            "Always findable, always in a position that helps the team."
        ),
    },

    # ── MENTAL ────────────────────────────────────────────────────────────

    "resilience": {
        "1-2": (
            "Gives up after a mistake or a lost duel. Head drops visibly. "
            "Avoids the ball after an error. May cry or want to stop."
        ),
        "3-5": (
            "Affected by mistakes but recovers within a few minutes. "
            "Can bounce back in training but struggles in matches or tournaments. "
            "Loses confidence after a bad half."
        ),
        "6-7": (
            "Mistakes don't linger. Asks for the ball again after losing it. "
            "Competes hard even when the team is losing. Handles most pressure well."
        ),
        "8-9": (
            "Thrives under pressure. Wants the ball in big moments. "
            "A mistake makes them more determined, not less. "
            "Leads by example when things get tough."
        ),
        "10": (
            "Unshakeable. Performs best when the pressure is highest. "
            "Tournament finals, penalty shootouts — always steps up. "
            "Team looks to them when things go wrong."
        ),
    },

    "intensity": {
        "1-2": (
            "Low effort. Jogs through exercises. Doesn't compete in duels. "
            "Body language suggests disengagement."
        ),
        "3-5": (
            "Tries hard in exercises they enjoy but switches off in others. "
            "Moderate effort in games. Doesn't press or track back with urgency."
        ),
        "6-7": (
            "Consistent effort across the session. Competes in every exercise. "
            "Presses when the team loses the ball. Good work rate."
        ),
        "8-9": (
            "Sets the tempo for the group. First to press, first to sprint back. "
            "Competes in every duel like it matters. Lifts others around them."
        ),
        "10": (
            "Maximum intensity every second. Treats every rondo rep like a final. "
            "Infectious energy that transforms the group. Relentless competitor."
        ),
    },

    "coachability": {
        "1-2": (
            "Doesn't listen to instructions. Ignores coaching cues. "
            "Resists trying new things. Gets frustrated when corrected."
        ),
        "3-5": (
            "Listens but doesn't always apply the feedback. "
            "Will try something new once but reverts to old habits. "
            "Needs repeated reminders."
        ),
        "6-7": (
            "Takes feedback on board and tries to apply it immediately. "
            "Asks questions. Open to trying new techniques or positions. "
            "Shows improvement within a session after a coaching point."
        ),
        "8-9": (
            "Self-corrects based on feedback. Remembers coaching points across sessions. "
            "Actively seeks feedback. Tries the hard thing, not the easy thing."
        ),
        "10": (
            "A coach's dream — absorbs and applies everything. "
            "Experiments on their own between sessions. Teaches teammates. "
            "Growth rate is visibly accelerated by their attitude to learning."
        ),
    },

    "joy": {
        "1-2": (
            "Doesn't want to be there. Resistant to starting. Negative body language. "
            "Asks when it's over."
        ),
        "3-5": (
            "Enjoys parts of the session (usually games) but not technical work. "
            "Engagement fluctuates. Needs external motivation."
        ),
        "6-7": (
            "Enjoys training. Smiles, engages, competes. "
            "Wants to come back. Happy through most of the session."
        ),
        "8-9": (
            "Loves it. Arrives early, doesn't want to leave. "
            "Tries things at home unprompted. Talks about training between sessions."
        ),
        "10": (
            "Football is their world. Practices on their own every day. "
            "Brings energy and enthusiasm that's contagious. "
            "The session is the highlight of their week."
        ),
    },
}


def rubric_for_dimension(key: str) -> str:
    """Return a formatted rubric string for a single dimension."""
    r = RUBRICS.get(key, {})
    if not r:
        return ""
    lines = []
    for level, desc in r.items():
        lines.append(f"  {level}: {desc}")
    return "\n".join(lines)


def all_rubrics_text() -> str:
    """Return all rubrics formatted for inclusion in an LLM prompt."""
    from .epm import DIM_BY_KEY
    parts = []
    for key, levels in RUBRICS.items():
        meta = DIM_BY_KEY.get(key)
        name = meta.name if meta else key
        parts.append(f"\n{name} ({key}):")
        for level, desc in levels.items():
            parts.append(f"  {level}: {desc}")
    return "\n".join(parts)
