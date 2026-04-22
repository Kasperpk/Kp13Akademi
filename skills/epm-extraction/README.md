# epm-extraction

Skill scaffold for extracting EPM dimension scores from coach session notes.

**Status:** Scaffold only. The skill itself (`SKILL.md`, `references/rubrics.md`, refactor of `extract_scores_from_notes`) lands in a follow-up pass once enough real eval cases have accumulated to validate the migration.

## What lives here

```
skills/epm-extraction/
  README.md             # this file
  evals/
    cases/              # one JSON per calibrated session (ground truth)
```

## How eval cases are produced

Cases are not labelled in a separate chore. They are a **byproduct of normal calibration practice**: when Kasper logs a session in the app and writes a rationale next to a dimension score, that dimension is treated as ground truth and a case JSON is appended here automatically by `app/core/eval_writer.py`.

A dimension only enters the case file if it has an explicit rationale. Dimensions where the AI proposed a number and Kasper clicked through without commentary are written to the DB only — they are not pretended to be ground truth.

## Case file format

```json
{
  "case_id": "felix_2026-04-22",
  "player_id": "felix",
  "date": "2026-04-22",
  "session_type": "coached",
  "session_theme": "...",
  "coach_notes": "...",
  "player_profile": { "name": "Felix", "age_group": "U9", ... },
  "expected": {
    "first_touch": [6.5, 7.5],
    "decision_speed": [3.5, 4.5]
  },
  "rationales": {
    "first_touch": "Anchor: 7/10 clean half-turns under live pressure",
    "decision_speed": "Defaults to safe pass when drive is on, 3 of 4 reps"
  }
}
```

`expected[dim] = [score - tolerance, score + tolerance]` — tolerance defaults to ±0.5. Rationale is the source-of-truth for *why* a dimension scored that way.

## When to run the eval

Once N ≥ 10 cases have accumulated. Until then, the eval is not statistically meaningful — single cases are too noisy to guide model selection. Use the period before that to keep calibrating in the normal app flow.
