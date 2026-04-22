"""Pydantic contracts for agent outputs.

The `WeeklySchedule` tree is the structured shape returned by
`agents.session_designer.design_week()` and consumed by the FastAPI mobile UI
(Jinja templates read these fields via attribute access). Saved to the
`weekly_schedules` table as JSON.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Weekday = Literal[
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"
]


class ScheduledExercise(BaseModel):
    exercise_id: str = Field(description="ID from the exercise library (e.g. bm_sole_taps)")
    name: str = Field(description="Exercise name from the library")
    description: str = Field(description="What the player does — rewritten for home context if needed")
    duration_min: int = Field(description="Minutes for this exercise")
    reps: str = Field(description="Specific reps/sets/duration. e.g. '3 x 30 seconds each foot', '8 reps left, 8 reps right'")
    setup: str = Field(description="Exact setup for home/garden: distances, equipment placement. A parent with zero football knowledge must understand this.")
    coaching_points: str = Field(description="2-3 key coaching cues from the library, phrased as observable actions")
    why_this_exercise: str = Field(description="One sentence: why THIS exercise for THIS player right now (link to their EPM gap or strength)")
    video_url: str = Field(description="Video URL for parent/player reference. Prefer direct exercise video; fallback to provided search URL.")


class ScheduledSession(BaseModel):
    day: Weekday
    theme: str = Field(description="Session's red thread — one specific footballing concept that connects all exercises")
    duration_min: int
    warm_up: list[ScheduledExercise]
    main: list[ScheduledExercise]
    cool_down: list[ScheduledExercise]
    coaches_note: str = Field(description="One sentence for the parent: what to watch for that shows progress. Phrased as an observable action.")


class WeeklySchedule(BaseModel):
    week_focus: str = Field(description="The main development theme for this week — stated as a footballing problem, not a vague label. e.g. 'Receiving on the half-turn to play forward under pressure'")
    week_rationale: str = Field(description="2-3 sentences: WHY this focus, based on EPM data. What gap are we closing? What did recent sessions reveal?")
    sessions: list[ScheduledSession] = Field(description="Exactly 3 training sessions for the week", min_length=3, max_length=3)
