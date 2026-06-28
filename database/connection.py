import sqlite3
import streamlit as st
from datetime import datetime
import secrets
import hashlib

DB_PATH = 'finance.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    # Core Tables
    conn.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password_hash TEXT, salt TEXT, role TEXT)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS customers (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, phone TEXT NOT NULL, national_id TEXT, created_at TEXT)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS loans (id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER NOT NULL, principal REAL NOT NULL, interest_rate REAL NOT NULL, term_months INTEGER NOT NULL, total_due REAL NOT NULL, balance REAL NOT NULL, status TEXT NOT NULL, disbursed_date TEXT, FOREIGN KEY(customer_id) REFERENCES customers(id))''')
    conn.execute('''CREATE TABLE IF NOT EXISTS repayments (id INTEGER PRIMARY KEY AUTOINCREMENT, loan_id INTEGER NOT NULL, amount REAL NOT NULL, method TEXT, reference TEXT, date TEXT, FOREIGN KEY(loan_id) REFERENCES loans(id))''')
    conn.execute('''CREATE TABLE IF NOT EXISTS ledger (id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, account TEXT, debit REAL DEFAULT 0, credit REAL DEFAULT 0, description TEXT, reference TEXT)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS messages_log (id INTEGER PRIMARY KEY AUTOINCREMENT, customer_id INTEGER, message TEXT, sent_at TEXT)''')
    conn.commit()

    # Admin Setup
    existing = conn.execute("SELECT * FROM users WHERE username = ?", ('admin',)).fetchone()
    if existing is None:
        from auth.login import hash_password # Note: We will import this in the next step
        salt, pw_hash = hash_password(st.secrets.get("ADMIN_PASSWORD", "admin123"))
        conn.execute('INSERT INTO users VALUES (?, ?, ?, ?)', ('admin', pw_hash, salt, 'admin'))
        conn.commit()
    
    conn.close()

