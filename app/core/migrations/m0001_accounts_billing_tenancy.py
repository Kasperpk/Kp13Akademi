"""0001 — accounts, billing and multi-tenancy foundation.

Turns the single-coach token-link tool into something that can have real
self-service accounts, paid subscriptions, and more than one coach/academy,
WITHOUT disturbing existing data:

  * New tables: ``academies``, ``accounts``, ``coaches``, ``subscriptions``.
  * Additive columns on ``players``: ``account_id``, ``coach_id``, ``academy_id``
    (all nullable — existing rows keep working).
  * Backfill: a default ``kp13`` academy + ``kasper`` coach, and every existing
    player is attached to them. The current token-link access path is untouched.

Frozen snapshot — do not edit. Add a new migration for further changes.
"""

from __future__ import annotations

# Mirror the TEXT-ISO timestamp default used by core.database so callers that
# slice created_at as an ISO string keep working. Inlined (not imported) so this
# migration stays an immutable snapshot independent of app constants.
_ISO_DEFAULT = "to_char(now() at time zone 'utc', 'YYYY-MM-DD\"T\"HH24:MI:SS')"

VERSION = "0001"
DESCRIPTION = "accounts, billing and multi-tenancy foundation"

STATEMENTS: list[str] = [
    # ---- tenancy roots ------------------------------------------------------
    f"""CREATE TABLE IF NOT EXISTS academies (
        id         TEXT PRIMARY KEY,
        name       TEXT NOT NULL,
        created_at TEXT DEFAULT ({_ISO_DEFAULT})
    )""",

    # ---- accounts (auth-provider agnostic) ----------------------------------
    # auth_provider = 'password' | 'clerk' | 'supabase' | 'google' | ...
    # external_id is the provider's user id when using managed auth; password_hash
    # is only populated for the 'password' provider. This lets us start with a
    # managed provider (recommended) or self-hosted auth without a schema change.
    f"""CREATE TABLE IF NOT EXISTS accounts (
        id             TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
        email          TEXT NOT NULL UNIQUE,
        role           TEXT NOT NULL DEFAULT 'player',
        auth_provider  TEXT NOT NULL DEFAULT 'password',
        external_id    TEXT,
        password_hash  TEXT,
        email_verified INTEGER NOT NULL DEFAULT 0,
        academy_id     TEXT REFERENCES academies(id),
        created_at     TEXT DEFAULT ({_ISO_DEFAULT})
    )""",
    """CREATE UNIQUE INDEX IF NOT EXISTS idx_accounts_provider_external
       ON accounts(auth_provider, external_id)
       WHERE external_id IS NOT NULL""",

    # ---- coaches ------------------------------------------------------------
    f"""CREATE TABLE IF NOT EXISTS coaches (
        id         TEXT PRIMARY KEY,
        account_id TEXT REFERENCES accounts(id),
        academy_id TEXT REFERENCES academies(id),
        name       TEXT NOT NULL,
        created_at TEXT DEFAULT ({_ISO_DEFAULT})
    )""",

    # ---- player ownership + tenancy scoping ---------------------------------
    "ALTER TABLE players ADD COLUMN IF NOT EXISTS account_id TEXT REFERENCES accounts(id)",
    "ALTER TABLE players ADD COLUMN IF NOT EXISTS coach_id   TEXT REFERENCES coaches(id)",
    "ALTER TABLE players ADD COLUMN IF NOT EXISTS academy_id TEXT REFERENCES academies(id)",
    "CREATE INDEX IF NOT EXISTS idx_players_account ON players(account_id)",
    "CREATE INDEX IF NOT EXISTS idx_players_coach   ON players(coach_id)",
    "CREATE INDEX IF NOT EXISTS idx_players_academy ON players(academy_id)",

    # ---- subscriptions (provider agnostic: stripe | reepay) -----------------
    # status mirrors Stripe's lifecycle: trialing|active|past_due|canceled|incomplete
    f"""CREATE TABLE IF NOT EXISTS subscriptions (
        id                       TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
        account_id               TEXT NOT NULL REFERENCES accounts(id),
        provider                 TEXT NOT NULL DEFAULT 'stripe',
        provider_customer_id     TEXT,
        provider_subscription_id TEXT,
        status                   TEXT NOT NULL DEFAULT 'incomplete',
        plan                     TEXT NOT NULL DEFAULT 'kp13_monthly',
        price_dkk                INTEGER NOT NULL DEFAULT 100,
        current_period_end       TEXT,
        cancel_at_period_end     INTEGER NOT NULL DEFAULT 0,
        created_at               TEXT DEFAULT ({_ISO_DEFAULT}),
        updated_at               TEXT
    )""",
    "CREATE INDEX IF NOT EXISTS idx_subscriptions_account ON subscriptions(account_id)",
    """CREATE UNIQUE INDEX IF NOT EXISTS idx_subscriptions_provider_sub
       ON subscriptions(provider_subscription_id)
       WHERE provider_subscription_id IS NOT NULL""",

    # ---- backfill single-tenant defaults (safe, idempotent) -----------------
    "INSERT INTO academies (id, name) VALUES ('kp13', 'KP13 Akademi') ON CONFLICT (id) DO NOTHING",
    "INSERT INTO coaches (id, name, academy_id) VALUES ('kasper', 'Kasper', 'kp13') ON CONFLICT (id) DO NOTHING",
    "UPDATE players SET academy_id = 'kp13'   WHERE academy_id IS NULL",
    "UPDATE players SET coach_id   = 'kasper' WHERE coach_id   IS NULL",
]
