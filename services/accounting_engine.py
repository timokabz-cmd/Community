# services/accounting_engine.py

def record_transaction(conn, loan_id, amount, narration, operator):
    """Logs a transaction into the ledger."""
    query = """INSERT INTO ledger (timestamp, loan_id, amount, narration, operator_name) 
               VALUES (CURRENT_TIMESTAMP, ?, ?, ?, ?)"""
    conn.execute(query, (loan_id, amount, narration, operator))
    conn.commit()

def get_ledger_balance(conn, loan_id):
    """Calculates total paid for a specific loan."""
    balance = conn.execute("SELECT SUM(amount) FROM ledger WHERE loan_id = ?", (loan_id,)).fetchone()[0]
    return balance or 0
