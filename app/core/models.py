"""Backward-compatibility shim — canonical home is `core.contracts`."""

from __future__ import annotations

from .contracts import (  # noqa: F401
    ScheduledExercise,
    ScheduledSession,
    WeeklySchedule,
    Weekday,
)

__all__ = ["ScheduledExercise", "ScheduledSession", "WeeklySchedule", "Weekday"]
