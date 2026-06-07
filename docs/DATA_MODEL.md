# KP13 Akademi — Data Model & Migrations

Companion to [`SPEC_AND_ARCHITECTURE.md`](SPEC_AND_ARCHITECTURE.md). This covers the
**platform-readiness foundation** (delivery step 1): versioned migrations plus the
accounts / subscription / multi-tenancy schema that everything monetization-related
depends on.

---

## 1. Migration tooling — what was added and why

The repo previously evolved its schema by hand-editing `core.database._SCHEMA_STATEMENTS`
(idempotent `CREATE TABLE IF NOT EXISTS` + additive `ALTER … IF NOT EXISTS`). That works
for one developer against one database, but it has no record of *what has been applied
where*, so it can't safely coordinate changes across local / staging / production.

**Decision: a lightweight in-house runner, not Alembic.** Alembic's main value is
autogenerating migrations from SQLAlchemy ORM models — and this project has no ORM; it
uses raw `psycopg`. Adopting Alembic would mean either introducing SQLAlchemy models
solely to satisfy it, or hand-writing migrations anyway (Alembic's manual mode) while
carrying a heavy dependency. Instead we keep the project's existing idiom — ordered lists
of single SQL statements — and add the one missing piece: an applied-version ledger.

New files:

| File | Role |
|---|---|
| `app/core/migrate.py` | The runner. Applies pending migrations in order, records them in `schema_migrations`, each in its own transaction. CLI: `--status` to inspect. |
| `app/core/migrations/__init__.py` | Package + contract docs for migration modules. |
| `app/core/migrations/m0001_accounts_billing_tenancy.py` | First migration (this document's schema). |

### How to run

From the `app/` directory (same working dir as the uvicorn entrypoint), against a database
with `DATABASE_URL` set:

```bash
python -m core.migrate --status   # show applied vs pending (applies nothing)
python -m core.migrate            # apply pending migrations
```

> ⚠️ **Not yet run.** These files are committed but no migration has been executed against
> any database — that needs your `DATABASE_URL` and a working Python env (the repo `.venv`
> currently points at a missing 3.14 base; recreate it before running). The runner has been
> validated for discovery and statement integrity only.

### Relationship to `init_db()`

`database.init_db()` still creates the **baseline** tables (idempotent). Migrations layer
**versioned changes** on top. Order: `init_db()` first (app startup already does this),
then `run_migrations()`. To wire migrations into startup, add one line to
`app/web/main.py`'s `startup()`:

```python
from core.migrate import run_migrations
@app.on_event("startup")
def startup():
    db.init_db()
    run_migrations()   # apply any pending schema changes on boot
```

This is intentionally **not** wired in yet — run it manually against each environment first
so a failing migration can't take down app boot. Wire it in once you trust the flow.

---

## 2. Schema delivered by migration 0001

Additive and backfilled — **no existing column or row is altered destructively.**

### New tables

```
academies                      accounts                         coaches
─────────                      ────────                         ───────
id          PK                 id            PK (uuid)          id          PK
name                           email         UNIQUE             account_id  → accounts
created_at                     role          player|parent|     academy_id  → academies
                                             coach|admin         name
                               auth_provider password|clerk|…   created_at
                               external_id   (provider user id)
                               password_hash (password auth)
                               email_verified
                               academy_id    → academies
                               created_at

subscriptions
─────────────
id                       PK (uuid)
account_id               → accounts
provider                 stripe|reepay
provider_customer_id
provider_subscription_id (unique when present)
status                   trialing|active|past_due|canceled|incomplete
plan                     kp13_monthly
price_dkk                100
current_period_end
cancel_at_period_end
created_at / updated_at
```

### Changed table: `players`

Three nullable, backfilled columns — existing token-link access is untouched:

- `account_id → accounts` — which login owns this player (a parent account can own several players).
- `coach_id → coaches` — the responsible coach (tenancy).
- `academy_id → academies` — the academy (tenancy).

### Backfill

Creates a default `kp13` academy and `kasper` coach, then attaches every existing player to
them. The app keeps working in single-tenant mode immediately; tenancy columns are populated
and ready for enforcement.

### Two deliberately provider-agnostic choices

- **Auth** — `accounts.auth_provider` + `external_id` + nullable `password_hash` means you can
  start with a managed provider (Clerk/Supabase — *recommended*, see SPEC §4.4) and store its
  user id in `external_id`, or self-host password auth, **without a schema change**.
- **Billing** — `subscriptions.provider` (`stripe` | `reepay`) + the generic
  `provider_customer_id` / `provider_subscription_id` lets you choose Stripe (with MobilePay)
  or a Danish provider later without reshaping the table.

---

## 3. Tenancy enforcement plan (the code side)

Schema scoping (columns) is in place; **query-time enforcement is the follow-up**. Today
`database.py` functions take a `player_id` and trust it. The path to safe multi-tenancy:

1. **Auth context** — once accounts exist, every authenticated request resolves to an
   `account_id` (+ derived `coach_id`/`academy_id`). Add a FastAPI dependency that yields this
   context.
2. **Authorization helper** — a single `assert_can_access(player_id, ctx)` checked at the top of
   each player-scoped route (verify `players.account_id == ctx.account_id` for player/parent
   roles, or `players.coach_id == ctx.coach_id` for coaches).
3. **Scoped queries for coach lists** — coach-facing reads (`get_players`) gain a
   `coach_id`/`academy_id` filter so a coach only ever sees their own players.
4. **Optional hardening later** — Postgres Row-Level Security keyed on a session GUC, as a
   defense-in-depth backstop once there are many tenants.

Do this in the same change that introduces auth (SPEC Epic A), so enforcement and the identity
it depends on land together.

---

## 4. Planned follow-up migrations

Sequenced behind 0001 (foundation) → auth/billing wiring → these:

- **0002 — booking** (SPEC Epic E): `coach_availability` (coach_id, weekday/date, start, end,
  capacity) and `bookings` (player_id, coach_id, slot start/end, status). Completed bookings feed
  the existing `session_observations` / `player_sessions` loop.
- **0003 — benchmarks** (SPEC Epic D3): `benchmarks` (age_group, dimension, level, expected_score,
  source) and an hours-vs-pro reference table, to power "you vs typical / next level." Remember the
  joy-guardrail rule from VISION.md.
- **0004 — exercise ↔ EPM tags**: promote the hand-maintained `EXERCISE_CATEGORY_TO_EPM` map in
  `epm.py` into `epm_dimensions` fields on the exercise YAML (VISION.md §"Mapping Exercises"), and
  a sync/validation step.

---

*Added 2026-06-06 as delivery step 1 (platform readiness) from SPEC_AND_ARCHITECTURE.md.*
