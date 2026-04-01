"""Render a SessionPlan to Markdown."""

from __future__ import annotations

from pathlib import Path

from models import Exercise, SessionPlan

OUTPUT_DIR = Path(__file__).parent / "output"


def render_session(
    plan: SessionPlan,
    exercises_by_id: dict[str, Exercise],
) -> str:
    """Return a Markdown string for the given session plan."""
    lines: list[str] = []

    # Header
    lines.append(f"# {plan.template_name} — {plan.date.isoformat()}")
    lines.append("")
    lines.append(f"**Context:** {plan.context}  ")
    lines.append(f"**Date:** {plan.date.isoformat()}  ")
    lines.append(f"**Total Duration:** {plan.total_duration_minutes} minutes  ")
    if plan.notes:
        lines.append(f"**Notes:** {plan.notes}  ")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Equipment checklist
    all_equipment: set[str] = set()
    for phase in plan.phases:
        for pex in phase.exercises:
            ex = exercises_by_id.get(pex.exercise_id)
            if ex:
                all_equipment.update(ex.equipment)
    if all_equipment:
        lines.append("## Equipment Needed")
        for item in sorted(all_equipment):
            lines.append(f"- {item}")
        lines.append("")
        lines.append("---")
        lines.append("")

    # Phases
    for i, phase in enumerate(plan.phases, 1):
        lines.append(f"## {i}. {phase.name} — {phase.duration_minutes} minutes")
        lines.append("")

        for pex in phase.exercises:
            ex = exercises_by_id.get(pex.exercise_id)
            if ex:
                lines.append(f"### {ex.name}")
                lines.append(f"*{ex.description}*")
                lines.append("")
                lines.append(f"**Duration:** {pex.duration_minutes} min  ")
                lines.append(f"**Intensity:** {ex.intensity.value}  ")
                players = f"{ex.min_players}"
                if ex.max_players:
                    players += f"–{ex.max_players}"
                else:
                    players += "+"
                lines.append(f"**Players:** {players}  ")
                if ex.space:
                    lines.append(f"**Space:** {ex.space.value.replace('_', ' ')}  ")
                if ex.equipment:
                    lines.append(f"**Equipment:** {', '.join(ex.equipment)}  ")
                lines.append("")
                if ex.setup:
                    lines.append("**Setup:**")
                    lines.append(ex.setup.strip())
                    lines.append("")
                if ex.diagram:
                    lines.append("```")
                    lines.append(ex.diagram.strip())
                    lines.append("```")
                    lines.append("")
                if ex.coaching_points:
                    lines.append("**Coaching Points:**")
                    for cp in ex.coaching_points:
                        lines.append(f"- {cp}")
                    lines.append("")
                if ex.variations:
                    lines.append("**Variations:**")
                    for var in ex.variations:
                        lines.append(f"- **{var.name}:** {var.description}")
                    lines.append("")
                if pex.notes:
                    lines.append(f"> {pex.notes}")
                    lines.append("")
            else:
                lines.append(f"### {pex.exercise_name}")
                lines.append(f"**Duration:** {pex.duration_minutes} min  ")
                if pex.notes:
                    lines.append(f"> {pex.notes}")
                lines.append("")

        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def save_session(
    plan: SessionPlan,
    exercises_by_id: dict[str, Exercise],
    directory: Path = OUTPUT_DIR,
) -> Path:
    """Render and save session plan to a Markdown file. Returns the file path."""
    directory.mkdir(parents=True, exist_ok=True)
    md = render_session(plan, exercises_by_id)
    filename = f"{plan.date.isoformat()}_{plan.context}_{plan.template_name.lower().replace(' ', '_')}.md"
    path = directory / filename
    path.write_text(md, encoding="utf-8")
    return path
