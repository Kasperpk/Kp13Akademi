---
name: weekly-progression
description: Design a player's home-training week as a coherent three-session arc — foundation, speed, challenge — anchored on EPM gaps and KP13 methodology. Use when generating any multi-session weekly plan (Mon/Wed/Fri or Mon/Thu, structured JSON or Danish prose). Encodes the progression pattern, age-weighted focus selection, and red-thread session design at the week level.
---

# KP13 Weekly Home-Training Progression

## When to Use

- Generating a player's full weekly home-training plan (typically 3 sessions)
- Selecting and sequencing exercises across days
- Both structured outputs (tool_use JSON) and Danish prose plans

This skill operates at the **week** level. For single-day session formatting and the FOKUS / OPVARMNING / HOVEDBLOK / NEDKØLING / KASPERS BESKED structure, use the `player-daily-plan` skill.

## The Three-Session Arc

Every week is **one developmental story told across three sessions**, each building on the previous one:

| Day pattern (3/wk) | Day pattern (2/wk) | Phase | What it does |
|---|---|---|---|
| Monday | Monday | **Foundation** | Slow, technical, build the pattern. Learn the move with focus and quality. |
| Wednesday | Thursday | **Speed** | Same pattern at game speed. Add pressure, decisions, time constraints. |
| Friday | — | **Challenge** | Combine patterns, compete, test under fatigue. End-of-week stress test. |

### Why the arc matters

A week of three identical "do these drills" sessions is wasted work. The arc forces real progression: the player feels Monday → Wednesday → Friday as a deliberate climb, not three random training sessions in a row.

## Focus Selection (Priority Order)

When choosing what the week works on, this is the priority — higher overrides lower:

1. **Coach notes from recent sessions** (highest) — anything Kasper has explicitly flagged in his notes about this player. Always wins.
2. **Age-weighted EPM gaps** — the most impactful dimension to improve right now, given the player's age. (Code computes this; trust the prioritized gap list passed in.)
3. **Player's stated goals** — only when they align with EPM data. Goals that contradict the data are deferred.

Don't average the three. Pick the top signal and commit.

## Each Session Has a Red Thread

Every individual session within the week needs a single specific footballing concept that connects warm-up → main → cool-down. Examples:

- ✅ "Receiving on the half-turn to play forward under pressure"
- ✅ "Quick feet to create space for the first touch forward"
- ❌ "Ball mastery" (too vague)
- ❌ "Speed" (a physical attribute, not a footballing concept)

The three sessions in a week share the **week's focus** but each has its own **session red thread** that advances it.

## Hard Constraints (Inherit from KP13 Methodology)

These are non-negotiable for every session in the week. Violating any is a defect.

1. **Solo only.** All exercises work with one player and one ball. Never assume a coach or parent is present. Use timers and self-checks.
2. **Persian Ball intensity.** Short, sharp, high-tempo. Quality first, then speed.
3. **Both feet, always.** Bilateral development is embedded in every session.
4. **Ball mastery foundation.** Every session opens with ball-mastery work.
5. **Game connection.** Every exercise links to a concrete match situation.
6. **Vary across sessions.** Don't repeat the same exercise on multiple days within the same week.

## KP13 Move Vocabulary

Use these by name when relevant: sole rolls, V-drag, L-drag, inside-outside, toe-taps, push-and-go, body feint, step-over, inside cut.

## Per-Exercise Quality Bar

Every selected exercise must include:

- **Setup** crystal clear for someone with zero football knowledge — exact distances, cone placement, where to stand, what success looks like
- **Reps/sets/duration** as specific numbers, not "a few reps"
- **Coaching points** as observable actions ("Light touch — ball barely moves"), not vague advice ("Have good technique")
- **Why this exercise for this player right now** — link to the EPM gap or strength being addressed
- **Video URL** — use the URL from the supplied exercise library entry; never invent

## Session Length

15-20 minutes total per session: 1-2 warm-up exercises, 2-3 main exercises, 1 cool-down.

## Output Mode

This skill encodes the **principles**. The runtime function decides the **output shape**:

- Structured tool_use JSON → schema enforced by the calling code (`create_weekly_schedule` tool).
- Danish prose plan → renders the week as readable text addressed directly to the player.

In both cases, the principles above govern selection, sequencing, and the per-exercise quality bar.
