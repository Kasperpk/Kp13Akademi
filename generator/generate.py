#!/usr/bin/env python3
"""Interactive CLI for generating football training sessions."""

from __future__ import annotations

import sys
from datetime import date

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table

from history import append_entry, last_used_map
from library import (
    filter_exercises,
    list_templates,
    load_exercises,
    load_template,
    pick_random_weighted,
)
from models import (
    Category,
    Exercise,
    HistoryEntry,
    PhaseTemplate,
    PlannedExercise,
    PlannedPhase,
    SessionPlan,
)
from renderer import render_session, save_session

console = Console()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _choose_from_list(options: list[str], prompt_text: str) -> str:
    for i, opt in enumerate(options, 1):
        console.print(f"  [bold cyan]{i}[/] — {opt}")
    while True:
        choice = Prompt.ask(prompt_text)
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(options):
                return options[idx]
        except ValueError:
            if choice in options:
                return choice
        console.print("[red]Invalid choice. Try again.[/]")


def _exercise_table(
    exercises: list[Exercise],
    recency: dict[str, date],
    today: date,
) -> Table:
    table = Table(show_header=True, header_style="bold magenta", expand=True)
    table.add_column("#", style="bold cyan", width=4)
    table.add_column("Name", min_width=25)
    table.add_column("Intensity", width=10)
    table.add_column("Players", width=10)
    table.add_column("Space", width=14)
    table.add_column("Last Used", width=14)

    for i, ex in enumerate(exercises, 1):
        last = recency.get(ex.id)
        if last is None:
            recency_str = "[green]never[/]"
        else:
            days = (today - last).days
            if days <= 3:
                recency_str = f"[red]{days}d ago[/]"
            elif days <= 14:
                recency_str = f"[yellow]{days}d ago[/]"
            else:
                recency_str = f"[green]{days}d ago[/]"

        players = f"{ex.min_players}"
        if ex.max_players:
            players += f"-{ex.max_players}"
        else:
            players += "+"

        table.add_row(
            str(i),
            ex.name,
            ex.intensity.value,
            players,
            ex.space.value.replace("_", " "),
            recency_str,
        )
    return table


def _pick_exercises_for_phase(
    phase: PhaseTemplate,
    all_exercises: list[Exercise],
    recency: dict[str, date],
    today: date,
    context: str,
    player_count: int | None,
    excluded_ids: set[str] | None = None,
) -> list[tuple[Exercise, int]]:
    """Interactive exercise picker for a single phase.

    Returns list of (Exercise, duration_minutes) tuples.
    """
    categories = phase.required_categories
    candidates = filter_exercises(
        all_exercises,
        categories=categories,
        min_players_available=player_count,
        require_equipment=phase.require_equipment or None,
        excluded_ids=excluded_ids,
    )

    if not candidates:
        console.print(f"[yellow]No exercises match the filters for this phase.[/]")
        return []

    console.print()
    console.print(
        Panel(
            f"[bold]{phase.name}[/]\n"
            f"Duration: {phase.duration_minutes[0]}-{phase.duration_minutes[1]} min  |  "
            f"Exercises: {phase.min_exercises}-{phase.max_exercises}\n"
            f"Categories: {', '.join(c.value for c in categories)}\n\n"
            f"{phase.notes}",
            title="Phase",
            border_style="blue",
        )
    )

    console.print(_exercise_table(candidates, recency, today))
    console.print()

    selected: list[tuple[Exercise, int]] = []
    remaining_time = phase.duration_minutes[1]

    while len(selected) < phase.max_exercises:
        min_needed = max(0, phase.min_exercises - len(selected))
        if min_needed > 0:
            console.print(f"  [dim]Need at least {min_needed} more exercise(s).[/]")

        choice = Prompt.ask(
            f"  Pick exercise # (or [bold]r[/]andom, [bold]d[/]one)",
            default="d" if len(selected) >= phase.min_exercises else None,
        )
        if choice is None:
            continue

        if choice.lower() == "d":
            if len(selected) < phase.min_exercises:
                console.print(
                    f"[red]Need at least {phase.min_exercises} exercise(s). "
                    f"You have {len(selected)}.[/]"
                )
                continue
            break

        if choice.lower() == "r":
            n = max(1, phase.min_exercises - len(selected))
            available = [c for c in candidates if c not in [s[0] for s in selected]]
            picks = pick_random_weighted(available, recency, count=n, today=today)
            for ex in picks:
                dur = _suggest_duration(ex, remaining_time, len(selected), phase)
                dur = IntPrompt.ask(f"    Duration for [bold]{ex.name}[/]", default=dur)
                selected.append((ex, dur))
                remaining_time -= dur
                console.print(f"    [green]✓ Added {ex.name} ({dur} min)[/]")
            continue

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(candidates):
                ex = candidates[idx]
                if ex in [s[0] for s in selected]:
                    console.print("[yellow]Already selected.[/]")
                    continue
                dur = _suggest_duration(ex, remaining_time, len(selected), phase)
                dur = IntPrompt.ask(
                    f"    Duration for [bold]{ex.name}[/]", default=dur
                )
                selected.append((ex, dur))
                remaining_time -= dur
                console.print(f"    [green]✓ Added {ex.name} ({dur} min)[/]")
            else:
                console.print("[red]Invalid number.[/]")
        except ValueError:
            console.print("[red]Enter a number, 'r', or 'd'.[/]")

    return selected


