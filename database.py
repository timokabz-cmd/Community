import sqlite3
from datetime import datetime

DB_NAME = "sacco_core.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Expanded Members Profile
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL UNIQUE,
            national_id TEXT,
            savings_balance REAL DEFAULT 0.0,
            shares_balance REAL DEFAULT 0.0,
            joined_date TEXT NOT NULL
        )
    ''')
    
    # 2. Advanced Loans Management
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS loans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER,
            loan_type TEXT NOT NULL, -- Business, Agriculture, Emergency, Education
            amount_disbursed REAL NOT NULL,
            amount_owed REAL NOT NULL,
            amount_paid REAL DEFAULT 0.0,
            date_issued TEXT,
            due_date TEXT NOT NULL,
            status TEXT DEFAULT 'Pending', -- Pending, Approved, Active, Defaulted, Cleared
            risk_level TEXT DEFAULT 'Low', -- Low, Medium, High
            collateral_details TEXT,
            FOREIGN KEY(member_id) REFERENCES members(id)
        )
    ''')
    
    # 3. Immutable Core Double-Entry Ledger
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            loan_id INTEGER,
            account_debit TEXT NOT NULL,
            account_credit TEXT NOT NULL,
            amount REAL NOT NULL,
            narration TEXT NOT NULL,
            operator_name TEXT DEFAULT 'System Automated'
        )
    ''')
    
    # Seed robust mock data if the schema is fresh
    cursor.execute("SELECT COUNT(*) FROM members")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO members (name, phone, national_id, savings_balance, shares_balance, joined_date) VALUES (?, ?, ?, ?, ?, ?)", [
            ("John Okello", "256772000111", "CM95012345XYZ", 650000, 250000, "2025-01-15"),
            ("Sarah Namubiru", "256701222333", "CF91043215ABC", 1450000, 500000, "2025-03-22"),
            ("David Mukasa", "256782444555", "CM88098765LMN", 180000, 60000, "2025-05-10"),
            ("Grace Nakato", "256752777888", "CF99071623PQR", 3000000, 1200000, "2026-02-11")
        ])
        
        cursor.executemany("INSERT INTO loans (member_id, loan_type, amount_disbursed, amount_owed, amount_paid, date_issued, due_date, status, risk_level, collateral_details) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", [
            (1, "Business", 1500000, 1100000, 400000, "2026-01-10", "2026-07-10", "Active", "Low", "Shop Inventory Kraal Receipt"),
            (2, "Agriculture", 3000000, 3000000, 0, "2026-02-15", "2026-05-15", "Active", "High", "Kibanja Land Agreement"),
            (3, "Emergency", 400000, 50000, 350000, "2026-06-01", "2026-07-01", "Active", "Medium", "Logbook Copy"),
            (4, "Development", 5000000, 5000000, 0, None, "2027-06-28", "Pending", "Low", "Land Title Deed")
        ])
        
    conn.commit()
    conn.close()

def add_new_member(name, phone, national_id, initial_savings):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        joined_date = datetime.now().strftime("%Y-%m-%d")
        cursor.execute('''
            INSERT INTO members (name, phone, national_id, savings_balance, joined_date)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, phone, national_id, initial_savings, joined_date))
        conn.commit()
        return True, "Member registered successfully!"
    except sqlite3.IntegrityError:
        return False, "Error: This phone number is already registered."
    finally:
        conn.close()

def issue_loan_request(member_id, loan_type, amount, collateral, duration_months):
    conn = get_db_connection()
    cursor = conn.cursor()
    due_date = datetime.now().strftime("%Y-%m-%d") # Placeholder calculation logic
    cursor.execute('''
        INSERT INTO loans (member_id, loan_type, amount_disbursed, amount_owed, status, risk_level, collateral_details, due_date)
        VALUES (?, ?, ?, ?, 'Pending', 'Low', ?, ?)
    ''', (member_id, loan_type, amount, amount, collateral, due_date))
    conn.commit()
    conn.close()
    return True

def update_loan_status(loan_id, new_status):
    conn = get_db_connection()
    cursor = conn.cursor()
    date_str = datetime.now().strftime("%Y-%m-%d")
    if new_status == "Approved":
        cursor.execute("UPDATE loans SET status = 'Active', date_issued = ? WHERE id = ?", (date_str, loan_id))
    else:
        cursor.execute("UPDATE loans SET status = ? WHERE id = ?", (new_status, loan_id))
    conn.commit()
    conn.close()

def process_manual_payment(loan_id, amount, operator):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT amount_owed, amount_paid FROM loans WHERE id = ?", (loan_id,))
    loan = cursor.fetchone()
    if not loan:
        return False, "Loan record not found."
        
    new_paid = loan['amount_paid'] + amount
    new_owed = max(0.0, loan['amount_owed'] - amount)
    new_status = 'Cleared' if new_owed <= 0 else 'Active'
    
    cursor.execute("UPDATE loans SET amount_paid = ?, amount_owed = ?, status = ? WHERE id = ?", (new_paid, new_owed, new_status, loan_id))
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
        INSERT INTO ledger (timestamp, loan_id, account_debit, account_credit, amount, narration, operator_name)
        VALUES (?, ?, 'Cash Account/Vault', 'Loan Assets Outstanding', ?, ?, ?)
    ''', (timestamp, loan_id, amount, f"Manual counter collection payment receipted", operator))
    
    conn.commit()
    conn.close()
    return True, "Payment tracked cleanly in system ledger."
