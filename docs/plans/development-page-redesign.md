# Development page redesign — hours-first, periodic skill review

**Branch:** `feature/hours-first-development-page`
**Status:** Plan, not implemented. Open questions at the bottom.

## Context

The development page (both the Streamlit "Min Udvikling" view and the FastAPI player view at `/p/{token}/development`) currently leads with EPM dimension scores: focus areas, strengths, and a 16-dimension grid by category. That makes the player's primary feedback signal a **score**, which:

- Moves attention onto numbers that move slowly and noisily
- Implicitly invites score-chasing (gamification of a measurement layer)
- Hides the lever the player actually controls day-to-day: **how much they trained**

Hours trained is the dominant input to improvement at this age, and it's also the most motivating thing to see go up. So the page should lead with hours, and skill-level work should happen in a slower, coach-led cadence (~every 10 weeks) rather than as an always-visible dashboard.

The skill rubrics themselves (the beginner/medium/advanced descriptions in [app/core/rubrics.py](../../app/core/rubrics.py)) are valuable — they give shape to what improvement looks like. They should stay, but surface only inside the periodic review, not on the daily page.

## What we're keeping vs. changing

**Keep:**
- The rubric data in [app/core/rubrics.py](../../app/core/rubrics.py) — unchanged.
- The per-dimension level-description pattern from [app/pages/1_Min_Udvikling.py](../../app/pages/1_Min_Udvikling.py) lines 164–203 (current rubric + next-level "next step"). The user explicitly likes this and wants to preserve it.
- The EPM scoring, gap/strength logic, observation pipeline — unchanged. EPM stays as the coach's instrument; it's just no longer the primary thing the player sees.
- `get_training_hours()` in [app/core/database.py](../../app/core/database.py) — already returns what we need.

**Change:**
- The player-facing development page leads with **training hours**, not skill scores.
- The 16-dimension skill grid is **removed from the daily player view**.
- The rubric "Se niveau" experience moves into a new **10-week review** flow, coach-presented.

## Proposed design

### 1. Player development page — hours-first hero

