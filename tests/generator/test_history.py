"""Tests for generator.history — load/save/append round-trip and last_used_map."""

from __future__ import annotations

from datetime import date


def test_load_missing_file_returns_empty(tmp_path):
    from history import load_history

    assert load_history(tmp_path / "does_not_exist.json") == []


def test_load_empty_file_returns_empty(tmp_path):
    from history import load_history

    path = tmp_path / "log.json"
    path.write_text("", encoding="utf-8")
    assert load_history(path) == []

    path.write_text("[]", encoding="utf-8")
    assert load_history(path) == []


def test_save_then_load_roundtrip(tmp_path):
    from history import load_history, save_history
    from models import HistoryEntry

    path = tmp_path / "log.json"
    entries = [
        HistoryEntry(
            date=date(2026, 4, 1),
            template_name="solo_30min",
            exercise_ids=["a", "b"],
            notes="first",
        ),
        HistoryEntry(
            date=date(2026, 4, 15),
            template_name="team_75min",
            exercise_ids=["c"],
            notes="",
        ),
    ]

    save_history(entries, path)
    loaded = load_history(path)

    assert len(loaded) == 2
    assert loaded[0].date == date(2026, 4, 1)
    assert loaded[0].exercise_ids == ["a", "b"]
    assert loaded[0].notes == "first"
    assert loaded[1].template_name == "team_75min"


def test_append_entry_persists(tmp_path):
    from history import append_entry, load_history
    from models import HistoryEntry

    path = tmp_path / "log.json"
    append_entry(
        HistoryEntry(date=date(2026, 4, 1), template_name="t", exercise_ids=["x"]),
        path,
    )
    append_entry(
        HistoryEntry(date=date(2026, 4, 2), template_name="t", exercise_ids=["y"]),
        path,
    )

    loaded = load_history(path)

    assert len(loaded) == 2
    assert [e.exercise_ids[0] for e in loaded] == ["x", "y"]


def test_last_used_map_returns_most_recent_date(tmp_history_file):
    from history import last_used_map

    result = last_used_map(tmp_history_file)

    # mastery_1 appears in both entries (2026-04-01 and 2026-04-15) — take the later one.
    assert result["mastery_1"] == date(2026, 4, 15)
    assert result["pass_1"] == date(2026, 4, 1)


def test_last_used_map_empty_when_no_history(tmp_path):
    from history import last_used_map

    assert last_used_map(tmp_path / "missing.json") == {}
