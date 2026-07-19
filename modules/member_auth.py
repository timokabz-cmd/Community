"""
modules/member_auth.py

Authentication layer for the member self-service portal.
Completely separate from the staff/admin auth system in auth.py.

Login flow:
  1. Member enters phone number
  2. System finds them in customers table
  3. If first_login=1 (or no PIN set): prompt to create a 4-digit PIN
  4. Otherwise: verify PIN → grant session access

Security:
  - 4-digit PIN hashed with SHA-256 + random 16-byte salt
  - Same pattern as admin password hashing in auth.py
  - PIN stored in member_pins table, never in customers table
  - Session state holds customer_id only — no raw PIN ever stored
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
    """
    Look up a customer by phone number.
    Returns the customer row or None.
    Strips spaces and handles both 07xx and +2567xx formats.
    """
    phone = phone.strip().replace(" ", "")
    conn  = get_db_connection()
    # Try exact match first, then normalised variants
    row = (
        conn.execute("SELECT * FROM customers WHERE phone = ?", (phone,)).fetchone()
        or conn.execute("SELECT * FROM customers WHERE REPLACE(phone,' ','') = ?", (phone,)).fetchone()
    )
    conn.close()
    return row


def has_pin(customer_id: int) -> bool:
    conn = get_db_connection()
    row  = conn.execute(
        "SELECT id FROM member_pins WHERE customer_id = ?", (customer_id,)
    ).fetchone()
    conn.close()
    return row is not None


def is_first_login(customer_id: int) -> bool:
    conn = get_db_connection()
    row  = conn.execute(
        "SELECT first_login FROM member_pins WHERE customer_id = ?", (customer_id,)
    ).fetchone()
    conn.close()
    return (row is None) or (row['first_login'] == 1)


def set_pin(customer_id: int, pin: str) -> bool:
    """Create or replace the PIN for a member. Returns True on success."""
    if not pin.isdigit() or len(pin) != 4:
        return False
    salt, pin_hash = _hash_pin(pin)
    conn = get_db_connection()
    existing = conn.execute(
        "SELECT id FROM member_pins WHERE customer_id = ?", (customer_id,)
    ).fetchone()
    if existing:
        conn.execute(
            "UPDATE member_pins SET pin_hash=?, pin_salt=?, first_login=0 WHERE customer_id=?",
            (pin_hash, salt, customer_id)
        )
    else:
        conn.execute(
            """INSERT INTO member_pins
               (customer_id, pin_hash, pin_salt, first_login)
               VALUES (?, ?, ?, 0)""",
            (customer_id, pin_hash, salt)
        )
    conn.commit()
    conn.close()
    return True


def verify_pin(customer_id: int, pin: str) -> bool:
    """Returns True if the supplied PIN matches the stored hash."""
    conn = get_db_connection()
    row  = conn.execute(
        "SELECT pin_hash, pin_salt FROM member_pins WHERE customer_id = ?",
        (customer_id,)
    ).fetchone()
    conn.close()
    if row is None:
        return False
    _, digest = _hash_pin(pin, row['pin_salt'])
    return hmac.compare_digest(digest, row['pin_hash'])


def record_login(customer_id: int):
    """Stamp last_login timestamp and clear first_login flag."""
    conn = get_db_connection()
    conn.execute(
        "UPDATE member_pins SET last_login=?, first_login=0 WHERE customer_id=?",
        (datetime.now().strftime('%Y-%m-%d %H:%M'), customer_id)
    )
    conn.commit()
    conn.close()


def get_member_data(customer_id: int) -> dict:
    """
    Single round-trip pulling everything the member portal needs.
    Returns a dict so the portal never makes its own DB calls.
    """
    conn = get_db_connection()

    customer = conn.execute(
        "SELECT * FROM customers WHERE id = ?", (customer_id,)
    ).fetchone()

    savings_account = conn.execute(
        "SELECT * FROM savings_accounts WHERE customer_id = ?", (customer_id,)
    ).fetchone()

    savings_txns = []
    if savings_account:
        savings_txns = conn.execute(
            """SELECT * FROM savings_transactions
               WHERE account_id = ?
               ORDER BY id DESC LIMIT 15""",
            (savings_account['id'],)
        ).fetchall()

    active_loan = conn.execute(
        "SELECT * FROM loans WHERE customer_id = ? AND status = 'Active' LIMIT 1",
        (customer_id,)
    ).fetchone()

    loan_schedule = []
    if active_loan:
        loan_schedule = conn.execute(
            """SELECT * FROM loan_schedule
               WHERE loan_id = ?
               ORDER BY installment_no""",
            (active_loan['id'],)
        ).fetchall()

    nssf_contribs = conn.execute(
        """SELECT * FROM nssf_contributions
           WHERE customer_id = ?
           ORDER BY created_at DESC LIMIT 12""",
        (customer_id,)
    ).fetchall()

    nssf_total = conn.execute(
        "SELECT COALESCE(SUM(nssf_amount),0) FROM nssf_contributions WHERE customer_id=?",
        (customer_id,)
    ).fetchone()[0]

    gold_points = conn.execute(
        "SELECT COALESCE(SUM(points),0) FROM gold_points_ledger WHERE customer_id=?",
        (customer_id,)
    ).fetchone()[0]

    gold_history = conn.execute(
        """SELECT reason, points, created_at FROM gold_points_ledger
           WHERE customer_id = ?
           ORDER BY created_at DESC LIMIT 10""",
        (customer_id,)
    ).fetchall()

    sacco = None
    if customer and customer['sacco_id']:
        sacco = conn.execute(
            "SELECT sacco_name, district, parish FROM sacco_profile WHERE id=?",
            (customer['sacco_id'],)
        ).fetchone()

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
