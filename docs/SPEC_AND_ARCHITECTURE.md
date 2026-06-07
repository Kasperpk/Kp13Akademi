# KP13 Akademi — Product Spec & Architecture

> Derived from `requirements and POD for the kp13 academy app.docx` (the founder's
> requirements note), compared against the current `Kp13Akademi` codebase, and
> turned into a structured spec + target architecture.
>
> Companion docs: [`VISION.md`](../VISION.md) (product philosophy & methodology),
> [`README.md`](../README.md) (repo tour).

---

## 1. Where the requirements doc and the code already meet

The requirements note is built on four AI-Human Edge concepts. The good news:
**the hard, defensible core (EPM + ELM + feedback loops) is already built.** The
gaps are mostly the "become a paid product" layer — accounts, payments, booking,
self-service onboarding, benchmarks, and the polished consumer shell.

| Requirement concept | Status | Where it lives in the code |
|---|---|---|
| **EPM** — propensity scores across technical / tactical / physical / mental | ✅ Built | `app/core/epm.py` — 16 dimensions, EMA update (α=0.3), confidence levels, gaps/strengths, age-weighted priorities; persisted in `epm_scores` / `epm_history` (`database.py`) |
| First-session measurement → baseline scores | ✅ Built | `app/core/onboarding.py` — sprint, turn-with/without-ball, juggling, taps, first touch, passing, finishing → mapped to EPM |
| **ELM** — language model giving guidance to players & parents | ✅ Built | `app/core/elm.py` + `app/core/agents/session_designer.py` — Claude `tool_use` for score extraction, daily plans, weekly parent summary, coach session prep |
| Feedback loops (session → score update → next recommendation) | ✅ Built | `epm.update_scores_from_observation` + `session_observations` + recommender; transfer tracking field exists |
| Training generator (individual sessions, busy schedules) | ✅ Built | `session_designer.design_week` → structured `WeeklySchedule` (3 sessions) via Pydantic contract; recency-aware exercise selection in `recommender.py` |
| La Masia + intense/focused (Persian Ball) methodology | ✅ Built | `skills/session-design/references/*`, `skills/weekly-progression/SKILL.md`, strong "natural Danish, no translated idioms" guardrails in `elm.py` |
| Progress = accumulated training hours | ✅ Built | `database.get_training_stats` (week / month / total + deltas), surfaced on player home (`web/main.py`, `home.html`) |
| Gamification | 🟡 Partial | Beatable `target` numbers per exercise + personal bests (`exercise_results`); no streaks, badges, XP, or levels yet |
| Mobile-friendly player experience | ✅ Built | FastAPI + Jinja + Tailwind, token URLs `/p/{token}`, pages: home, today, session, mastery, week, settings |
| Video explanations for core drills | 🟡 Partial | `video_url` fields + YouTube search fallback + Cloudinary upload (`cloudinary_upload.py`, `5_Videovæg.py`); no recorded core-drill library yet |

---

## 2. What the requirements ask for that does **not** exist yet

These are the true build gaps — the difference between "Kasper's coaching tool" and
"a product strangers can sign up and pay for."

| # | Gap | Requirement source | Current reality |
|---|---|---|---|
| G1 | **Self-service email sign-up & accounts** | "sign up with email", "create an account" | No accounts. Access is a coach-minted opaque token link (`access_tokens`) + a single coach password (`auth.py`). |
| G2 | **Subscription billing — 100 DKK/month** | "for 100 dkk a month be part of the platform" | No billing, no plans, no entitlement checks anywhere. |
| G3 | **Player self-onboarding (goals + basic info at signup)** | "write their goals and basic information when they create an account" | Players are created by the coach; goals/profile entered coach-side. No player-facing signup form. |
| G4 | **Book a session with a coach** | "get access to booking trainings with a coach" | A "book session" page is referenced but not implemented — no calendar, slots, or booking route. |
| G5 | **Adaptive session-length step-down** (45→25→12→3 min if not completed) | "if they don't do 45 min sessions, design 25… 12… single 2-3 min" | Durations vary, completions are tracked, but non-completion does **not** auto-regenerate shorter sessions. |
| G6 | **Benchmark engine** — hours & abilities vs pros at the same age | "compared to professional athletes at their age group", "what the next level looks like" | Educational rubric ladder exists (`mastery.html`, `review.py`), but no age-group/pro reference dataset or "you vs benchmark" comparison. |
| G7 | **"My Journey" journal** — unified timeline of videos, reflections, coach commentary | "a 'my journey' page like a journal" | Video wall exists but is not a unified player journal/timeline with reflections. |
| G8 | **Conversion landing page** (pain points + dream outcomes) | "very compelling… highlight the pain points and dream outcomes" | `welcome.html` is a thin entry page, not a marketing/conversion surface. |
| G9 | **Daily feedback cadence / reminders** (built into daily rhythm) | "feedback daily… feels natural and easy" | Daily plan generation exists, but no push/email reminders or daily check-in loop. |
| G10 | **Multi-tenancy / scale** | "scaleable from the start" | Single coach (Kasper), 2–5 players, no `academy_id`/`coach_id` scoping, no migration tool. |
| G11 | **Recorded core-drill video library** | "record a few videos… upload them… reused and combined" | Infra ready (Cloudinary), content + linking model not built. |

