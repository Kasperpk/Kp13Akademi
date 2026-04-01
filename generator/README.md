# Football Session Generator

A Python CLI tool for designing varied training sessions based on La Masia philosophy,
PersianBall ball mastery, and evidence-based coaching methodology.

## Quick Start

```bash
cd generator
pip install -r requirements.txt
python generate.py
```

## How It Works

1. **Choose a template** — `individual` (1-on-1) or `u9_team` (La Masia team session)
2. **Set the date** and player count
3. **Pick exercises for each phase** — browse filtered candidates, see recency info, or let the tool pick randomly (weighted toward least-recently-used)
4. **Preview** the session in your terminal
5. **Save** — outputs a Markdown session plan to `output/` and logs to history

## Project Structure

```
generator/
├── exercises/           # YAML exercise library (~120 exercises)
│   ├── warmup.yaml
│   ├── ball_mastery.yaml
│   ├── rondo.yaml          # La Masia rondos
│   ├── positional_play.yaml # La Masia positional exercises
│   ├── passing.yaml
│   ├── receiving.yaml
│   ├── finishing.yaml
│   ├── agility.yaml
│   ├── small_sided_games.yaml
│   ├── one_v_one.yaml
│   ├── cool_down.yaml
│   └── strength.yaml
├── templates/
│   ├── individual.yaml  # 1-on-1 session template
│   └── u9_team.yaml     # U9 La Masia team template
├── history/
│   └── log.json         # Session history (auto-updated)
├── principles/
│   ├── la_masia.md      # La Masia philosophy reference
│   └── methodology.md   # Evidence-based methodology tags
├── output/              # Generated session plans
├── generate.py          # Main CLI entry point
├── models.py            # Pydantic data models
├── library.py           # Exercise loading & filtering
├── history.py           # Session history tracking
├── renderer.py          # Markdown output renderer
└── requirements.txt
```

## Adding Exercises

Add entries to any YAML file in `exercises/`. Each exercise follows this schema:

```yaml
- id: unique_slug
  name: "Exercise Name"
  description: "1-2 sentence description"
  category: warmup  # warmup|ball_mastery|rondo|positional_play|passing|receiving|finishing|agility|small_sided_games|one_v_one|cool_down|strength
  coaching_points:
    - "Key coaching cue 1"
    - "Key coaching cue 2"
  age_range: [6, 25]
  min_players: 1
  max_players: null     # null = unlimited
  space: small_10x10    # minimal_3x3|small_10x10|medium_20x20|half_pitch|full_pitch
  equipment: [ball, cones]
  duration_seconds: [60, 300]  # [min, max] range
  intensity: moderate   # low|moderate|high|maximum
  methodology_tags: [game_realistic, decision_making]
  physical_tags: [acceleration, change_of_direction]
  la_masia_principles: [possession, technical_excellence]
  variations:
    - name: "Variation name"
      description: "How to modify the exercise"
  source: "la_masia"   # optional attribution
```

## Creating Custom Templates

Add a YAML file to `templates/` following this structure:

```yaml
name: "Template Name"
context: "team"  # or "individual"
total_duration_minutes: [75, 90]

phases:
  - name: "Phase Name"
    duration_minutes: [10, 15]
    required_categories:
      - warmup
    min_exercises: 2
    max_exercises: 4
    notes: "Coaching guidance for this phase"
```

## Session History

Every saved session is logged to `history/log.json`. The tool uses this to:
- Show when each exercise was last used
- Weight random selection toward least-recently-used exercises
- Help you avoid repetition across sessions

## Methodology

See `principles/la_masia.md` and `principles/methodology.md` for the coaching
philosophy and evidence-based methodology underlying the exercise library.
