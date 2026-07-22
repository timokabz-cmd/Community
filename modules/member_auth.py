"""
modules/member_auth.py
Authentication for the member self-service portal.
PostgreSQL version: uses %s placeholders via psycopg2.
"""
import hashlib
import hmac
import secrets
from datetime import datetime
from database import get_db_connection

def _hash_pin(pin: str, salt: str = None):
    if salt is None:
        salt = secrets.token_hex(16)
    digest = hashlib.sha256((salt + pin).encode()).hexdigest()
    return salt, digest

def find_member_by_phone(phone: str):
    phone = phone.strip().replace(" ", "")
    conn  = get_db_connection()
    cur   = conn.cursor()
    cur.execute("SELECT * FROM customers WHERE phone = %s", (phone,))
    row = cur.fetchone()
    if not row:
        cur.execute("SELECT * FROM customers WHERE REPLACE(phone,' ','') = %s", (phone,))
        row = cur.fetchone()
    cur.close()
    conn.close()
    return row

def has_pin(customer_id: int) -> bool:
    conn = get_db_connection()
    cur  = conn.cursor()
    cur.execute("SELECT id FROM member_pins WHERE customer_id = %s", (customer_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row is not None

def is_first_login(customer_id: int) -> bool:
    conn = get_db_connection()
    cur  = conn.cursor()
    cur.execute("SELECT first_login FROM member_pins WHERE customer_id = %s", (customer_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return (row is None) or (row['first_login'] == 1)

def set_pin(customer_id: int, pin: str) -> bool:
    if not pin.isdigit() or len(pin) != 4:
        return False
    salt, pin_hash = _hash_pin(pin)
    conn = get_db_connection()
    cur  = conn.cursor()
    cur.execute("SELECT id FROM member_pins WHERE customer_id = %s", (customer_id,))
    existing = cur.fetchone()
    if existing:
        cur.execute(
            "UPDATE member_pins SET pin_hash=%s, pin_salt=%s, first_login=0 WHERE customer_id=%s",
            (pin_hash, salt, customer_id)
        )
    else:
        cur.execute(
            "INSERT INTO member_pins (customer_id, pin_hash, pin_salt, first_login) VALUES (%s,%s,%s,0)",
            (customer_id, pin_hash, salt)
        )
    conn.commit()
    cur.close()
    conn.close()
    return True

def verify_pin(customer_id: int, pin: str) -> bool:
    conn = get_db_connection()
    cur  = conn.cursor()
    cur.execute("SELECT pin_hash, pin_salt FROM member_pins WHERE customer_id = %s", (customer_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row is None:
        return False
    _, digest = _hash_pin(pin, row['pin_salt'])
    return hmac.compare_digest(digest, row['pin_hash'])

def record_login(customer_id: int):
    conn = get_db_connection()
    cur  = conn.cursor()
    cur.execute(
        "UPDATE member_pins SET last_login=%s, first_login=0 WHERE customer_id=%s",
        (datetime.now().strftime('%Y-%m-%d %H:%M'), customer_id)
    )
    conn.commit()
    cur.close()
    conn.close()

def get_member_data(customer_id: int) -> dict:
    conn = get_db_connection()
    cur  = conn.cursor()

    cur.execute("SELECT * FROM customers WHERE id = %s", (customer_id,))
    customer = cur.fetchone()

    cur.execute("SELECT * FROM savings_accounts WHERE customer_id = %s", (customer_id,))
    savings_account = cur.fetchone()

    savings_txns = []
    if savings_account:
        cur.execute("""
            SELECT * FROM savings_transactions
            WHERE account_id = %s ORDER BY id DESC LIMIT 15
        """, (savings_account['id'],))
        savings_txns = cur.fetchall()

    cur.execute(
        "SELECT * FROM loans WHERE customer_id = %s AND status = 'Active' LIMIT 1",
        (customer_id,)
    )
    active_loan = cur.fetchone()

    loan_schedule = []
    if active_loan:
        cur.execute(
            "SELECT * FROM loan_schedule WHERE loan_id = %s ORDER BY installment_no",
            (active_loan['id'],)
        )
        loan_schedule = cur.fetchall()

    cur.execute("""
        SELECT * FROM nssf_contributions
        WHERE customer_id = %s ORDER BY created_at DESC LIMIT 12
    """, (customer_id,))
    nssf_contribs = cur.fetchall()

    cur.execute(
        "SELECT COALESCE(SUM(nssf_amount),0) AS t FROM nssf_contributions WHERE customer_id=%s",
        (customer_id,)
    )
    nssf_total = list(cur.fetchone().values())[0]

    cur.execute(
        "SELECT COALESCE(SUM(points),0) AS t FROM gold_points_ledger WHERE customer_id=%s",
        (customer_id,)
    )
    gold_points = list(cur.fetchone().values())[0]

    cur.execute("""
        SELECT reason, points, created_at FROM gold_points_ledger
        WHERE customer_id = %s ORDER BY created_at DESC LIMIT 10
    """, (customer_id,))
    gold_history = cur.fetchall()

    sacco = None
    if customer and customer['sacco_id']:
        cur.execute(
            "SELECT sacco_name, district, parish FROM sacco_profile WHERE id=%s",
            (customer['sacco_id'],)
        )
        sacco = cur.fetchone()

    cur.close()
    conn.close()

    return dict(
        customer      = customer,
        savings       = savings_account,
        transactions  = savings_txns,
        loan          = active_loan,
        schedule      = loan_schedule,
        nssf_contribs = nssf_contribs,
        nssf_total    = float(nssf_total),
        gold_points   = int(gold_points),
        gold_history  = gold_history,
        sacco         = sacco,
    )
