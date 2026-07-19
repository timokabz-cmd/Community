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
    # users
    # ---------------------------------------------------------------
    conn.execute('''CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password_hash TEXT,
        salt TEXT,
        role TEXT,
        sacco_id INTEGER,
        language TEXT DEFAULT 'en'
    )''')
    existing_user_cols = [row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()]
    if 'sacco_id'  not in existing_user_cols:
        conn.execute("ALTER TABLE users ADD COLUMN sacco_id INTEGER")
    if 'language'  not in existing_user_cols:
        conn.execute("ALTER TABLE users ADD COLUMN language TEXT DEFAULT 'en'")

    # ---------------------------------------------------------------
    # customers
    # ---------------------------------------------------------------
    conn.execute('''CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT NOT NULL,
        national_id TEXT,
        created_at TEXT,
        member_type TEXT DEFAULT 'Member',
        occupation TEXT
    )''')

    existing_cols = [row[1] for row in conn.execute("PRAGMA table_info(customers)").fetchall()]
    for col, defn in [
        ('member_type',          "TEXT DEFAULT 'Member'"),
        ('occupation',           "TEXT"),
        ('location',             "TEXT"),
        ('photo',                "BLOB"),
        ('gender',               "TEXT"),
        ('date_of_birth',        "TEXT"),
        ('pwd_status',           "TEXT DEFAULT 'No'"),
        ('subsistence_status',   "TEXT"),
        ('village',              "TEXT"),
        ('parish',               "TEXT"),
        ('sacco_id',             "INTEGER DEFAULT 1"),
        ('nssf_registered',      "INTEGER DEFAULT 0"),
        ('nssf_number',          "TEXT DEFAULT NULL"),
        ('nssf_contribution_rate',"REAL DEFAULT 5.0"),
    ]:
        if col not in existing_cols:
            conn.execute(f"ALTER TABLE customers ADD COLUMN {col} {defn}")

    # ---------------------------------------------------------------
    # NSSF contributions ledger
    # ---------------------------------------------------------------
    conn.execute('''CREATE TABLE IF NOT EXISTS nssf_contributions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        sacco_id INTEGER NOT NULL,
        savings_transaction_id INTEGER,
        gross_deposit REAL NOT NULL,
        nssf_amount REAL NOT NULL,
        net_to_sacco REAL NOT NULL,
        contribution_rate REAL NOT NULL,
        period TEXT NOT NULL,
        remitted INTEGER DEFAULT 0,
        created_at TEXT DEFAULT (datetime('now', 'localtime')),
        FOREIGN KEY(customer_id) REFERENCES customers(id)
    )''')

    # ---------------------------------------------------------------
    # Gold Points ledger
    # ---------------------------------------------------------------
    conn.execute('''CREATE TABLE IF NOT EXISTS gold_points_ledger (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        sacco_id INTEGER NOT NULL,
        points INTEGER NOT NULL,
        reason TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now', 'localtime')),
        FOREIGN KEY(customer_id) REFERENCES customers(id)
    )''')

    # ---------------------------------------------------------------
    # Member PINs — for member self-service portal login.
    # Completely separate from the staff/admin users table.
    # Login identifier: phone number (what every Ugandan knows by heart).
    # PIN is 4 digits, hashed with SHA-256 + salt (same pattern as users).
    # first_login flag forces PIN setup on first access.
    # ---------------------------------------------------------------
    conn.execute('''CREATE TABLE IF NOT EXISTS member_pins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL UNIQUE,
        pin_hash TEXT NOT NULL,
        pin_salt TEXT NOT NULL,
        first_login INTEGER DEFAULT 1,
        last_login TEXT,
        created_at TEXT DEFAULT (datetime('now', 'localtime')),
        FOREIGN KEY(customer_id) REFERENCES customers(id)
    )''')

    # ---------------------------------------------------------------
    # Loans
    # ---------------------------------------------------------------
    conn.execute('''CREATE TABLE IF NOT EXISTS loans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        principal REAL NOT NULL,
        interest_rate REAL NOT NULL,
        term_months INTEGER NOT NULL,
        total_due REAL NOT NULL,
        balance REAL NOT NULL,
        status TEXT NOT NULL,
        disbursed_date TEXT,
        FOREIGN KEY(customer_id) REFERENCES customers(id)
    )''')
    existing_loan_cols = [row[1] for row in conn.execute("PRAGMA table_info(loans)").fetchall()]
    if 'sacco_id' not in existing_loan_cols:
        conn.execute("ALTER TABLE loans ADD COLUMN sacco_id INTEGER DEFAULT 1")

    conn.execute('''CREATE TABLE IF NOT EXISTS loan_schedule (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        loan_id INTEGER NOT NULL,
        installment_no INTEGER,
        due_date TEXT,
        due_amount REAL,
        paid_amount REAL DEFAULT 0,
        status TEXT DEFAULT 'Pending',
        FOREIGN KEY(loan_id) REFERENCES loans(id)
    )''')

    conn.execute('''CREATE TABLE IF NOT EXISTS repayments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        loan_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        method TEXT,
        reference TEXT,
        date TEXT,
        FOREIGN KEY(loan_id) REFERENCES loans(id)
    )''')

    conn.execute('''CREATE TABLE IF NOT EXISTS guarantors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        loan_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        phone TEXT,
        national_id TEXT,
        relationship TEXT,
        FOREIGN KEY(loan_id) REFERENCES loans(id)
    )''')

    conn.execute('''CREATE TABLE IF NOT EXISTS collateral (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        loan_id INTEGER NOT NULL,
        description TEXT NOT NULL,
        estimated_value REAL,
        status TEXT DEFAULT 'Held',
        FOREIGN KEY(loan_id) REFERENCES loans(id)
    )''')

    # ---------------------------------------------------------------
    # Savings
    # ---------------------------------------------------------------
    conn.execute('''CREATE TABLE IF NOT EXISTS savings_accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        balance REAL DEFAULT 0,
        opened_date TEXT,
        FOREIGN KEY(customer_id) REFERENCES customers(id)
    )''')
    existing_sa_cols = [row[1] for row in conn.execute("PRAGMA table_info(savings_accounts)").fetchall()]
    if 'sacco_id' not in existing_sa_cols:
        conn.execute("ALTER TABLE savings_accounts ADD COLUMN sacco_id INTEGER DEFAULT 1")

    conn.execute('''CREATE TABLE IF NOT EXISTS savings_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_id INTEGER NOT NULL,
        type TEXT,
        amount REAL,
        date TEXT,
        FOREIGN KEY(account_id) REFERENCES savings_accounts(id)
    )''')
    existing_txn_cols = [row[1] for row in conn.execute("PRAGMA table_info(savings_transactions)").fetchall()]
    if 'channel' not in existing_txn_cols:
        conn.execute("ALTER TABLE savings_transactions ADD COLUMN channel TEXT")

    # ---------------------------------------------------------------
    # Accounting & messaging
    # ---------------------------------------------------------------
    conn.execute('''CREATE TABLE IF NOT EXISTS ledger (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        account TEXT,
        debit REAL DEFAULT 0,
        credit REAL DEFAULT 0,
        description TEXT,
        reference TEXT
    )''')
    existing_ledger_cols = [row[1] for row in conn.execute("PRAGMA table_info(ledger)").fetchall()]
    if 'sacco_id' not in existing_ledger_cols:
        conn.execute("ALTER TABLE ledger ADD COLUMN sacco_id INTEGER DEFAULT 1")

    conn.execute('''CREATE TABLE IF NOT EXISTS messages_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        message TEXT,
        sent_at TEXT
    )''')

    conn.commit()

    # ---------------------------------------------------------------
    # Safety net: backfilled sacco_id=1 data needs a matching row
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
