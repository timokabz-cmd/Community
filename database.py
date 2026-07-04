import sqlite3

DB_PATH = 'finance.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()

    # ---------------------------------------------------------------
    # sacco_profile: migrate from the old single-tenant singleton
    # (id fixed at 1 via CHECK constraint) to a proper multi-row table,
    # one row per SACCO. SQLite can't ALTER a CHECK constraint away,
    # so if we detect the old shape we rename, recreate, and copy data.
    # ---------------------------------------------------------------
    existing_tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    if 'sacco_profile' in existing_tables:
        table_sql_row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='sacco_profile'"
        ).fetchone()
        table_sql = table_sql_row[0] if table_sql_row else ''
        if table_sql and 'CHECK' in table_sql:
            conn.execute("ALTER TABLE sacco_profile RENAME TO sacco_profile_legacy_singleton")

    conn.execute('''CREATE TABLE IF NOT EXISTS sacco_profile (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sacco_name TEXT,
        parish TEXT,
        sub_county TEXT,
        constituency TEXT,
        district TEXT,
        date_of_formation TEXT,
        ursb_registration_number TEXT,
        permanent_registration_status TEXT DEFAULT 'No',
        bank_account_number TEXT,
        bank_name TEXT,
        total_registered_members INTEGER,
        number_of_enterprise_groups INTEGER,
        emyooga_category TEXT,
        apex_sacco_name TEXT,
        parish_associations TEXT,
        number_of_parish_associations INTEGER,
        date_of_last_agm TEXT,
        date_of_last_audit TEXT,
        auditor_name TEXT,
        audit_report_filed TEXT DEFAULT 'No',
        annual_subscription_paid TEXT DEFAULT 'No',
        share_capital_per_member REAL,
        membership_joining_fee REAL
    )''')

    if 'sacco_profile_legacy_singleton' in [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]:
        cols = [row[1] for row in conn.execute("PRAGMA table_info(sacco_profile_legacy_singleton)").fetchall()]
        col_list = ", ".join(cols)
        conn.execute(f"INSERT INTO sacco_profile ({col_list}) SELECT {col_list} FROM sacco_profile_legacy_singleton")
        conn.execute("DROP TABLE sacco_profile_legacy_singleton")

    # ---------------------------------------------------------------
    # users: each user is scoped to one SACCO via sacco_id, EXCEPT
    # role='admin' (the platform operator / super-admin), whose
    # sacco_id is NULL and who can switch between every SACCO.
    # ---------------------------------------------------------------
    conn.execute('''CREATE TABLE IF NOT EXISTS users ( username TEXT PRIMARY KEY, password_hash TEXT, salt TEXT, role TEXT, sacco_id INTEGER )''')
    existing_user_cols = [row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()]
    if 'sacco_id' not in existing_user_cols:
        conn.execute("ALTER TABLE users ADD COLUMN sacco_id INTEGER")

    conn.execute('''CREATE TABLE IF NOT EXISTS customers ( id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, phone TEXT NOT NULL, national_id TEXT, created_at TEXT, member_type TEXT DEFAULT 'Member', occupation TEXT )''')

    # Migration: add new columns to an existing customers table if upgrading
    # from an older version of the schema (SQLite has no "ADD COLUMN IF NOT EXISTS").
    existing_cols = [row[1] for row in conn.execute("PRAGMA table_info(customers)").fetchall()]
    if 'member_type' not in existing_cols:
        conn.execute("ALTER TABLE customers ADD COLUMN member_type TEXT DEFAULT 'Member'")
    if 'occupation' not in existing_cols:
        conn.execute("ALTER TABLE customers ADD COLUMN occupation TEXT")
    if 'location' not in existing_cols:
        conn.execute("ALTER TABLE customers ADD COLUMN location TEXT")
    if 'photo' not in existing_cols:
        conn.execute("ALTER TABLE customers ADD COLUMN photo BLOB")
    if 'gender' not in existing_cols:
        conn.execute("ALTER TABLE customers ADD COLUMN gender TEXT")
    if 'date_of_birth' not in existing_cols:
        conn.execute("ALTER TABLE customers ADD COLUMN date_of_birth TEXT")
    if 'pwd_status' not in existing_cols:
        conn.execute("ALTER TABLE customers ADD COLUMN pwd_status TEXT DEFAULT 'No'")
    if 'subsistence_status' not in existing_cols:
        conn.execute("ALTER TABLE customers ADD COLUMN subsistence_status TEXT")
    if 'village' not in existing_cols:
        conn.execute("ALTER TABLE customers ADD COLUMN village TEXT")
    if 'parish' not in existing_cols:
        conn.execute("ALTER TABLE customers ADD COLUMN parish TEXT")
    if 'sacco_id' not in existing_cols:
        conn.execute("ALTER TABLE customers ADD COLUMN sacco_id INTEGER DEFAULT 1")

    conn.execute('''CREATE TABLE IF NOT EXISTS loans ( id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER NOT NULL, principal REAL NOT NULL, interest_rate REAL NOT NULL, term_months INTEGER NOT NULL, total_due REAL NOT NULL, balance REAL NOT NULL, status TEXT NOT NULL, disbursed_date TEXT, FOREIGN KEY(customer_id) REFERENCES customers(id) )''')
    existing_loan_cols = [row[1] for row in conn.execute("PRAGMA table_info(loans)").fetchall()]
    if 'sacco_id' not in existing_loan_cols:
        conn.execute("ALTER TABLE loans ADD COLUMN sacco_id INTEGER DEFAULT 1")

    conn.execute('''CREATE TABLE IF NOT EXISTS loan_schedule ( id INTEGER PRIMARY KEY AUTOINCREMENT, loan_id INTEGER NOT NULL, installment_no INTEGER, due_date TEXT, due_amount REAL, paid_amount REAL DEFAULT 0, status TEXT DEFAULT 'Pending', FOREIGN KEY(loan_id) REFERENCES loans(id) )''')

    conn.execute('''CREATE TABLE IF NOT EXISTS repayments ( id INTEGER PRIMARY KEY AUTOINCREMENT, loan_id INTEGER NOT NULL, amount REAL NOT NULL, method TEXT, reference TEXT, date TEXT, FOREIGN KEY(loan_id) REFERENCES loans(id) )''')

    conn.execute('''CREATE TABLE IF NOT EXISTS guarantors ( id INTEGER PRIMARY KEY AUTOINCREMENT, loan_id INTEGER NOT NULL, name TEXT NOT NULL, phone TEXT, national_id TEXT, relationship TEXT, FOREIGN KEY(loan_id) REFERENCES loans(id) )''')

    conn.execute('''CREATE TABLE IF NOT EXISTS collateral ( id INTEGER PRIMARY KEY AUTOINCREMENT, loan_id INTEGER NOT NULL, description TEXT NOT NULL, estimated_value REAL, status TEXT DEFAULT 'Held', FOREIGN KEY(loan_id) REFERENCES loans(id) )''')

    conn.execute('''CREATE TABLE IF NOT EXISTS savings_accounts ( id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER NOT NULL, balance REAL DEFAULT 0, opened_date TEXT, FOREIGN KEY(customer_id) REFERENCES customers(id) )''')
    existing_sa_cols = [row[1] for row in conn.execute("PRAGMA table_info(savings_accounts)").fetchall()]
    if 'sacco_id' not in existing_sa_cols:
        conn.execute("ALTER TABLE savings_accounts ADD COLUMN sacco_id INTEGER DEFAULT 1")

    conn.execute('''CREATE TABLE IF NOT EXISTS savings_transactions ( id INTEGER PRIMARY KEY AUTOINCREMENT, account_id INTEGER NOT NULL, type TEXT, amount REAL, date TEXT, FOREIGN KEY(account_id) REFERENCES savings_accounts(id) )''')

    # Migration: add channel (mode of payment) to an existing savings_transactions table
    existing_txn_cols = [row[1] for row in conn.execute("PRAGMA table_info(savings_transactions)").fetchall()]
    if 'channel' not in existing_txn_cols:
        conn.execute("ALTER TABLE savings_transactions ADD COLUMN channel TEXT")

    conn.execute('''CREATE TABLE IF NOT EXISTS ledger ( id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, account TEXT, debit REAL DEFAULT 0, credit REAL DEFAULT 0, description TEXT, reference TEXT )''')
    existing_ledger_cols = [row[1] for row in conn.execute("PRAGMA table_info(ledger)").fetchall()]
    if 'sacco_id' not in existing_ledger_cols:
        conn.execute("ALTER TABLE ledger ADD COLUMN sacco_id INTEGER DEFAULT 1")

    conn.execute('''CREATE TABLE IF NOT EXISTS messages_log ( id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER, message TEXT, sent_at TEXT )''')

    conn.commit()

    # ---------------------------------------------------------------
    # Safety net: any pre-existing data that just got backfilled to
    # sacco_id=1 needs an actual SACCO row to point to, or it becomes
    # orphaned (invisible once the switcher is in place).
    # ---------------------------------------------------------------
    sacco_id_1_referenced = any([
        conn.execute("SELECT 1 FROM customers WHERE sacco_id = 1 LIMIT 1").fetchone(),
        conn.execute("SELECT 1 FROM loans WHERE sacco_id = 1 LIMIT 1").fetchone(),
        conn.execute("SELECT 1 FROM savings_accounts WHERE sacco_id = 1 LIMIT 1").fetchone(),
    ])
    sacco_1_exists = conn.execute("SELECT 1 FROM sacco_profile WHERE id = 1").fetchone()
    if sacco_id_1_referenced and not sacco_1_exists:
        conn.execute(
            "INSERT INTO sacco_profile (id, sacco_name) VALUES (1, 'Unassigned (Legacy Data)')"
        )
        conn.commit()

    conn.close()
