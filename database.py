import sqlite3

def get_db_connection():
    # Connect to the financial database
    conn = sqlite3.connect('finance_system.db')
    conn.row_factory = sqlite3.Row  # Allows accessing columns by name
    return conn

def init_db():
    conn = get_db_connection()
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
                     
    # 4. Users Table (New for Authentication)
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                    (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, role TEXT)''')
    
    # Create a default admin user if the table is empty
    cursor.execute("SELECT count(*) FROM users")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)", 
                       ("admin", "admin123", "Admin"))
    
    conn.commit()
    conn.close()
