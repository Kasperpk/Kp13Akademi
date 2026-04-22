# Clients

Individual player management. One folder per client. The markdown files here are the **canonical narrative source of truth** — the SQLite DB stores derived state (EPM scores, observations, score history), but the "why" lives in markdown.

## How to add a new client

1. Copy the `_template/` folder
2. Rename it to the player's name (e.g., `lucas/` or `lucas-hansen/`)
3. Fill in `profile.md` (who they are) and `goals.md` (what they're working toward)
4. Record baseline measurements in `benchmarks.md`
5. Write a starting-point entry in `history.md`
6. Add a session file after each training in `sessions/`
7. Keep running observations in `notes/ongoing.md`

## Structure per client

```
clients/
└── player-name/
    ├── profile.md        — who they are (identity, dimension anchors, context)
    ├── goals.md          — what they're working toward (focus areas, long-term)
    ├── benchmarks.md     — measured numbers over time (append-only test log)
    ├── history.md        — narrative milestones (append-only progress evidence)
    ├── sessions/         — one file per training session
    │   └── YYYY-MM-DD.md
    └── notes/
        └── ongoing.md    — running coaching observations (append-only)
```

## What lives where

| File | Purpose | Write cadence |
|---|---|---|
| `profile.md` | Identity + per-dimension anchors | Edit when the player changes (new role, new injury, new strength) |
| `goals.md` | Current focus + long-term goals | Update when a block ends or focus shifts |
| `benchmarks.md` | Hard-number test log (sprint times, juggling, etc.) | Append every 6–8 weeks or before/after tournaments |
| `history.md` | Narrative milestones, the story of progress | Append every 6–8 weeks and after every tournament |
| `notes/ongoing.md` | Dated running observations incl. EPM calibration blocks | Appended automatically by the Log Træning page; add manually any time |
| `sessions/<date>.md` | Full per-session plans + observations | One per training session |

All six feed into `build_player_context()` in `app/core/clients_loader.py` — when the AI extracts scores from coach notes, it sees the entire narrative context.

## Evidence of progress

Two sources prove the player is improving:

- **Quantitative trajectory** — lives in the DB. Every calibrated score is written to `epm_history` ([database.py:43](../app/core/database.py#L43)), and the raw per-session coach-adjusted scores live in `session_observations.extracted_scores`. This supports time-series charts per dimension.
- **Narrative milestones** — live in `history.md`. Written in prose, tied to tournament moments and benchmark deltas. This is the story a chart can't tell.

## Current clients

- [Felix](felix/) — U9, started 2026-04-14
- [Sofus](sofus/) — U9, started 2026-04-05
