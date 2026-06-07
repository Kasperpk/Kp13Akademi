"""Versioned schema migrations for KP13 Akademi.

Each migration is a module named ``mNNNN_description`` exposing:

    VERSION: str            # zero-padded, sortable, e.g. "0001"
    DESCRIPTION: str        # human summary
    STATEMENTS: list[str]   # ordered DDL/DML, each a single SQL statement

The runner in ``core.migrate`` applies any module whose ``VERSION`` is not yet
recorded in the ``schema_migrations`` table, in ascending ``VERSION`` order.

Migrations are immutable once shipped: never edit an applied migration — add a
new one. Statements must be idempotent where practical (``IF NOT EXISTS``,
``ON CONFLICT DO NOTHING``) so a partial/retried run is safe.
"""