---

## 3. Structured specification

Organized as epics → features → acceptance criteria, with the build state. Use this
as the backlog spine.

### Epic A — Accounts, Access & Onboarding  *(mostly NEW)*

- **A1. Email sign-up & login** *(NEW — G1)*
  - Email + password and/or magic link; email verification.
  - On signup, create a `player` (or `parent`+`player`) account; replace token-link access with authenticated sessions. Keep token links as an optional "share with parent" convenience.
  - *Acceptance:* a new user can register, verify email, log in, and land on their own dashboard with no coach involvement.
- **A2. Player/parent self-onboarding** *(NEW — G3; extends existing `onboarding.py`)*
  - Wizard: basic info (name, birth year → age group, position, dominant foot, club), ambitions/goals (free text), preferred training days, weekly time budget.
  - Seed EPM at "Discovering" baseline; mark `confidence=low` until the first measured session.
  - *Acceptance:* profile + goals + preferred days persisted; player immediately gets a (baseline) generated week.
- **A3. First-session assessment capture** *(BUILT, expose to coach UI — `onboarding.py`)*
  - Coach enters measurements → `suggest_epm_from_measurements` → review/adjust → apply as baseline (already modeled in `player_assessments`).
  - *Acceptance:* measured baseline overwrites the cold-start baseline and flips confidence upward.
- **A4. Roles & entitlements** *(NEW)*
  - Roles: `player`, `parent`, `coach`, `admin`. Gate features by role + subscription status (see Epic B).

### Epic B — Subscription & Billing  *(NEW — G2)*

- **B1. Plans & checkout** — single plan, 100 DKK/month; Stripe (or Reepay for DK/MobilePay). Trial period optional.
- **B2. Entitlement enforcement** — middleware/dependency that checks active subscription before serving generators, plans, booking.
- **B3. Billing portal & lifecycle** — upgrade/cancel, dunning, webhooks → update `subscriptions` table; grace period on failed payment.
- **B4. Free vs paid surface** — landing + first dashboard glimpse free; generators/plans/booking behind paywall.
  - *Acceptance:* a user without an active subscription is cleanly blocked from paid features with an upgrade prompt; webhook-driven status changes take effect within seconds.

### Epic C — Training Intelligence  *(BUILT — harden & extend)*

- **C1. Weekly plan generator** *(BUILT — `session_designer.py`)* — keep the Pydantic `WeeklySchedule` contract as the UI binding.
- **C2. Daily plan / daily rhythm** *(BUILT generation; NEW cadence — G9)* — add reminders + a lightweight daily check-in that feeds completion back into EPM.
- **C3. Adaptive session length** *(NEW — G5)* — if a player misses N sessions at the current default length, the next generated week steps the duration down (45→25→12→3) and surfaces a "just start" micro-session. Drive off `session_completions` history.
- **C4. Score extraction from notes** *(BUILT — `elm.extract_scores_from_notes`)*.
- **C5. Exercise library & recency** *(BUILT — `generator/`, `recommender.py`)* — extend with `epm_dimensions` tags directly in YAML (VISION.md §"Mapping Exercises") to replace the hand-maintained `EXERCISE_CATEGORY_TO_EPM` map.

### Epic D — Progress, Benchmarks & Motivation

- **D1. Training-hours dashboard** *(BUILT — `get_training_stats`)*.
- **D2. EPM progress over time** *(BUILT — `epm_history`)* — radar + trend lines (coach side exists; bring a player-friendly view to mobile).
- **D3. Benchmark engine** *(NEW — G6)* — `benchmarks` table keyed by age group + dimension (+ hours-vs-pro reference). Render "you vs typical / next level"; **joy is the guardrail metric** — never push a benchmark while joy is dropping (rule already stated in VISION.md).
- **D4. Gamification** *(PARTIAL — extend)* — streaks (consecutive weeks hitting session target), volume milestones, dimension "level-ups" on rubric ladder. Keep it a thin layer over quality (the codebase explicitly treats the `target` number as secondary to session depth — preserve that).

