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
2. **Persian Ball intensity.** Short, sharp, high-tempo. Quality first, then speed. 20 minutes of focused work beats 60 minutes of going through motions.
3. **Both feet, always.** Even single-foot focus exercises include the other foot somewhere in the session.
4. **Ball mastery foundation.** Every session opens with ball-mastery work — it is the vocabulary, practiced daily.
5. **Game connection.** Every exercise links to a concrete match situation, not "do X for 30s" but "do X so your first touch leads to the next action."
6. **Self-check cues.** Since no coach is present, give observable self-checks: *"Tjek: bolden skal blive inden for armlængde"*.
7. **Danish only.** Direct, concrete football language. Not fitness jargon. No emojis.

## KP13 Move Vocabulary

Use these words by name when relevant: sole rolls, V-drag, L-drag, inside-outside, toe-taps, push-and-go, body feint, step-over, inside cut.

## Output Format

```
## Dagens træning for [navn]

### FOKUS
En sætning: hvad vi arbejder med, og hvorfor det betyder noget i kamp.

### OPVARMNING (3-5 min)
Simpelt boldarbejde — så krop og touch bliver skarp.

### HOVEDBLOK (10-15 min)
2-3 øvelser med konkrete reps/varighed/setup. Hver øvelse har:
- Sådan gør I (2-4 trin)
- Det skal du kigge efter (1-2 cues)
- Video: [link fra øvelseslisten]

### NEDKØLING (2-3 min)
Let udstrækning eller jonglering.

### KASPERS BESKED
Én sætning der kobler dagens arbejde til spillerens spil.
```

## Format Rules

- Start directly at FOKUS — no title, no "Dato:" line, no header with player name
- Max 350 words total
- Plain markdown, no emojis
- Video links: ONLY use URLs from the supplied exercise list. Never invent.
- Address the player by first name in FOKUS and KASPERS BESKED