def _suggest_duration(
    ex: Exercise,
    remaining_time: int,
    already_picked: int,
    phase: PhaseTemplate,
) -> int:
    """Suggest a reasonable duration for an exercise within a phase."""
    avg_duration_s = (ex.duration_seconds[0] + ex.duration_seconds[1]) / 2
    suggested = max(2, round(avg_duration_s / 60))
    phase_avg = (phase.duration_minutes[0] + phase.duration_minutes[1]) // 2
    slots_left = max(1, phase.min_exercises - already_picked)
    max_allowed = max(2, remaining_time - (slots_left - 1) * 2)
    return min(suggested, max_allowed, remaining_time)


# ---------------------------------------------------------------------------
# Main flow
# ---------------------------------------------------------------------------


def main() -> None:
    console.print(
        Panel(
            "[bold]Football Session Generator[/]\n"
            "Design varied training sessions based on La Masia, PersianBall & evidence-based methodology.",
            border_style="green",
        )
    )

    # Load data
    all_exercises = load_exercises()
    console.print(f"Loaded [bold]{len(all_exercises)}[/] exercises from library.")

    recency = last_used_map()
    today = date.today()

    # 1. Choose template
    templates = list_templates()
    if not templates:
        console.print("[red]No templates found. Add YAML files to templates/.[/]")
        sys.exit(1)

    console.print("\n[bold]Available templates:[/]")
    template_name = _choose_from_list(templates, "Choose template")
    template = load_template(template_name)
    console.print(f"\nUsing template: [bold green]{template.name}[/]")

    # 2. Session date
    date_str = Prompt.ask("Session date", default=today.isoformat())
    try:
        session_date = date.fromisoformat(date_str)
    except ValueError:
        console.print("[red]Invalid date format. Using today.[/]")
        session_date = today

    # 3. Player count
    if template.context == "team":
        player_count = IntPrompt.ask("Number of players", default=12)
    else:
        player_count = 1

    # 4. Phase-by-phase exercise selection
    planned_phases: list[PlannedPhase] = []
    all_selected_ids: list[str] = []
    used_in_session: set[str] = set()

    for phase_tmpl in template.phases:
        selections = _pick_exercises_for_phase(
            phase_tmpl, all_exercises, recency, today, template.context, player_count,
            excluded_ids=used_in_session,
        )

        planned_exercises = []
        phase_total = 0
        for ex, dur in selections:
            planned_exercises.append(
                PlannedExercise(
                    exercise_id=ex.id,
                    exercise_name=ex.name,
                    duration_minutes=dur,
                )
            )
            phase_total += dur
            all_selected_ids.append(ex.id)
            used_in_session.add(ex.id)

        planned_phases.append(
            PlannedPhase(
                name=phase_tmpl.name,
                duration_minutes=phase_total,
                exercises=planned_exercises,
            )
        )

    # 5. Session notes
    notes = Prompt.ask("Session notes (optional)", default="")

    # 6. Build plan
    total_dur = sum(p.duration_minutes for p in planned_phases)
    plan = SessionPlan(
        date=session_date,
        template_name=template.name,
        context=template.context,
        total_duration_minutes=total_dur,
        phases=planned_phases,
        notes=notes,
    )

    # 7. Preview
    ex_map = {ex.id: ex for ex in all_exercises}
    md = render_session(plan, ex_map)
    console.print()
    console.print(Panel(md, title="Session Preview", border_style="cyan"))

    # 8. Save
    if Confirm.ask("\nSave this session?", default=True):
        path = save_session(plan, ex_map)
        console.print(f"[green]Session saved to {path}[/]")

        entry = HistoryEntry(
            date=session_date,
            template_name=template.name,
            exercise_ids=all_selected_ids,
            notes=notes,
        )
        append_entry(entry)
        console.print("[green]History updated.[/]")
    else:
        console.print("[yellow]Session discarded.[/]")


if __name__ == "__main__":
    main()
