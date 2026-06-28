import sqlite3
import os

def init_db():
    # This ensures the database is created if it doesn't exist
    conn = sqlite3.connect('finance_system.db')
    cursor = conn.cursor()
    
    # 1. Members Table
    cursor.execute('''CREATE TABLE IF NOT EXISTS members 
                    (id INTEGER PRIMARY KEY, name TEXT, phone TEXT)''')
    
    # 2. Loans Table
    cursor.execute('''CREATE TABLE IF NOT EXISTS loans 
                    (id INTEGER PRIMARY KEY, member_id INTEGER, amount REAL, status TEXT, 
                     FOREIGN KEY(member_id) REFERENCES members(id))''')
    
    # 3. Ledger Table
    cursor.execute('''CREATE TABLE IF NOT EXISTS ledger 
                    (id INTEGER PRIMARY KEY, amount REAL, narration TEXT, operator_name TEXT, 
                     timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
                     
    # 4. Users Table (The missing piece)
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                    (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, role TEXT)''')
    
    # Create default admin
    cursor.execute("SELECT count(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", 
                       ("admin", "admin123", "Admin"))
    
    conn.commit()
    conn.close()
