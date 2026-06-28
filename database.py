import sqlite3

# Using v3 ensures the app starts with a fresh, clean database
DB_NAME = "sacco_v3.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Members Table
    cursor.execute('''CREATE TABLE IF NOT EXISTS members (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, phone TEXT UNIQUE, 
        national_id TEXT, savings_balance REAL DEFAULT 0, shares_balance REAL DEFAULT 0, joined_date TEXT)''')
    # Loans Table
    cursor.execute('''CREATE TABLE IF NOT EXISTS loans (
        id INTEGER PRIMARY KEY AUTOINCREMENT, member_id INTEGER, loan_type TEXT, 
        amount_disbursed REAL, amount_owed REAL, amount_paid REAL DEFAULT 0, 
        status TEXT DEFAULT 'Pending', risk_level TEXT DEFAULT 'Low', 
        collateral_details TEXT, due_date TEXT)''')
    # Ledger Table
    cursor.execute('''CREATE TABLE IF NOT EXISTS ledger (
        id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, loan_id INTEGER, 
        amount REAL, narration TEXT, operator_name TEXT)''')
    conn.commit()
    conn.close()