Redesign [app/web/templates/development.html](../../app/web/templates/development.html) and [app/web/main.py:267-313](../../app/web/main.py#L267-L313).

Top-of-page hero (in priority order):
- **This week** — minutes/sessions trained
- **This month** — total hours
- **All-time** — total hours since joining (with start date for context)

Below the hero:
- **Activity grid** — last 8–12 weeks as a week-by-week visual (e.g., GitHub-style cells per week showing sessions). Lets the player see consistency without us naming a streak that "breaks."
- **Recent sessions** — list of the last 5–10 completed sessions with type, date, theme.

**No streak counter.** Per user feedback (2026-04-27): streaks risk turning training into a chore and stressing players who miss a week for legitimate reasons. The activity grid gives the same consistency signal without a number that resets to zero. The motivational lever stays in the planner (plans that adapt to busy weeks and are fun to follow), not in the dashboard.

Removed from this page:
- Focus areas / Strengths blocks (gap & strength badges)
- The 16-dimension category grid (with personal scores)
- The 5-stage legend at the bottom

Result: a player visiting `/p/{token}/development` sees how much they've trained — and nothing about their per-skill scores. See section 4 for what they *can* see about skills.

### 2. New surface: 10-week skill review (coach-led, dedicated page)

A dedicated Streamlit page the coach runs every ~10 weeks with the player present. New file: [app/pages/7_10_uger_review.py](../../app/pages/).

The page is a guided session — pick a player → walk through each core skill → for each one show the current level (rubric description matching today's score) and the next-level description, identical in shape to today's `1_Min_Udvikling.py` lines 164–203. The coach narrates while the player watches. At the end: pick 1–3 dimensions to focus on for the next 10 weeks.

The rubric-rendering kernel is extracted from `1_Min_Udvikling.py` lines 164–203 into a shared helper (e.g., `app/core/review.py`) so both this page and the player-facing "mastery levels" page in section 4 can reuse it.

The user noted (2026-04-27) it's hard to judge between "dedicated page" and "tab on existing page" without seeing it. Default to dedicated page; if it feels like overkill once built, fold it back into `1_Min_Udvikling.py` as a tab.

**Output:** a markdown artifact at `clients/{player}/reviews/YYYY-MM-DD.md` capturing the levels seen and the chosen focus areas. No DB persistence in v1 — keeps the change minimal and matches the existing per-player markdown pattern in `clients/`. We can promote to a DB row if review history needs to be queried.

### 3. Streamlit "Min Udvikling" — also realigned

Mirror the player FastAPI page's hours-first structure as the default view. Keep the rubric expanders accessible behind a clear "10-ugers review" entry point, not on the front of the page.

### 4. Player-facing "Mastery levels" page (educational, no personal score)

This is the key design move from the 2026-04-27 conversation: **players never see their own skill levels**, but they *do* see the rubrics as teaching content. They can read what mastery looks like for every skill — they just don't see where they personally are on the ladder.

New route: `GET /p/{token}/mastery` (or `/skills`) on the FastAPI app. New template [app/web/templates/mastery.html](../../app/web/templates/).

For each of the 16 dimensions, the page shows:
- Skill name + short description (from `DimensionMeta.description` in [app/core/epm.py](../../app/core/epm.py)).
- All 5 rubric levels expanded — `1-2`, `3-5`, `6-7`, `8-9`, `10` — pulled from [app/core/rubrics.py](../../app/core/rubrics.py). The full ladder, generic, with no "you are here" marker anywhere.
- Optionally: collapsed by default with the `10/10` "Elite" line as the headline, expand to see the full progression.

The player learns "if I'm at 10/10 in first touch, the ball sits perfectly every time" without ever being told their current number. The 10-week review is where the coach reveals personal level.

This page is reachable from the bottom nav (replacing or alongside the existing "Development" link). Suggested label: "Færdigheder" / "Skills" or "Mestring" / "Mastery."

**Why this works:** the rubric content has two values — (a) it's a measurement instrument for the coach, (b) it's a teaching tool that defines what "good" looks like. Today both functions live on the same surface, which entangles "what does mastery look like?" with "where am I right now?" Splitting them: (a) goes to the coach-led 10-week review; (b) becomes a passive reference page available to the player anytime.

## Files to change

- [app/web/templates/development.html](../../app/web/templates/development.html) — full rewrite (hours hero + activity grid + recent sessions). No skill scores.
- [app/web/main.py:player_development](../../app/web/main.py#L267-L313) — replace the EPM-prep block with a hours+activity payload. Add a helper for the last-N-weeks activity grid.
- New: [app/web/main.py:player_mastery](../../app/web/main.py) — new route serving the educational "all rubric levels, no personal score" page.
- New: [app/web/templates/mastery.html](../../app/web/templates/) — renders the 16 skills with their full rubric ladders.
- [app/web/templates/base.html](../../app/web/templates/base.html) — bottom nav: replace or rename "Development" entry, add a "Mestring/Skills" entry.
- [app/pages/1_Min_Udvikling.py](../../app/pages/1_Min_Udvikling.py) — restructure: hours/activity hero at top, "Start 10-ugers review" button leading to the new review page. Rubric block leaves this page (it lives on the new pages now).
- New: [app/core/review.py](../../app/core/review.py) — shared rubric-presentation helpers extracted from `1_Min_Udvikling.py` lines 164–203 so the review page, the player mastery page, and (if needed later) the Streamlit "Min Udvikling" page can reuse the same rendering.
- New: [app/pages/7_10_uger_review.py](../../app/pages/) — guided coach-led 10-week review. Writes a markdown artifact to `clients/{player}/reviews/YYYY-MM-DD.md`.
- No DB schema change required.

Untouched:
- [app/core/epm.py](../../app/core/epm.py), [app/core/recommender.py](../../app/core/recommender.py), [app/core/elm.py](../../app/core/elm.py) — coaching loop continues unchanged.
- [app/core/rubrics.py](../../app/core/rubrics.py) — content unchanged.

## Out of scope (for this issue)

- Pushing reminders ("you've trained 3h this week, one more session for your streak")
- Coach-side review history view across multiple cycles
- Persisting reviews to the DB (v1 = markdown artifacts in `clients/{player}/reviews/`)
- Backfilling historic activity data (we use what's already in `session_completions` / `daily_plans` / `session_observations` / `player_sessions`)

## Verification

1. `/p/{token}/development` shows training hours hero + activity grid + recent sessions. No focus areas, no strengths, no skill grid, no streak counter.
2. `/p/{token}/mastery` shows all 16 skills with their full rubric ladders, no personal score anywhere on the page.
3. Streamlit "Min Udvikling" leads with the hours view; the rubric expanders no longer live here.
4. The new 10-week review page renders current + next-level rubric for each core skill (same UX kernel as today's `1_Min_Udvikling.py` lines 164–203), and writes a dated markdown artifact to `clients/{player}/reviews/`.
5. No regression on `make test`.
6. Manually verified for both players (Sofus, Felix) on dev DB.

## Resolved decisions (2026-04-27)

- **Streak**: dropped. Activity grid gives the consistency signal without a number that punishes missed weeks.
- **Review surface**: dedicated Streamlit page. Revisit if it feels like overkill once built.
- **Player skill peek**: players never see their personal levels. They *do* see the full rubric content for every skill on a separate "Mastery levels" page — generic, educational, no personal score.
- **Review output**: markdown artifact in `clients/{player}/reviews/YYYY-MM-DD.md` for v1. No DB row. Promote later if needed.

## Still open — decide during implementation, low risk

- **Cadence trigger** — strict 10-week cron from `started_date`, coach-initiated whenever, or suggested-but-not-enforced? Lean toward coach-initiated, with a "last review was N weeks ago" hint visible to the coach.
- **First review for existing players** — Sofus and Felix have ~3 weeks of data. Run their first review whenever the coach wants; subsequent ones can fall into a 10-week rhythm.
- **Mastery page label** — "Mestring" / "Skills" / "Færdigheder" / something else. Pick during the template build.
