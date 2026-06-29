import sqlite3

DB_PATH = 'finance.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()

    conn.execute('''CREATE TABLE IF NOT EXISTS users ( username TEXT PRIMARY KEY, password_hash TEXT, salt TEXT, role TEXT )''')

    conn.execute('''CREATE TABLE IF NOT EXISTS customers ( id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, phone TEXT NOT NULL, national_id TEXT, created_at TEXT, member_type TEXT DEFAULT 'Member', occupation TEXT )''')

    # Migration: add new columns to an existing customers table if upgrading
    # from an older version of the schema (SQLite has no "ADD COLUMN IF NOT EXISTS").
    existing_cols = [row[1] for row in conn.execute("PRAGMA table_info(customers)").fetchall()]
    if 'member_type' not in existing_cols:
        conn.execute("ALTER TABLE customers ADD COLUMN member_type TEXT DEFAULT 'Member'")
    if 'occupation' not in existing_cols:
        conn.execute("ALTER TABLE customers ADD COLUMN occupation TEXT")

    conn.execute('''CREATE TABLE IF NOT EXISTS loans ( id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER NOT NULL, principal REAL NOT NULL, interest_rate REAL NOT NULL, term_months INTEGER NOT NULL, total_due REAL NOT NULL, balance REAL NOT NULL, status TEXT NOT NULL, disbursed_date TEXT, FOREIGN KEY(customer_id) REFERENCES customers(id) )''')

    conn.execute('''CREATE TABLE IF NOT EXISTS loan_schedule ( id INTEGER PRIMARY KEY AUTOINCREMENT, loan_id INTEGER NOT NULL, installment_no INTEGER, due_date TEXT, due_amount REAL, paid_amount REAL DEFAULT 0, status TEXT DEFAULT 'Pending', FOREIGN KEY(loan_id) REFERENCES loans(id) )''')

    conn.execute('''CREATE TABLE IF NOT EXISTS repayments ( id INTEGER PRIMARY KEY AUTOINCREMENT, loan_id INTEGER NOT NULL, amount REAL NOT NULL, method TEXT, reference TEXT, date TEXT, FOREIGN KEY(loan_id) REFERENCES loans(id) )''')

    conn.execute('''CREATE TABLE IF NOT EXISTS guarantors ( id INTEGER PRIMARY KEY AUTOINCREMENT, loan_id INTEGER NOT NULL, name TEXT NOT NULL, phone TEXT, national_id TEXT, relationship TEXT, FOREIGN KEY(loan_id) REFERENCES loans(id) )''')

    conn.execute('''CREATE TABLE IF NOT EXISTS collateral ( id INTEGER PRIMARY KEY AUTOINCREMENT, loan_id INTEGER NOT NULL, description TEXT NOT NULL, estimated_value REAL, status TEXT DEFAULT 'Held', FOREIGN KEY(loan_id) REFERENCES loans(id) )''')

    conn.execute('''CREATE TABLE IF NOT EXISTS savings_accounts ( id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER NOT NULL, balance REAL DEFAULT 0, opened_date TEXT, FOREIGN KEY(customer_id) REFERENCES customers(id) )''')

    conn.execute('''CREATE TABLE IF NOT EXISTS savings_transactions ( id INTEGER PRIMARY KEY AUTOINCREMENT, account_id INTEGER NOT NULL, type TEXT, amount REAL, date TEXT, FOREIGN KEY(account_id) REFERENCES savings_accounts(id) )''')

    conn.execute('''CREATE TABLE IF NOT EXISTS ledger ( id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, account TEXT, debit REAL DEFAULT 0, credit REAL DEFAULT 0, description TEXT, reference TEXT )''')

    conn.execute('''CREATE TABLE IF NOT EXISTS messages_log ( id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER, message TEXT, sent_at TEXT )''')

    conn.commit()
    conn.close()