### Epic E — Booking & Coaching Touchpoints  *(NEW — G4)*

- **E1. Coach availability** — coach defines bookable slots.
- **E2. Player booking** — player books an individual/academy session; confirmation + calendar entry; feeds `player_sessions`/`session_observations`.
- **E3. Post-session loop** — booked session → coach logs notes → EPM update → next week regenerates (closes C1↔C4 loop around a real booking).

### Epic F — "My Journey" & Media  *(PARTIAL — G7, G11)*

- **F1. Unified journey timeline** — merge player training videos, reflections, completed sessions, and coach commentary into one chronological page.
- **F2. Coach video feedback** *(BUILT base — `player_videos`)* — coach uploads match footage / 1-on-1 / advice (nutrition, mentality), to one player or many.
- **F3. Core-drill video library** *(NEW — G11)* — recorded canonical drill videos in Cloudinary, linked from `video_url` so generated sessions show real demonstrations instead of YouTube search links.

### Epic G — Marketing & Conversion  *(NEW — G8)*

- **G1. Landing page** — football-themed, pain points + dream outcomes for parent & kid personas (personas already written in `VISION.md`), pricing, CTA to sign up.
- **G2. SEO/share** — server-rendered (Jinja already supports this), OG tags, Danish-first copy.

### Epic H — Platform & Scale  *(NEW — G10)*

- **H1. Multi-tenancy** — add `coach_id`/`academy_id` scoping to player-owned tables; enforce in every query.
- **H2. Migrations** — adopt a migration tool (no more editing `_SCHEMA_STATEMENTS` by hand).
- **H3. Background jobs** — async workers for plan generation, weekly summaries, reminders, billing webhooks.
- **H4. Observability** — error tracking + structured logs + health checks (`/healthz` already exists).

---

## 4. Architecture & tech-stack recommendation

### 4.1 Guiding principle: evolve, don't rewrite

