import hashlib
import hmac
import secrets
import streamlit as st
from database import get_db_connection

# ── Role constants — use these everywhere, never raw strings ─────────────────
ROLE_SUPER_ADMIN = 'super_admin'   # platform owner (timo) — all SACCOs, all pages
ROLE_SACCO_ADMIN = 'sacco_admin'   # SACCO chairperson/manager — own SACCO only, management pages
ROLE_STAFF       = 'staff'         # data entry clerk — own SACCO only, limited pages

def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    digest = hashlib.sha256((salt + password).encode()).hexdigest()
    return salt, digest

def ensure_admin_account():
    """
    Ensures the platform super-admin account exists on every boot.
    Also migrates any legacy role='admin' rows to role='super_admin' so
    the database stays consistent with the new three-tier system.
    """
    conn = get_db_connection()

    # ── Migrate legacy role values ────────────────────────────────────────────
    # Old system used 'admin' for both the platform owner and SACCO managers.
    # New system: platform owner = 'super_admin', SACCO manager = 'sacco_admin'.
    # We migrate timo to super_admin and any other 'admin' accounts
    # (created via the old Administration form) to sacco_admin, since they were
    # always meant to be SACCO-scoped, not platform-wide.
    conn.execute(
        "UPDATE users SET role = ? WHERE username = ? AND role = 'admin'",
        (ROLE_SUPER_ADMIN, 'timo')
    )
    conn.execute(
        "UPDATE users SET role = ? WHERE username != 'timo' AND role = 'admin'",
        (ROLE_SACCO_ADMIN,)
    )
    conn.commit()

    # ── Create super-admin if not present ────────────────────────────────────
    existing = conn.execute("SELECT * FROM users WHERE username = ?", ('timo',)).fetchone()
    if existing is None:
        try:
            default_password = st.secrets.get("ADMIN_PASSWORD", "timo123")
        except Exception:
            default_password = "timo123"
        salt, pw_hash = hash_password(default_password)
        conn.execute(
            'INSERT INTO users (username, password_hash, salt, role, sacco_id) VALUES (?,?,?,?,?)',
            ('timo', pw_hash, salt, ROLE_SUPER_ADMIN, None)
        )
        conn.commit()

    conn.close()

def verify_user(username, password):
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    if user is None:
        return None
    _, digest = hash_password(password, user['salt'])
    return user if hmac.compare_digest(digest, user['password_hash']) else None

def update_password(username, new_password):
    conn = get_db_connection()
    salt, pw_hash = hash_password(new_password)
    conn.execute(
        "UPDATE users SET password_hash = ?, salt = ? WHERE username = ?",
        (pw_hash, salt, username)
    )
    conn.commit()
    conn.close()

def create_user(username, password, role, sacco_id=None):
    """
    Create any user. Role must be one of ROLE_* constants.
    sacco_id is required for sacco_admin and staff; None for super_admin.
    Returns True on success, False if username already exists.
    """
    if role not in (ROLE_SUPER_ADMIN, ROLE_SACCO_ADMIN, ROLE_STAFF):
        return False
    conn = get_db_connection()
    existing = conn.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone()
    if existing:
        conn.close()
        return False
    salt, pw_hash = hash_password(password)
    conn.execute(
        'INSERT INTO users (username, password_hash, salt, role, sacco_id) VALUES (?,?,?,?,?)',
        (username, pw_hash, salt, role, sacco_id)
    )
    conn.commit()
    conn.close()
    return True

def delete_user(username):
    """Remove a user. Super-admin account (timo) cannot be deleted."""
    if username == 'timo':
        return False
    conn = get_db_connection()
    conn.execute("DELETE FROM users WHERE username = ?", (username,))
    conn.commit()
    conn.close()
    return True

def get_all_users():
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT u.username, u.role, u.sacco_id, s.sacco_name
        FROM users u
        LEFT JOIN sacco_profile s ON u.sacco_id = s.id
        ORDER BY u.role, u.username
    """).fetchall()
    conn.close()
    return rows
