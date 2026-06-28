import sqlite3

# The name of your database file
DB_NAME = "community_finance.db"

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DB_NAME)
    # This allows us to access columns by name (e.g., row['name'])
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database with all required tables for the system."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Members Table
    cursor.execute('''CREATE TABLE IF NOT EXISTS members 
                    (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                     name TEXT NOT NULL, 
                     phone TEXT NOT NULL)''')
    
    # 2. Loans Table (Placeholder for future integration)
    cursor.execute('''CREATE TABLE IF NOT EXISTS loans 
                    (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                     member_id INTEGER, 
                     amount REAL, 
                     status TEXT,
                     FOREIGN KEY(member_id) REFERENCES members(id))''')
    
    # 3. Ledger Table (For double-entry accounting)
    cursor.execute('''CREATE TABLE IF NOT EXISTS ledger 
                    (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                     timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, 
                     loan_id INTEGER, 
                     amount REAL, 
                     narration TEXT, 
                     operator_name TEXT)''')
    
    conn.commit()
    conn.close()
