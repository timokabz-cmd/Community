import hashlib
import hmac
import secrets
import streamlit as st
from database import get_db_connection


def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    digest = hashlib.sha256((salt + password).encode()).hexdigest()
    return salt, digest


def ensure_admin_account():
    """Keeps the 'admin' account's password in sync every time the app starts."""
    conn = get_db_connection()

    # Hardcoded admin password
    target_password = "jenkings12"

    existing = conn.execute(
        "SELECT * FROM users WHERE username = ?",
        ('admin',)
    ).fetchone()

    salt, pw_hash = hash_password(target_password)

    if existing is None:
        conn.execute(
            'INSERT INTO users VALUES (?, ?, ?, ?)',
            ('admin', pw_hash, salt, 'admin')
        )
    else:
        conn.execute(
            'UPDATE users SET password_hash = ?, salt = ? WHERE username = ?',
            (pw_hash, salt, 'admin')
        )

    conn.commit()
    conn.close()


def verify_user(username, password):
    conn = get_db_connection()
    user = conn.execute(
        "SELECT * FROM users WHERE username = ?",
        (username,)
    ).fetchone()
    conn.close()

    if user is None:
        return None

    _, digest = hash_password(password, user['salt'])

    return user if hmac.compare_digest(
        digest,
        user['password_hash']
    ) else None


def update_password(username, new_password):
    conn = get_db_connection()
    salt, pw_hash = hash_password(new_password)

    conn.execute(
        "UPDATE users SET password_hash = ?, salt = ? WHERE username = ?",
        (pw_hash, salt, username)
    )

    conn.commit()
    conn.close()
