# KP13 Akademi — Player Intelligence System

## The Problem We Solve

Parents see their kid light up when they play football. The kid wants to get better but club training alone isn't enough — it's designed for the group, not the individual. Parents want to help but don't know how. They don't know what to train, how much, or whether what they're doing is actually working. They're flying blind.

**KP13 Akademi gives every player a personal development system.** Wake up, open the app, know exactly what to do today. See yourself getting better. Understand why you're doing what you're doing. All grounded in elite coaching methodology, all adapted to you.

---

## Buyer Personas — Who We Build For

### The Invested Parent

**Trigger:** Their kid loves football, is showing talent or passion, but isn't developing fast enough through club training alone. Or: they see other kids getting private coaching and worry about falling behind.

**Expected outcome:** "Just tell us what to do." Clear structure, visible improvement, and the kid enjoying training *more* because they feel themselves getting better.

**Fears:**
- Wasting money on another football camp that changes nothing
- Pushing the kid too hard and killing the joy
- Not knowing if the training is actually good ("smart people who think they know what to do but actually don't")
- Paying for something they could do themselves if they just knew how

**Decision question:** "How do I know it's working?"

**What wins the deal (Lagoon Oasis principle):** Make them feel *confident and secure*. Don't sell 50 drill options — deliver one clear plan per day, show progress over time, and be transparent about methodology. The parent who feels "this person understands my kid and has a plan" will choose you every time.

### The Ambitious Kid (U8–U12)

**Trigger:** Watches football on TV, wants to be like their favourite player, gets frustrated when they can't do what the best kids do.

**Expected outcome:** Feel like a real footballer. Know what the best players at their age can do and see themselves closing the gap. Have "their thing" — a personal training identity.

**Fears:**
- Being embarrassed (drills that are too hard and feel like failure)
- Being bored (repetitive drills with no game connection)
- Not understanding why they're doing something

**What wins:** Make it feel like *their* journey. "You're working on driving with speed today because last week you improved your close control by 12% — now it's time to use it in game situations." Connect every session to their real matches and real progress.

---

## The Intelligence System

Built on Schmarzo's Intelligence Analytics framework: **Entity Propensity Models** (EPMs) per player, **Entity Language Models** (ELMs) as the interface, **causal models** for understanding why, and **feedback loops** that make the system smarter with every session.

### Layer 1: Player EPM — The Digital Twin

Every player gets a living model across four dimensions, each scored 1–10 and updated after every coached session and logged home session.

#### Technical Dimension

| Score | What It Measures | How It's Observed |
|-------|-----------------|-------------------|
| `first_touch` | Receiving quality — controlling the ball into space, on the half-turn, under pressure | Coach observation during passing/receiving drills and game forms |
| `passing` | Weight, accuracy, and decision-making in distribution | Rondos, positional play, game situations |
| `ball_mastery` | Close control, comfort on the ball, moves repertoire | Ball mastery drills, pressure dribbling |
| `dribbling_speed` | Carrying the ball at pace, push-and-go, dynamic ball carrying | Driving drills, 1v1s, game forms with space to exploit |
| `finishing` | Shooting technique, composure in front of goal | Finishing drills after combination play |
| `weak_foot` | Proficiency with non-dominant foot across all skills | Tracked across all drill types (tagged in exercise metadata) |

#### Physical Dimension

| Score | What It Measures | How It's Observed |
|-------|-----------------|-------------------|
| `acceleration` | First 3–5 steps, explosive starts, reactive speed | Agility drills, sprint starts, 1v1 races |
| `agility` | Change of direction, lateral movement, body control | Agility courses, reactive drills, defensive transitions |
| `endurance` | Sustained intensity across a full session or match | Session-level observation, intensity maintenance in final phase |

#### Cognitive/Tactical Dimension

| Score | What It Measures | How It's Observed |
|-------|-----------------|-------------------|
| `game_reading` | Positional awareness, scanning, anticipation | Positional play, SSGs, shoulder-checking frequency |
| `decision_speed` | Choosing the right action under pressure (drive vs pass, press vs hold) | Game forms, constrained SSGs, rondo decision moments |
| `positional_play` | Understanding of space, movement off the ball, creating angles | Positional exercises, off-ball movement in SSGs |

#### Mental/Character Dimension

