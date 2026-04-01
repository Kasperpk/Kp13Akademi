"""Data models for the football session generator."""

from __future__ import annotations

import enum
from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class Category(str, enum.Enum):
    WARMUP = "warmup"
    BALL_MASTERY = "ball_mastery"
    RONDO = "rondo"
    POSITIONAL_PLAY = "positional_play"
    PASSING = "passing"
    RECEIVING = "receiving"
    FINISHING = "finishing"
    AGILITY = "agility"
    SSG = "small_sided_games"
    ONE_V_ONE = "one_v_one"
    COOL_DOWN = "cool_down"
    STRENGTH = "strength"


class Space(str, enum.Enum):
    MINIMAL = "minimal_3x3"
    SMALL = "small_10x10"
    MEDIUM = "medium_20x20"
    HALF_PITCH = "half_pitch"
    FULL_PITCH = "full_pitch"


class Intensity(str, enum.Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    MAXIMUM = "maximum"


class MethodologyTag(str, enum.Enum):
    CONSTRAINTS_LED = "constraints_led"
    DIFFERENTIAL_LEARNING = "differential_learning"
    IMPLICIT_LEARNING = "implicit_learning"
    EXPLICIT_INSTRUCTION = "explicit_instruction"
    GAME_REALISTIC = "game_realistic"
    BOTH_FEET = "both_feet"
    DECISION_MAKING = "decision_making"
    PERIODIZATION_RECOVERY = "periodization_recovery"


class PhysicalTag(str, enum.Enum):
    ACCELERATION = "acceleration"
    DECELERATION = "deceleration"
    CHANGE_OF_DIRECTION = "change_of_direction"
    ENDURANCE = "endurance"
    POWER = "power"
    STABILITY = "stability"
    FLEXIBILITY = "flexibility"


class LaMasiaPrinciple(str, enum.Enum):
    POSSESSION = "possession"
    POSITIONAL_PLAY = "positional_play"
    RONDO = "rondo"
    PLAY_OUT_FROM_BACK = "play_out_from_back"
    THIRD_MAN = "third_man"
    TECHNICAL_EXCELLENCE = "technical_excellence"
    BOTH_FEET = "both_feet"
    SMALL_SIDED = "small_sided"


# ---------------------------------------------------------------------------
# Exercise models
# ---------------------------------------------------------------------------


class Variation(BaseModel):
    name: str
    description: str


class Exercise(BaseModel):
    id: str
    name: str
    description: str
    category: Category
    coaching_points: list[str] = Field(default_factory=list)
    age_range: list[int] = Field(default_factory=lambda: [6, 25])
    min_players: int = 1
    max_players: Optional[int] = None
    space: Space = Space.SMALL
    equipment: list[str] = Field(default_factory=lambda: ["ball"])
    duration_seconds: list[int] = Field(
        default_factory=lambda: [60, 300],
        description="[min, max] duration range in seconds",
    )
    intensity: Intensity = Intensity.MODERATE
    methodology_tags: list[MethodologyTag] = Field(default_factory=list)
    physical_tags: list[PhysicalTag] = Field(default_factory=list)
    la_masia_principles: list[LaMasiaPrinciple] = Field(default_factory=list)
    variations: list[Variation] = Field(default_factory=list)
    setup: str = Field(
        default="",
        description="How to set up: grid size, cone placement, player starting positions",
    )
    diagram: str = Field(
        default="",
        description="ASCII pitch diagram showing layout, player positions, movement arrows",
    )
    source: Optional[str] = None


# ---------------------------------------------------------------------------
# Session template models
# ---------------------------------------------------------------------------


class PhaseTemplate(BaseModel):
    name: str
    duration_minutes: list[int] = Field(
        description="[min, max] duration range for this phase"
    )
    required_categories: list[Category]
    require_equipment: list[str] = Field(
        default_factory=list,
        description="Exercise must include ALL of these equipment items",
    )
    min_exercises: int = 1
    max_exercises: int = 6
    notes: str = ""


class SessionTemplate(BaseModel):
    name: str
    context: str  # "individual" or "team"
    total_duration_minutes: list[int] = Field(
        default_factory=lambda: [75, 90],
        description="[min, max] total session duration",
    )
    phases: list[PhaseTemplate]


# ---------------------------------------------------------------------------
# Session plan models (generated output)
# ---------------------------------------------------------------------------


class PlannedExercise(BaseModel):
    exercise_id: str
    exercise_name: str
    duration_minutes: int
    notes: str = ""


class PlannedPhase(BaseModel):
    name: str
    duration_minutes: int
    exercises: list[PlannedExercise]


class SessionPlan(BaseModel):
    date: date
    template_name: str
    context: str
    total_duration_minutes: int
    phases: list[PlannedPhase]
    notes: str = ""


# ---------------------------------------------------------------------------
# History models
# ---------------------------------------------------------------------------


class HistoryEntry(BaseModel):
    date: date
    template_name: str
    exercise_ids: list[str]
    notes: str = ""