The current stack is a **strong MVP foundation** and already embodies the AI-Human
Edge thesis. The requirements ("best practices, modular, scaleable from the start,
optimal stack") are best served by **hardening and extending** it, not replacing it.
The biggest single risk is not the stack — it's the missing accounts/billing/tenancy
layer and the hand-rolled schema with no migrations.

### 4.2 Current stack (as built)

| Layer | Today |
|---|---|
| Player app | FastAPI + Jinja2 + Tailwind (CDN), mobile-first, token URLs |
| Coach console | Streamlit (`Min_Udvikling.py` + `pages/`) |
| Intelligence | Anthropic Claude (`claude-sonnet-4-6`) via `tool_use`, skill/markdown prompt files |
| Data | Postgres (Neon), psycopg3 + pool, hand-written schema in `database.py` (no migrations) |
| Media | Cloudinary |
| Deploy | `Procfile` → uvicorn (Railway/Render/Heroku-style) |
| Quality | pytest, ruff, mypy, GitHub Actions |

### 4.3 Recommended target architecture

```
┌───────────────────────────────────────────────────────────────┐
│  CLIENTS                                                        │
│  • Marketing landing (SSR, public)                              │
│  • Player/Parent PWA  (installable, web-push, offline-ish)      │
│  • Coach console (internal)                                     │
└───────────────┬───────────────────────────────────────────────┘
                │ HTTPS
┌───────────────▼───────────────────────────────────────────────┐
│  API / WEB  — FastAPI (single service, modular routers)         │
│  routers: auth · billing · onboarding · plans · booking ·       │
│           progress · journey · coach · webhooks                 │
│  ── Auth & sessions ──  ── Entitlement (subscription) guard ──  │
└───────┬───────────────────────────┬───────────────┬───────────┘
        │                           │               │
┌───────▼────────┐        ┌─────────▼─────────┐  ┌──▼───────────┐
│ CORE (domain)  │        │  ELM / Agents     │  │ Integrations │
│ epm · recommender│      │  session_designer │  │ Stripe/Reepay│
│ onboarding · benchmark│ │  elm · skills     │  │ Cloudinary   │
│ scheduling · gamify│    │  (Claude tool_use)│  │ Email/Push   │
└───────┬────────┘        └─────────┬─────────┘  └──┬───────────┘
        │                           │               │
┌───────▼───────────────────────────▼───────────────▼───────────┐
│ DATA: Postgres (Neon) + Alembic migrations                     │
│ players · accounts · subscriptions · epm_scores/history ·      │
│ observations · schedules · bookings · benchmarks · videos      │
│ Object storage: Cloudinary (video/images)                      │
└────────────────────────────────────────────────────────────────┘
        ▲
┌───────┴──────────────┐
│ BACKGROUND WORKERS    │  daily plans · reminders · weekly parent
│ (Arq/RQ + scheduler)  │  summaries · billing webhook processing
└───────────────────────┘
```

### 4.4 Specific stack choices

| Concern | Recommendation | Why |
|---|---|---|
| **Backend framework** | **Keep FastAPI** as the single product service; group features into routers/modules. | Async, typed, already in use, plays well with Claude SDK and Stripe webhooks. |
| **Coach console** | **Keep Streamlit short-term** as the internal coach tool; medium-term fold coach screens into the FastAPI app once multi-coach. | Streamlit is great for one operator, weak as multi-tenant SaaS UI. |
| **Frontend** | **PWA**: keep Jinja + Tailwind, add **HTMX/Alpine** for interactivity + a service worker for installability and **web push**. Go native (Capacitor wrapper) only if app-store presence is required. | Matches "web and mobile" without a second codebase; SSR keeps the landing page fast and SEO-friendly; fastest path given current skills. |
| **Auth** | **Managed**: Clerk or Supabase Auth (email + magic link + social, GDPR/EU regions). FastAPI-Users + JWT if you want zero vendor lock-in. | Don't hand-roll auth for a paid product; email verification, password reset, sessions come for free. |
| **Payments** | **Stripe Billing**; enable **MobilePay via Stripe** for DK. Consider **Reepay/Quickpay** if you want Danish-first invoicing/MobilePay subscriptions. | 100 DKK/month recurring, dunning, customer portal, webhooks. MobilePay matters for a Danish audience. |
| **Database** | **Stay on Postgres/Neon.** Adopt **Alembic** for migrations (introduce SQLAlchemy Core models, or keep psycopg + use `yoyo`/`sqlbag`). | Hand-editing `_SCHEMA_STATEMENTS` won't survive multi-env/multi-tenant. Migrations are the #1 platform-readiness fix. |
| **Background jobs** | **Arq** (async, Redis) or **RQ**; **APScheduler** for cron-like (daily plans, weekly summaries, reminders). | Claude calls + emails + webhooks must move off the request path. |
| **Notifications** | **Email** via Resend/Postmark; **Web Push** via the PWA. SMS/MobilePay-push later. | Powers the "daily rhythm" feedback loop (G9) and weekly parent summary delivery. |
| **AI** | **Keep Anthropic Claude + `tool_use`**. Centralize prompts in the existing `skills/` files. Add **prompt caching** (player history → recent sessions → request) as VISION.md describes, and **streaming** for plans. Cost-guard with per-account rate limits. | Already the core moat; structured `tool_use` → Pydantic contracts is exactly right. |
| **Multi-tenancy** | Add `coach_id`/`academy_id` to player-scoped tables; enforce in a query layer; optionally Postgres RLS later. | Required before onboarding coaches beyond Kasper. |
| **Observability** | **Sentry** + structured logging; keep `/healthz`. | Paid users need reliability signals. |
| **Hosting** | App on **Railway/Render/Fly.io**, DB on **Neon**, media on **Cloudinary**, Redis on the same platform. EU region for GDPR. | Matches current Procfile deploy; minimal ops. |
| **Compliance** | GDPR + processing **children's data** (U7–U15): parental consent flow, data minimization, EU data residency, clear retention. | Non-negotiable for a Danish youth product. |

### 4.5 Danish-language quality (already a strength — keep it)

`elm.py` and the `weekly-progression` skill encode strict "write natural Danish, never
translated English idioms" rules. This directly answers the doc's open question about
translation. **Keep generation Danish-native** and reserve English for football terms
that have no natural Danish equivalent — exactly the policy already in the prompts.

---

## 5. Suggested delivery sequence

A pragmatic order that turns the existing coaching tool into a sellable product while
keeping it usable throughout:

1. **Platform readiness** (H2 migrations, H1 tenancy scoping, H4 observability) — do this *before* piling on features.
2. **Accounts & onboarding** (Epic A) — email signup, self-onboarding wizard, expose assessment capture.
3. **Billing** (Epic B) — Stripe/Reepay + entitlement guard. *Now it can take money.*
4. **Conversion shell** (Epic G landing + F1 journey + player-side progress D2) — the surface a buyer actually evaluates.
5. **Engagement loops** (C2/C3 daily cadence + adaptive length, D4 gamification, G9 reminders).
6. **Booking** (Epic E) and **Benchmarks** (D3) — higher-value, higher-effort; sequence by demand.
7. **Core-drill video library** (F3) — content effort; parallelizable anytime.

---

*Generated by comparing the requirements doc against the codebase on 2026-06-06.*
