import sqlite3
DB_NAME = "sacco_v4.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS members (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, phone TEXT UNIQUE, 
        national_id TEXT, savings_balance REAL DEFAULT 0, joined_date TEXT)''')
    conn.commit()
    conn.close()
