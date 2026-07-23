"""
database.py

PostgreSQL (Supabase) database layer for CommunityFinanceOS.

Performance optimisations vs first version:
  - init_db() cached with @st.cache_resource so it only runs ONCE per
    Streamlit worker process, not on every page load.
  - get_db_connection() adds connect_timeout=10 to avoid indefinite hangs.
  - _col_exists / _table_exists use EXISTS queries (faster than fetching rows).
  - Connection uses the Supabase transaction pooler (port 6543) which is
    IPv4-compatible and has lower latency than direct connections from
    Streamlit Cloud.
"""

import os
import streamlit as st
import psycopg2
from psycopg2.extras import RealDictCursor


def _get_url():
    try:
        url = st.secrets.get("DATABASE_URL")
        if url:
            return url
    except Exception:
        pass
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    raise RuntimeError(
        "DATABASE_URL not found. "
        "Add it to Streamlit secrets: Settings → Secrets → DATABASE_URL"
    )


def get_db_connection():
    """
    Opens a psycopg2 connection with RealDictCursor (row['col'] access)
    and a 10-second connect timeout so slow cold-starts don't hang forever.
    """
    url = _get_url()
    conn = psycopg2.connect(
        url,
        cursor_factory=RealDictCursor,
        connect_timeout=10,
        keepalives=1,
        keepalives_idle=30,
        keepalives_interval=10,
        keepalives_count=5,
    )
    conn.autocommit = False
    return conn


def _col_exists(cur, table, column):
    cur.execute("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name   = %s
              AND column_name  = %s
        )
    """, (table, column))
    return cur.fetchone()['exists']


def _table_exists(cur, table):
    cur.execute("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name   = %s
        )
    """, (table,))
    return cur.fetchone()['exists']