| Score | What It Measures | How It's Observed |
|-------|-----------------|-------------------|
| `resilience` | Response to setbacks, mistakes, losing, tournament pressure | Coach observation during competitive moments |
| `intensity` | Effort, tempo, urgency in training | Rated every session as a baseline |
| `coachability` | Willingness to try new things, response to feedback | Session-by-session observation |
| `joy` | Engagement, enthusiasm, fun level | Critical health metric — if this drops, something is wrong |

**Total: 16 EPM dimensions** — enough to be meaningful, few enough to rate consistently after each session.

#### Scoring Protocol

After every coached session, the coach provides:
1. **Free-text observations** (what they naturally write already — see ongoing.md notes)
2. **Claude extracts structured ratings** via tool_use (same pattern as deep-work-advisor's `fill_session_fields`)
3. **Scores update via exponential moving average**: `new = (1 - α) × old + α × observed`, where α = 0.3 (recent sessions weighted more, but history smooths noise)
4. **Each score carries a confidence level** based on number of observations (low/medium/high)

#### EPM Design Canvas (per player)

```
┌─────────────────────────────────────────────────────┐
│  ENTITY: Felix Kirk Nebel (U9, Central/Wing)        │
├─────────────────────────────────────────────────────┤
│  DATA SOURCES                                       │
│  • Coach session observations (free-text + ratings) │
│  • Home training completion logs                    │
│  • Match/tournament observations                    │
│  • Parent feedback (engagement, mood at home)       │
├─────────────────────────────────────────────────────┤
│  PROPENSITY SCORES                                  │
│  Technical:  first_touch: 7.2  passing: 8.1         │
│              ball_mastery: 7.5  dribbling_speed: 4.8 │
│              finishing: 5.5    weak_foot: 5.0        │
│  Physical:   acceleration: 5.0  agility: 5.5        │
│              endurance: 6.0                          │
│  Cognitive:  game_reading: 6.5  decision_speed: 4.5 │
│              positional_play: 7.0                    │
│  Mental:     resilience: 6.0  intensity: 5.0        │
│              coachability: 8.0  joy: 8.5             │
├─────────────────────────────────────────────────────┤
│  KEY INSIGHT (from causal model)                    │
│  Felix's dribbling_speed (4.8) is bottlenecked by   │
│  decision_speed (4.5), not physical ability. He CAN │
│  drive but doesn't CHOOSE to. Prescribe constrained │
│  games where driving is rewarded, not just allowed. │
└─────────────────────────────────────────────────────┘
```

### Layer 2: Causal Model — Understanding Why

A Directed Acyclic Graph (DAG) per player capturing the real causal relationships:

```
training_frequency ──→ skill_acquisition_rate ──→ technical_scores
                                                        │
home_practice_consistency ──→ technical_foundation ──────┘
                                                        │
session_quality (focus, intensity) ──→ skill_retention ─┘
                                                        
match_experience ──→ decision_making_under_pressure ──→ cognitive_scores
                            ↑                                  │
            resilience ─────┘                                  │
                                                               │
coaching_method (constraints vs explicit) ──→ transfer_rate ───┘
                            ↑
          coachability ─────┘

joy ──→ training_frequency ──→ everything
```

**The critical causal insight already visible in your data:**

- **Sofus**: High technical base → but poor transfer under pressure → caused by low resilience → which causes him to default to safe actions under tournament stress. The intervention isn't more technical drills — it's building resilience through progressively pressured environments.
- **Felix**: High passing ability → but low dribbling_speed usage → bottlenecked by decision_speed not physical ability → the intervention is constrained games that *demand* driving, not drills that *allow* it.

The causal model enables **counterfactual reasoning**: "What if we increased Sofus's training frequency from 1x/week to 2x/week individual + 3x home sessions? Based on similar development curves, his transfer_rate would likely improve because more reps under pressure builds the automaticity needed for tournament performance."

### Layer 3: ELM — The Daily Interface

The Entity Language Model translates EPM data into natural language guidance. Three interfaces:

#### A. Player Morning View (Daily)

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Good morning Felix! 🟢 Training day
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  TODAY'S FOCUS: Driving into space
  ─────────────────────────────────
  You've been nailing your passing this week (8.1 ⬆️)
  Now it's time to add the drive. When you receive  
  with space ahead — GO.

  🏋️ Home Session (20 min)
  1. Ball mastery warm-up (5 min) — sole rolls,
     inside-outside, both feet
  2. Push-and-go sprints (8 min) — set up 2 cones
     10m apart, receive → big touch → sprint → stop
     Reps: 6 right foot, 6 left foot
  3. Drive-or-pass decision game (7 min) — 
     parent calls "GO" or "PASS" as you receive
     
  WHY THIS MATTERS
  In Tuesday's session you had 3 moments where you
  could have driven but chose the safe pass. This
  drill builds the habit so it becomes automatic.

  📊 YOUR PROGRESS (last 4 weeks)
  Dribbling speed:  ████░░░░░░  4.8  (+0.6)
  Decision speed:   ████░░░░░░  4.5  (+0.3)
  Passing:          ████████░░  8.1  (+0.2)
  
  NEXT COACHED SESSION: Saturday April 19
  Theme: 1v1 situations with finish after drive
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

#### B. Parent Weekly Summary

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Felix — Week 2 Summary
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  
  WHAT WE WORKED ON
  This week focused on driving with the ball at  
  speed — Felix's #1 development area. We did 1  
  coached session and Felix completed 3 home sessions.
  
  WHAT I SAW
  Felix's technique for carrying the ball is improving.
  In the coached session he drove past defenders twice
  — something he wouldn't attempt two weeks ago. The 
  decision to drive vs pass is still developing but the
  physical ability is clearly there.
  
  WHAT'S NEXT
  Next week we add game-realistic pressure: 1v1  
  duels leading to a finish, and small-sided games  
  where driving earns bonus points. The goal is to  
  make driving feel like a natural option, not a  
  forced one.
  
  💡 HOW YOU CAN HELP
  When you play in the garden, challenge him to  
  "beat you" with the ball rather than passing around  
  you. Celebrate the attempts, not just the successes.
  
  PROGRESS SNAPSHOT
  ┌────────────────┬──────┬───────┬────────┐
  │ Dimension      │ Now  │ Start │ Change │
  ├────────────────┼──────┼───────┼────────┤
  │ Dribbling speed│  4.8 │  3.9  │  +0.9  │
  │ Decision speed │  4.5 │  4.0  │  +0.5  │
  │ Passing        │  8.1 │  7.8  │  +0.3  │
  │ Intensity      │  5.5 │  5.0  │  +0.5  │
  │ Joy            │  8.5 │  8.5  │   0.0  │
  └────────────────┴──────┴───────┴────────┘
  
  Joy is steady at 8.5 — Felix is enjoying this. ✓
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

#### C. Coach Session Logger (Post-Session)

Same pattern as deep-work-advisor's log session page:

1. **Free-text notes** — coach writes naturally (like the ongoing.md entries you already write)
2. **Claude extracts structured ratings** — via tool_use, maps observations to EPM dimensions
3. **Coach reviews and adjusts** — confirms or overrides AI suggestions
4. **Save** — EPM updates, feedback loop runs, next session recommendations adjust

### Layer 4: Feedback Loops — How It Gets Smarter

Three feedback loops, directly from the deep-work-advisor pattern:

#### Loop 1: Session-Level (after every coached session)

```
Coach logs session (free-text) 
  → Claude extracts EPM dimension ratings
  → Scores update via EMA (α = 0.3)
  → Recommendation engine adjusts:
     - Which exercises to prescribe for home training
     - Which theme for next coached session  
     - Which dimensions need attention
```

#### Loop 2: Transfer Tracking (coached session → team/match observation)

```
Individual session works on [skill]
  → Coach observes team training or match
  → Notes whether skill transferred to game context
  → If not: increase pressure/game-realism in individual sessions
  → If yes: move to next development priority
```

This is already happening in your notes — the April 15 observations for both Felix and Sofus explicitly track transfer. The system formalizes it.

#### Loop 3: Program-Level (monthly/quarterly)

```
Review EPM score trajectories across all dimensions
  → Identify: what's improving, what's stalling, what's declining
  → Causal analysis: WHY is something stalling?
     (not enough reps? wrong drill type? mental blocker?)
  → Adjust development plan for next period
  → Update parent on trajectory and revised focus
```

### Layer 5: Benchmark Engine — "How Do I Compare?"

Age-group development benchmarks built from:
1. **Your own coaching data** — as you train more players, you build a proprietary dataset of what typical U9/U10/U11 development looks like across all 16 dimensions
2. **Published development frameworks** — La Masia age-stage expectations, FA/DBU development guidelines, sports science literature on motor skill acquisition rates
3. **Top-player reference profiles** — simplified models of what elite players at each age demonstrate (used for aspiration, not pressure)

Presented to the player as: "Your first touch is 7.2. Players who went on to play at elite U13 level averaged 7.5 at your age. You're on track."

**Critical design rule**: Benchmarks are for motivation, never for pressure. The `joy` score is the system's health metric — if joy drops while we push benchmarks, the system flags it immediately and the coach intervenes.

---

## Technical Architecture

### Extending What Exists

The current system is not thrown away — it becomes the content engine that feeds the intelligence layer.

```
┌──────────────────────────────────────────────────────────┐
│                    PLAYER INTERFACE                       │
│         (Streamlit / Mobile-friendly web app)            │
│                                                          │
│  ┌─────────┐  ┌──────────┐  ┌─────────┐  ┌───────────┐ │
│  │ Daily   │  │ Progress │  │ Session │  │  Weekly   │ │
│  │ Plan    │  │ Dashboard│  │ Logger  │  │  Review   │ │
│  └────┬────┘  └────┬─────┘  └────┬────┘  └─────┬─────┘ │
│       │            │             │              │        │
├───────┴────────────┴─────────────┴──────────────┴────────┤
│                    ELM LAYER (Claude)                     │
│  • Three-tier prompt caching (player history → recent    │
│    sessions → current request)                           │
│  • Tool_use for structured extraction from coach notes   │
│  • Streaming responses for daily plans & weekly reviews  │
├──────────────────────────────────────────────────────────┤
│                    EPM LAYER                              │
│  • 16 dimensions per player, EMA-updated                 │
│  • Causal model (DAG) per player                         │
│  • Benchmark engine (age-group comparisons)              │
│  • Recommendation engine (exercise selection)            │
├──────────────────────────────────────────────────────────┤
│                 CONTENT ENGINE (existing)                 │
│  ┌───────────┐  ┌────────────┐  ┌─────────────────────┐ │
│  │ Exercise  │  │ Principles │  │ Session Templates   │ │
│  │ Library   │  │ (La Masia, │  │ (individual, team)  │ │
│  │ (120+     │  │  CLA, etc) │  │                     │ │
│  │ YAML)     │  │            │  │                     │ │
│  └───────────┘  └────────────┘  └─────────────────────┘ │
├──────────────────────────────────────────────────────────┤
│                    DATA LAYER                             │
│  • SQLite (local) + Google Sheets (sync/backup)          │
│  • Player profiles, EPM scores, session logs,            │
│    feedback history, benchmark data                      │
│  • Exercise usage history (existing log.json → SQLite)   │
└──────────────────────────────────────────────────────────┘
```

### New Data Models (extending existing models.py)

```python
class EPMDimension(str, Enum):
    # Technical
    FIRST_TOUCH = "first_touch"
    PASSING = "passing"
    BALL_MASTERY = "ball_mastery"
    DRIBBLING_SPEED = "dribbling_speed"
    FINISHING = "finishing"
    WEAK_FOOT = "weak_foot"
    # Physical
    ACCELERATION = "acceleration"
    AGILITY = "agility"
    ENDURANCE = "endurance"
    # Cognitive
    GAME_READING = "game_reading"
    DECISION_SPEED = "decision_speed"
    POSITIONAL_PLAY = "positional_play"
    # Mental
    RESILIENCE = "resilience"
    INTENSITY = "intensity"
    COACHABILITY = "coachability"
    JOY = "joy"

class PlayerEPM(BaseModel):
    player_id: str
    scores: dict[EPMDimension, float]          # current EMA scores
    confidence: dict[EPMDimension, str]         # low/medium/high
    observation_count: dict[EPMDimension, int]  # how many data points
    last_updated: date
    causal_insights: list[str]                  # coach-confirmed causal notes

class SessionObservation(BaseModel):
    date: date
    player_id: str
    session_type: str                           # "coached" | "home" | "match"
    theme: str
    coach_notes: str                            # free text
    extracted_scores: dict[EPMDimension, float] # Claude-extracted ratings
    coach_adjusted: bool                        # did coach override AI?
    exercises_used: list[str]                   # exercise IDs from library
    transfer_observed: bool | None              # did previous skill transfer?

class DailyPlan(BaseModel):
    date: date
    player_id: str
    focus_dimension: EPMDimension
    exercises: list[PlannedExercise]
    why_this_matters: str                       # ELM-generated explanation
    connection_to_goals: str                    # links to player goals
```

### Mapping Exercises to EPM Dimensions

The existing exercise YAML metadata already supports this. Each exercise has `methodology_tags`, `physical_tags`, and `la_masia_principles`. We add one field:

```yaml
# In each exercise YAML
epm_dimensions:
  - first_touch
  - passing
  - decision_speed
```

This enables the recommendation engine: "Felix needs to improve dribbling_speed (4.8) and decision_speed (4.5) → select exercises tagged with those dimensions, weighted by recency and difficulty progression."

---

## Build Phases

### Phase 1 — MVP: Coach Intelligence Tool (Weeks 1–4)

**Goal:** Digitize what you already do. The coach gets an EPM-powered tool. Parents get a weekly summary.

1. **Extend models.py** with `EPMDimension`, `PlayerEPM`, `SessionObservation`
2. **Build the session logger** — coach writes free-text notes → Claude extracts EPM ratings → coach confirms → scores update
3. **Migrate existing client data** — convert Sofus and Felix profiles, goals, and notes into initial EPM scores (baseline assessment)
4. **Build the EPM dashboard** — Streamlit page showing each player's 16 dimensions as a radar chart with trend lines
5. **Add `epm_dimensions` tags** to exercise YAML files

**Output:** Coach uses the tool after every session. EPM scores start accumulating. The system is learning.

### Phase 2 — Parent Interface (Weeks 5–8)

**Goal:** Parents and players see progress. The buyer persona comes alive.

1. **Weekly parent summary** — ELM generates a natural language report from the week's EPM changes + coach notes
2. **Progress dashboard** — simple, clean view of scores over time with explanations
3. **Benchmark comparisons** — initial benchmarks from your coaching experience + published frameworks
4. **"How you can help" section** — specific guidance for parents (e.g., "Challenge him to beat you with the ball in the garden")

**Output:** Parents receive a weekly email/message with their kid's progress. They feel informed and confident. This is the Lagoon Oasis moment — making the buyer feel secure.

### Phase 3 — Daily Player Plans (Weeks 9–12)

**Goal:** The kid wakes up and knows what to do.

1. **Recommendation engine** — selects exercises from the library based on EPM gaps, causal model, and session history
2. **ELM daily plan generation** — personalized plan with "why this matters" explanation
3. **Home session logging** — simple "did you do it? how did it feel?" → feeds back into EPM
4. **Transfer tracking** — coach marks whether home training skills showed up in the next coached session

**Output:** Felix opens the app Monday morning and sees exactly what to do for 20 minutes. After coached sessions, the plan adjusts. The system compounds.

### Phase 4 — Intelligence Compounding (Ongoing)

**Goal:** The system gets smarter than any single coach could be alone.

1. **Cross-player learning** — patterns across all players inform benchmarks and development predictions
2. **Causal model refinement** — which interventions actually caused improvement? Counterfactual analysis.
3. **Curriculum generation** — auto-generate proforløb (course sequences) based on player EPM + goals
4. **Self-calibrating weights** — feedback loop adjusts how much weight different observation types carry (same pattern as deep-work-advisor's EMA weight updates)

---

## The Competitive Moat

Every session makes the system smarter. Every player adds to the benchmark data. Every feedback loop tightens the recommendations. This is Schmarzo's core thesis: **intelligence analytics compound in value**. A competitor who starts tomorrow is 6 months of learning behind.

The exercise library is replicable. The coaching methodology is learnable. But a living, adaptive intelligence system that knows each player's causal model, tracks transfer from training to matches, and generates personalized daily plans grounded in hundreds of accumulated observations — that's not replicable. That's the edge.

---

## What Makes This Different (Answering the Buyer's Decision Question)

"What makes this different from a regular football school?"

1. **Your kid gets a personal development model.** Not a generic curriculum — an adaptive system that knows their strengths, weaknesses, and what they need next.
2. **You'll see it working.** Weekly progress reports with real scores, not vague "he did great today."
3. **Every session connects.** Home training builds on coached sessions. Coached sessions build on home training. Nothing is isolated.
4. **The system learns.** It gets better at knowing what your kid needs with every session, every observation, every data point.
5. **Joy is a first-class metric.** If your kid stops enjoying it, we'll know before you do — and we'll adjust.
