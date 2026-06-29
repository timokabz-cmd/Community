# database/connection.py
import sqlite3
import streamlit as st

DB_PATH = 'finance.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    # Add your CREATE TABLE statements here
    conn.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password_hash TEXT, salt TEXT, role TEXT)''')
    # ... include all other table creation logic ...
    conn.commit()
    conn.close()