@st.cache_resource
def init_db():
    """
    Creates all tables and runs safe column migrations.
    Decorated with @st.cache_resource so it runs ONCE per worker process —
    not on every page interaction. This is the main performance fix.
    """
    conn = get_db_connection()
    cur  = conn.cursor()

    # ── sacco_profile ────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sacco_profile (
            id                            SERIAL PRIMARY KEY,
            sacco_name                    TEXT,
            parish                        TEXT,
            sub_county                    TEXT,
            constituency                  TEXT,
            district                      TEXT,
            date_of_formation             TEXT,
            ursb_registration_number      TEXT,
            permanent_registration_status TEXT DEFAULT 'No',
            bank_account_number           TEXT,
            bank_name                     TEXT,
            total_registered_members      INTEGER,
            number_of_enterprise_groups   INTEGER,
            emyooga_category              TEXT,
            apex_sacco_name               TEXT,
            parish_associations           TEXT,
            number_of_parish_associations INTEGER,
            date_of_last_agm              TEXT,
            date_of_last_audit            TEXT,
            auditor_name                  TEXT,
            audit_report_filed            TEXT DEFAULT 'No',
            annual_subscription_paid      TEXT DEFAULT 'No',
            share_capital_per_member      REAL,
            membership_joining_fee        REAL
        )
    """)

    # ── users ────────────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username      TEXT PRIMARY KEY,
            password_hash TEXT,
            salt          TEXT,
            role          TEXT,
            sacco_id      INTEGER,
            language      TEXT DEFAULT 'en'
        )
    """)
    for col, defn in [('sacco_id', 'INTEGER'), ('language', "TEXT DEFAULT 'en'")]:
        if not _col_exists(cur, 'users', col):
            cur.execute(f"ALTER TABLE users ADD COLUMN {col} {defn}")

    # ── customers ────────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            id          SERIAL PRIMARY KEY,
            name        TEXT NOT NULL,
            phone       TEXT NOT NULL,
            national_id TEXT,
            created_at  TEXT,
            member_type TEXT DEFAULT 'Member',
            occupation  TEXT
        )
    """)
    for col, defn in [
        ('member_type',            "TEXT DEFAULT 'Member'"),
        ('occupation',             'TEXT'),
        ('location',               'TEXT'),
        ('photo',                  'BYTEA'),
        ('gender',                 'TEXT'),
        ('date_of_birth',          'TEXT'),
        ('pwd_status',             "TEXT DEFAULT 'No'"),
        ('subsistence_status',     'TEXT'),
        ('village',                'TEXT'),
        ('parish',                 'TEXT'),
        ('sacco_id',               'INTEGER DEFAULT 1'),
        ('nssf_registered',        'INTEGER DEFAULT 0'),
        ('nssf_number',            'TEXT'),
        ('nssf_contribution_rate', 'REAL DEFAULT 5.0'),
    ]:
        if not _col_exists(cur, 'customers', col):
            cur.execute(f"ALTER TABLE customers ADD COLUMN {col} {defn}")

    # ── nssf_contributions ───────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS nssf_contributions (
            id                     SERIAL PRIMARY KEY,
            customer_id            INTEGER NOT NULL REFERENCES customers(id),
            sacco_id               INTEGER NOT NULL,
            savings_transaction_id INTEGER,
            gross_deposit          REAL NOT NULL,
            nssf_amount            REAL NOT NULL,
            net_to_sacco           REAL NOT NULL,
            contribution_rate      REAL NOT NULL,
            period                 TEXT NOT NULL,
            remitted               INTEGER DEFAULT 0,
            created_at             TEXT DEFAULT TO_CHAR(NOW(), 'YYYY-MM-DD HH24:MI:SS')
        )
    """)

    # ── gold_points_ledger ───────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS gold_points_ledger (
            id          SERIAL PRIMARY KEY,
            customer_id INTEGER NOT NULL REFERENCES customers(id),
            sacco_id    INTEGER NOT NULL,
            points      INTEGER NOT NULL,
            reason      TEXT NOT NULL,
            created_at  TEXT DEFAULT TO_CHAR(NOW(), 'YYYY-MM-DD HH24:MI:SS')
        )
    """)

    # ── member_pins ──────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS member_pins (
            id          SERIAL PRIMARY KEY,
            customer_id INTEGER NOT NULL UNIQUE REFERENCES customers(id),
            pin_hash    TEXT NOT NULL,
            pin_salt    TEXT NOT NULL,
            first_login INTEGER DEFAULT 1,
            last_login  TEXT,
            created_at  TEXT DEFAULT TO_CHAR(NOW(), 'YYYY-MM-DD HH24:MI:SS')
        )
    """)

    # ── loans ────────────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS loans (
            id             SERIAL PRIMARY KEY,
            customer_id    INTEGER NOT NULL REFERENCES customers(id),
            principal      REAL NOT NULL,
            interest_rate  REAL NOT NULL,
            term_months    INTEGER NOT NULL,
            total_due      REAL NOT NULL,
            balance        REAL NOT NULL,
            status         TEXT NOT NULL,
            disbursed_date TEXT
        )
    """)
    if not _col_exists(cur, 'loans', 'sacco_id'):
        cur.execute("ALTER TABLE loans ADD COLUMN sacco_id INTEGER DEFAULT 1")

    # ── loan_schedule ────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS loan_schedule (
            id             SERIAL PRIMARY KEY,
            loan_id        INTEGER NOT NULL REFERENCES loans(id),
            installment_no INTEGER,
            due_date       TEXT,
            due_amount     REAL,
            paid_amount    REAL DEFAULT 0,
            status         TEXT DEFAULT 'Pending'
        )
    """)

    # ── repayments ───────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS repayments (
            id        SERIAL PRIMARY KEY,
            loan_id   INTEGER NOT NULL REFERENCES loans(id),
            amount    REAL NOT NULL,
            method    TEXT,
            reference TEXT,
            date      TEXT
        )
    """)

    # ── guarantors ───────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS guarantors (
            id           SERIAL PRIMARY KEY,
            loan_id      INTEGER NOT NULL REFERENCES loans(id),
            name         TEXT NOT NULL,
            phone        TEXT,
            national_id  TEXT,
            relationship TEXT
        )
    """)

    # ── collateral ───────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS collateral (
            id              SERIAL PRIMARY KEY,
            loan_id         INTEGER NOT NULL REFERENCES loans(id),
            description     TEXT NOT NULL,
            estimated_value REAL,
            status          TEXT DEFAULT 'Held'
        )
    """)

    # ── savings_accounts ─────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS savings_accounts (
            id          SERIAL PRIMARY KEY,
            customer_id INTEGER NOT NULL REFERENCES customers(id),
            balance     REAL DEFAULT 0,
            opened_date TEXT
        )
    """)
    if not _col_exists(cur, 'savings_accounts', 'sacco_id'):
        cur.execute("ALTER TABLE savings_accounts ADD COLUMN sacco_id INTEGER DEFAULT 1")

    # ── savings_transactions ─────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS savings_transactions (
            id         SERIAL PRIMARY KEY,
            account_id INTEGER NOT NULL REFERENCES savings_accounts(id),
            type       TEXT,
            amount     REAL,
            date       TEXT
        )
    """)
    if not _col_exists(cur, 'savings_transactions', 'channel'):
        cur.execute("ALTER TABLE savings_transactions ADD COLUMN channel TEXT")

    # ── ledger ───────────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ledger (
            id          SERIAL PRIMARY KEY,
            date        TEXT,
            account     TEXT,
            debit       REAL DEFAULT 0,
            credit      REAL DEFAULT 0,
            description TEXT,
            reference   TEXT
        )
    """)
    if not _col_exists(cur, 'ledger', 'sacco_id'):
        cur.execute("ALTER TABLE ledger ADD COLUMN sacco_id INTEGER DEFAULT 1")

    # ── messages_log ─────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages_log (
            id          SERIAL PRIMARY KEY,
            customer_id INTEGER,
            message     TEXT,
            sent_at     TEXT
        )
    """)

    conn.commit()

    # Safety net — ensure legacy sacco_id=1 has a profile row
    cur.execute("SELECT 1 FROM customers WHERE sacco_id = 1 LIMIT 1")
    if cur.fetchone():
        cur.execute("SELECT 1 FROM sacco_profile WHERE id = 1")
        if not cur.fetchone():
            cur.execute(
                "INSERT INTO sacco_profile (id, sacco_name) VALUES (1, 'Unassigned (Legacy Data)')"
            )
            conn.commit()

    cur.close()
    conn.close()
