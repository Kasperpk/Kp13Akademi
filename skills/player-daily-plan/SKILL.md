---
name: player-daily-plan
description: Generate a single-day, 15-25 minute SOLO home training session in Danish for a KP13 academy player. Use when producing the player's daily home plan that supplements Kasper's weekly academy session. Enforces Persian Ball intensity, both-feet, ball-mastery foundation, and the specific KP13 output format (FOKUS / OPVARMNING / HOVEDBLOK / NEDKØLING / KASPERS BESKED).
---

# KP13 Daily Home-Training Session

## When to Use

- Generating the player's daily home training plan (15-25 min)
- The supplement to Kasper's weekly 1-on-1 academy session
- The player will train **alone with one ball** — no coach, no parent assumed present

## Hard Constraints

These are non-negotiable. Violating any of them is a defect.

1. **Solo only.** Every exercise must work with one player and one ball. Wall optional. Phone timer for intervals. Never "pass to your dad", never "Kasper says/calls/counts/watches".
2. **No "Forældre:" sections. Ever.** Do not address parents anywhere in the output. Each exercise gets one "**Fokus:**" line directed at the player — a single observable self-check they can do alone: *"Fokus: bolden skal blive inden for en armslængde"*.
3. **Persian Ball intensity.** Short, sharp, high-tempo. Quality first, then speed. 20 minutes of focused work beats 60 minutes of going through motions.
4. **Both feet, always.** Even single-foot focus exercises include the other foot somewhere in the session.
5. **Ball mastery foundation.** Every session opens with ball-mastery work — it is the vocabulary, practiced daily.
6. **Game connection.** Every exercise links to a concrete match situation, not "do X for 30s" but "do X so your first touch leads to the next action."
7. **Self-check cues.** Since no coach is present, give observable self-checks the player can use alone.
8. **Danish only.** Direct, concrete football language. Not fitness jargon. No emojis.

## KP13 Move Vocabulary

Use these words by name when relevant: sole rolls, V-drag, L-drag, inside-outside, toe-taps, push-and-go, body feint, step-over, inside cut.

## Output Format

```
### FOKUS
En sætning: hvad vi arbejder med, og hvorfor det betyder noget i kamp.

### OPVARMNING (3-5 min)
Simpelt boldarbejde — så krop og touch bliver skarp.

**[Øvelsesnavn]** — [reps/varighed]
[2-4 trin beskrivelse]
Fokus: [ét observerbart self-check for spilleren]
Video: [URL fra exercise-videos.md — udelad linjen helt hvis ingen URL er registreret]

### HOVEDBLOK (10-15 min)
2-3 øvelser med konkrete reps/varighed/setup.

**[Øvelsesnavn]** — [reps/varighed]
[2-4 trin beskrivelse]
Fokus: [ét observerbart self-check for spilleren]
Video: [URL fra exercise-videos.md — udelad linjen helt hvis ingen URL er registreret]

### NEDKØLING (2-3 min)
Let boldleg eller kontrol.

**[Øvelsesnavn]** — [varighed]
[Kort beskrivelse]
Fokus: [ét observerbart self-check for spilleren]

### KASPERS BESKED
Én sætning der kobler dagens arbejde til spillerens spil.
```

## Format Rules

- Start directly at FOKUS — no title, no "Dato:" line, no header with player name
- Max 350 words total
- Plain markdown, no emojis
- Never use "Forældre:" anywhere — not even once
- **Video links:** Look up the exercise name in `exercise-videos.md`. If a URL exists, include `Video: [url]`. If no URL is listed, omit the Video line entirely. Never invent URLs.
- Address the player by first name in FOKUS and KASPERS BESKED

## Exercise Video Registry

Before generating, check `skills/player-daily-plan/exercise-videos.md` for recorded video URLs. Each entry maps an exercise name to a Cloudinary URL. Only include a `Video:` line when the URL is present in that file.
