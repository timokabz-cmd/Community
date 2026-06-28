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
    
    # 1. Members Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL UNIQUE,
            savings_balance REAL DEFAULT 0.0,
            shares_balance REAL DEFAULT 0.0
        )
    ''')
    
    # 2. Loans Table (Focused on Recovery & Risk)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS loans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_id INTEGER,
            amount_disbursed REAL NOT NULL,
            amount_owed REAL NOT NULL,
            amount_paid REAL DEFAULT 0.0,
            due_date TEXT NOT NULL,
            status TEXT DEFAULT 'Active', -- Active, Defaulted, Cleared
            risk_level TEXT DEFAULT 'Low', -- Low, Medium, High
            FOREIGN KEY(member_id) REFERENCES members(id)
        )
    ''')
    
    # 3. Immutable Double-Entry Ledger Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ledger (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            loan_id INTEGER,
            account_debit TEXT NOT NULL,
            account_credit TEXT NOT NULL,
            amount REAL NOT NULL,
            narration TEXT NOT NULL,
            FOREIGN KEY(loan_id) REFERENCES loans(id)
        )
    ''')
    
    # Seed Mock Data if empty
    cursor.execute("SELECT COUNT(*) FROM members")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO members (name, phone, savings_balance, shares_balance) VALUES (?, ?, ?, ?)", [
            ("John Okello", "256772000111", 600000, 200000),
            ("Sarah Namubiru", "256701222333", 1200000, 400000),
            ("David Mukasa", "256782444555", 150000, 50000)
        ])
        
        # Seed Mock Loans
        cursor.executemany("INSERT INTO loans (member_id, amount_disbursed, amount_owed, due_date, status, risk_level) VALUES (?, ?, ?, ?, ?, ?)", [
            (1, 1500000, 1500000, "2026-07-05", "Active", "Low"),
            (2, 3000000, 3000000, "2026-06-20", "Active", "High"), # Past Due
            (3, 400000, 100000, "2026-06-25", "Active", "Medium") # Partially paid
        ])
        
    conn.commit()
    conn.close()

def record_repayment(loan_id, amount, phone):
    """
    Executes a strict double-entry ledger movement:
    DEBIT: Mobile Money Wallet (Asset increases)
    CREDIT: Outstanding Loans (Asset decreases)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Fetch loan details
    cursor.execute("SELECT amount_owed, amount_paid FROM loans WHERE id = ?", (loan_id,))
    loan = cursor.fetchone()
    
    if not loan:
        return False, "Loan not found"
        
    new_paid = loan['amount_paid'] + amount
    new_owed = max(0.0, loan['amount_owed'] - amount)
    new_status = 'Cleared' if new_owed <= 0 else 'Active'
    
    # Update Loan balances
    cursor.execute('''
        UPDATE loans 
        SET amount_paid = ?, amount_owed = ?, status = ?, risk_level = 'Low' 
        WHERE id = ?
    ''', (new_paid, new_owed, new_status, loan_id))
    
    # Write Immutable Ledger entry
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
        INSERT INTO ledger (timestamp, loan_id, account_debit, account_credit, amount, narration)
        VALUES (?, ?, 'Mobile Money Escrow A/C', 'Loan Portfolio A/C', ?, ?)
    ''', (timestamp, loan_id, amount, f"Automated MoMo Repayment from {phone}"))
    
    conn.commit()
    conn.close()
    return True, f"Successfully cleared UGX {amount:,}"
