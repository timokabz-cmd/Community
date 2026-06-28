import streamlit as st
import sqlite3
import hashlib
import hmac
import secrets
from datetime import datetime
import random

DB_PATH = 'finance.db'

# ---------------------------------------------------------------------------
# 1. DATABASE CONNECTION HELPERS
# ---------------------------------------------------------------------------
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    digest = hashlib.sha256((salt + password).encode()).hexdigest()
    return salt, digest

# ---------------------------------------------------------------------------
# 2. DOUBLE-ENTRY ACCOUNTING HELPERS
# (defined early so the seed function can use them)
# ---------------------------------------------------------------------------
def post_double_entry(account_debit, account_credit, amount, description, reference=None):
    """Posts a balanced debit/credit pair to the ledger for any transaction."""
    conn = get_db_connection()
    today = datetime.now().strftime('%Y-%m-%d %H:%M')
    conn.execute(
        "INSERT INTO ledger (date, account, debit, credit, description, reference) VALUES (?,?,?,?,?,?)",
        (today, account_debit, amount, 0, description, reference)
    )
    conn.execute(
        "INSERT INTO ledger (date, account, debit, credit, description, reference) VALUES (?,?,?,?,?,?)",
        (today, account_credit, 0, amount, description, reference)
    )
    conn.commit()
    conn.close()

def _post_double_entry_on_conn(conn, account_debit, account_credit, amount, description, reference=None):
    """Same as post_double_entry but reuses an existing open connection (used during seeding)."""
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    conn.execute(
        "INSERT INTO ledger (date, account, debit, credit, description, reference) VALUES (?,?,?,?,?,?)",
        (now, account_debit, amount, 0, description, reference)
    )
    conn.execute(
        "INSERT INTO ledger (date, account, debit, credit, description, reference) VALUES (?,?,?,?,?,?)",
        (now, account_credit, 0, amount, description, reference)
    )

def get_ledger(limit=200):
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM ledger ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return rows

def get_trial_balance():
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT account, SUM(debit) as total_debit, SUM(credit) as total_credit "
        "FROM ledger GROUP BY account ORDER BY account"
    ).fetchall()
    conn.close()
    return rows

# ---------------------------------------------------------------------------
# 3. SEED DATA — 50 Ugandan customer profiles
# (embedded here so Streamlit Cloud auto-populates on first deploy)
# ---------------------------------------------------------------------------
_SEED_CUSTOMERS = [
    ("Nakato Sarah",          "077255977",  "CM920012345YDRE"),
    ("Wasswa John",           "077255978",  "CM930023456ABCD"),
    ("Namukasa Florence",     "077255979",  "CM890034567EFGH"),
    ("Ssemakula Robert",      "075255980",  "CM910045678IJKL"),
    ("Namusoke Grace",        "077255981",  "CM940056789MNOP"),
    ("Kato Emmanuel",         "075255982",  "CM900067890QRST"),
    ("Nalubega Harriet",      "076255983",  "CM950078901UVWX"),
    ("Mukasa David",          "077255984",  "CM880089012YZAB"),
    ("Namubiru Prossy",       "075255985",  "CM920090123CDEF"),
    ("Ssali Fred",            "077255986",  "CM910001234GHIJ"),
    ("Akello Mary",           "078255987",  "CM930012345KLMN"),
    ("Oryem Patrick",         "077255988",  "CM900023456OPQR"),
    ("Apio Immaculate",       "075255989",  "CM940034567STUV"),
    ("Okello Geoffrey",       "076255990",  "CM920045678WXYZ"),
    ("Achola Joyce",          "077255991",  "CM910056789ABCD"),
    ("Muwanga Alex",          "077255992",  "CM950067890EFGH"),
    ("Nakyagaba Agnes",       "075255993",  "CM890078901IJKL"),
    ("Kibuuka Moses",         "077255994",  "CM930089012MNOP"),
    ("Zawedde Phiona",        "076255995",  "CM900090123QRST"),
    ("Nsubuga Ivan",          "077255996",  "CM920001234UVWX"),
    ("Atim Christine",        "078255997",  "CM940012345YZAB"),
    ("Olweny Samuel",         "077255998",  "CM910023456CDEF"),
    ("Aber Sandra",           "075255999",  "CM950034567GHIJ"),
    ("Ojok Richard",          "077256000",  "CM900045678KLMN"),
    ("Adong Lillian",         "076256001",  "CM930056789OPQR"),
    ("Mugisha Peter",         "077256002",  "CM920067890STUV"),
    ("Tumuhimbise Rose",      "075256003",  "CM910078901WXYZ"),
    ("Kabagambe Joseph",      "077256004",  "CM940089012ABCD"),
    ("Kobusingye Judith",     "078256005",  "CM890090123EFGH"),
    ("Rwaheru Daniel",        "077256006",  "CM930001234IJKL"),
    ("Asingwire Eunice",      "075256007",  "CM900012345MNOP"),
    ("Byaruhanga Isaac",      "076256008",  "CM920023456QRST"),
    ("Kamugisha Annet",       "077256009",  "CM910034567UVWX"),
    ("Tusiime Simon",         "077256010",  "CM950045678YZAB"),
    ("Birungi Consolata",     "075256011",  "CM900056789CDEF"),
    ("Muhindo Vincent",       "077256012",  "CM930067890GHIJ"),
    ("Kabugho Gertrude",      "076256013",  "CM920078901KLMN"),
    ("Masereka Julius",       "077256014",  "CM910089012OPQR"),
    ("Baluku Beatrice",       "078256015",  "CM940090123STUV"),
    ("Mukirane Stephen",      "077256016",  "CM890001234WXYZ"),
    ("Nabirye Irene",         "075256017",  "CM930012345ABCD"),
    ("Wanyama Brian",         "077256018",  "CM900023456EFGH"),
    ("Chemutai Jane",         "076256019",  "CM920034567IJKL"),
    ("Chepkoech David",       "077256020",  "CM910045678MNOP"),
    ("Ouma Lawrence",         "075256021",  "CM950056789QRST"),
    ("Aduku Patience",        "077256022",  "CM900067890UVWX"),
    ("Ocen Benard",           "077256023",  "CM930078901YZAB"),
    ("Awor Dorcus",           "076256024",  "CM920089012CDEF"),
    ("Mwaka Ruth",            "078256025",  "CM910090123GHIJ"),
    ("Kitimbo Gerald",        "077256026",  "CM940001234IJKL"),
]

# (principal UGX, flat interest %, term months) — one entry per customer above
_SEED_LOANS = [
    (500_000,    10,  3),
    (1_000_000,  12,  6),
    (750_000,    10,  3),
    (2_000_000,  15,  6),
    (300_000,    10,  2),
    (1_500_000,  12,  6),
    (800_000,    10,  3),
    (5_000_000,  18, 12),
    (600_000,    10,  3),
    (2_500_000,  15,  9),
    (1_200_000,  12,  6),
    (400_000,    10,  2),
    (3_000_000,  15,  9),
    (700_000,    10,  3),
    (1_800_000,  12,  6),
    (900_000,    10,  3),
    (4_000_000,  18, 12),
    (650_000,    10,  3),
    (2_200_000,  15,  9),
    (1_100_000,  12,  6),
    (350_000,    10,  2),
    (3_500_000,  15, 12),
    (850_000,    10,  3),
    (1_600_000,  12,  6),
    (950_000,    10,  3),
    (6_000_000,  20, 12),
    (550_000,    10,  3),
    (2_800_000,  15,  9),
    (1_300_000,  12,  6),
    (450_000,    10,  2),
    (500_000,    10,  3),
    (1_000_000,  12,  6),
    (750_000,    10,  3),
    (2_000_000,  15,  6),
    (300_000,    10,  2),
    (7_500_000,  20, 12),
    (800_000,    10,  3),
    (1_500_000,  12,  6),
    (600_000,    10,  3),
    (2_500_000,  15,  9),
    (1_200_000,  12,  6),
    (400_000,    10,  2),
    (3_000_000,  15,  9),
    (700_000,    10,  3),
    (1_800_000,  12,  6),
    (900_000,    10,  3),
    (4_500_000,  18, 12),
    (650_000,    10,  3),
    (2_200_000,  15,  9),
    (1_100_000,  12,  6),
]

_SEED_METHODS = ["MTN MoMo", "Airtel Money", "Bank Transfer", "Cash"]


def _run_seed():
    """
    Populates the database with 50 demo profiles, loans, and repayments.
    Called automatically by init_db() when the customers table is empty.
    Safe to call multiple times — the guard in init_db() prevents duplicates.
    """
    conn = get_db_connection()
    today = datetime.now().strftime('%Y-%m-%d')
    now   = datetime.now().strftime('%Y-%m-%d %H:%M')

    # ── Insert 50 customers ──────────────────────────────────────────────────
    customer_ids = []
    for name, phone, nid in _SEED_CUSTOMERS:
        cur = conn.execute(
            "INSERT INTO customers (name, phone, national_id, created_at) VALUES (?,?,?,?)",
            (name, phone, nid, today)
        )
        customer_ids.append(cur.lastrowid)
    conn.commit()

    # ── Issue one loan per customer ──────────────────────────────────────────
    loans = []  # (loan_id, total_due, customer_id, customer_name)
    for i, cid in enumerate(customer_ids):
        principal, rate, term = _SEED_LOANS[i]
        total_due = round(principal * (1 + rate / 100), 2)
        cur = conn.execute(
            """INSERT INTO loans
               (customer_id, principal, interest_rate, term_months,
                total_due, balance, status, disbursed_date)
               VALUES (?,?,?,?,?,?,?,?)""",
            (cid, principal, rate, term, total_due, total_due, 'Active', today)
        )
        lid = cur.lastrowid
        loans.append((lid, total_due, cid, _SEED_CUSTOMERS[i][0]))
        _post_double_entry_on_conn(
            conn, "Loans Receivable", "Cash/Bank",
            principal,
            f"Loan #{lid} disbursed — {_SEED_CUSTOMERS[i][0]}",
            f"LOAN-{lid}"
        )
    conn.commit()

    # ── Repayments ───────────────────────────────────────────────────────────
    # Loans  0–9  → fully repaid  (Closed)
    # Loans 10–24 → one partial payment (~50 % of total due)
    # Loans 25–34 → two partial payments
    # Loans 35–49 → no payments yet (freshly disbursed)

    for idx, (lid, total_due, cid, cname) in enumerate(loans):
        method = _SEED_METHODS[idx % len(_SEED_METHODS)]

        if idx < 10:
            # Full repayment
            amount = total_due
            ref    = f"MM-{secrets.token_hex(4).upper()}"
            conn.execute(
                "INSERT INTO repayments (loan_id, amount, method, reference, date) VALUES (?,?,?,?,?)",
                (lid, amount, method, ref, now)
            )
            conn.execute(
                "UPDATE loans SET balance = 0, status = 'Closed' WHERE id = ?", (lid,)
            )
            _post_double_entry_on_conn(
                conn, "Cash/Bank", "Loans Receivable",
                amount, f"Full repayment — loan #{lid}", ref
            )
            msg = (
                f"Dear {cname}, we have received your payment of "
                f"UGX {amount:,.0f} via {method} (Ref: {ref}). "
                f"Your loan is now fully settled. Thank you!"
            )
            conn.execute(
                "INSERT INTO messages_log (customer_id, message, sent_at) VALUES (?,?,?)",
                (cid, msg, now)
            )

        elif idx < 25:
            # One partial payment (40–60 % of total due, rounded to nearest 1,000)
            frac   = round(random.uniform(0.40, 0.60), 2)
            amount = max(round(total_due * frac / 1000) * 1000, 50_000)
            new_bal = round(total_due - amount, 2)
            ref     = f"MM-{secrets.token_hex(4).upper()}"
            conn.execute(
                "INSERT INTO repayments (loan_id, amount, method, reference, date) VALUES (?,?,?,?,?)",
                (lid, amount, method, ref, now)
            )
            conn.execute(
                "UPDATE loans SET balance = ? WHERE id = ?", (new_bal, lid)
            )
            _post_double_entry_on_conn(
                conn, "Cash/Bank", "Loans Receivable",
                amount, f"Partial repayment — loan #{lid}", ref
            )
            msg = (
                f"Dear {cname}, we have received your payment of "
                f"UGX {amount:,.0f} via {method} (Ref: {ref}). "
                f"Your new loan balance is UGX {new_bal:,.0f}. Thank you."
            )
            conn.execute(
                "INSERT INTO messages_log (customer_id, message, sent_at) VALUES (?,?,?)",
                (cid, msg, now)
            )

        elif idx < 35:
            # Two partial payments
            frac1   = round(random.uniform(0.25, 0.35), 2)
            amount1 = max(round(total_due * frac1 / 1000) * 1000, 50_000)
            bal_1   = round(total_due - amount1, 2)

            frac2   = round(random.uniform(0.20, 0.30), 2)
            amount2 = max(round(bal_1 * frac2 / 1000) * 1000, 50_000)
            bal_2   = round(bal_1 - amount2, 2)

            for amt, bal in [(amount1, bal_1), (amount2, bal_2)]:
                ref = f"MM-{secrets.token_hex(4).upper()}"
                conn.execute(
                    "INSERT INTO repayments (loan_id, amount, method, reference, date) VALUES (?,?,?,?,?)",
                    (lid, amt, method, ref, now)
                )
                _post_double_entry_on_conn(
                    conn, "Cash/Bank", "Loans Receivable",
                    amt, f"Partial repayment — loan #{lid}", ref
                )
                msg = (
                    f"Dear {cname}, we have received your payment of "
                    f"UGX {amt:,.0f} via {method} (Ref: {ref}). "
                    f"Your new loan balance is UGX {bal:,.0f}. Thank you."
                )
                conn.execute(
                    "INSERT INTO messages_log (customer_id, message, sent_at) VALUES (?,?,?)",
                    (cid, msg, now)
                )
            conn.execute(
                "UPDATE loans SET balance = ? WHERE id = ?", (bal_2, lid)
            )
        # idx 35–49: no repayments (freshly disbursed Active loans)

    conn.commit()
    conn.close()

# ---------------------------------------------------------------------------
# 4. DATABASE SCHEMA & INITIALISATION
# ---------------------------------------------------------------------------
def init_db():
    conn = get_db_connection()

    conn.execute('''CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password_hash TEXT,
        salt TEXT,
        role TEXT
    )''')

    conn.execute('''CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT NOT NULL,
        national_id TEXT,
        created_at TEXT
    )''')

    conn.execute('''CREATE TABLE IF NOT EXISTS loans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        principal REAL NOT NULL,
        interest_rate REAL NOT NULL,
        term_months INTEGER NOT NULL,
        total_due REAL NOT NULL,
        balance REAL NOT NULL,
        status TEXT NOT NULL,
        disbursed_date TEXT,
        FOREIGN KEY(customer_id) REFERENCES customers(id)
    )''')

    conn.execute('''CREATE TABLE IF NOT EXISTS repayments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        loan_id INTEGER NOT NULL,
        amount REAL NOT NULL,
        method TEXT,
        reference TEXT,
        date TEXT,
        FOREIGN KEY(loan_id) REFERENCES loans(id)
    )''')

    conn.execute('''CREATE TABLE IF NOT EXISTS ledger (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        account TEXT,
        debit REAL DEFAULT 0,
        credit REAL DEFAULT 0,
        description TEXT,
        reference TEXT
    )''')

    conn.execute('''CREATE TABLE IF NOT EXISTS messages_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        message TEXT,
        sent_at TEXT
    )''')

    conn.commit()

    # Ensure there is always an admin account to log in with
    existing = conn.execute("SELECT * FROM users WHERE username = ?", ('admin',)).fetchone()
    if existing is None:
        default_password = st.secrets.get("ADMIN_PASSWORD", "admin123")
        salt, pw_hash = hash_password(default_password)
        conn.execute('INSERT INTO users VALUES (?, ?, ?, ?)', ('admin', pw_hash, salt, 'admin'))
        conn.commit()

    # Auto-seed 50 demo profiles on the very first run (when DB is empty)
    needs_seed = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0] == 0
    conn.close()

    if needs_seed:
        _run_seed()

# ---------------------------------------------------------------------------
# 5. AUTH HELPERS
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# 6. CUSTOMERS
# ---------------------------------------------------------------------------
def add_customer(name, phone, national_id):
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO customers (name, phone, national_id, created_at) VALUES (?,?,?,?)",
        (name, phone, national_id, datetime.now().strftime('%Y-%m-%d'))
    )
    conn.commit()
    conn.close()

def get_customers():
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM customers ORDER BY id DESC").fetchall()
    conn.close()
    return rows

# ---------------------------------------------------------------------------
# 7. LOANS
# ---------------------------------------------------------------------------
def issue_loan(customer_id, principal, interest_rate, term_months):
    total_due = round(principal * (1 + interest_rate / 100), 2)
    conn = get_db_connection()
    today = datetime.now().strftime('%Y-%m-%d')
    cursor = conn.execute(
        """INSERT INTO loans (customer_id, principal, interest_rate, term_months,
           total_due, balance, status, disbursed_date)
           VALUES (?,?,?,?,?,?,?,?)""",
        (customer_id, principal, interest_rate, term_months, total_due, total_due, 'Active', today)
    )
    loan_id = cursor.lastrowid
    conn.commit()
    conn.close()
    # Loan disbursed: receivable goes up (debit), cash goes out (credit)
    post_double_entry("Loans Receivable", "Cash/Bank", principal,
                      f"Loan #{loan_id} disbursed", f"LOAN-{loan_id}")
    return loan_id

def get_loans(status=None):
    conn = get_db_connection()
    query = """SELECT loans.*, customers.name as customer_name, customers.phone as customer_phone
               FROM loans JOIN customers ON loans.customer_id = customers.id"""
    if status:
        rows = conn.execute(query + " WHERE loans.status = ? ORDER BY loans.id DESC", (status,)).fetchall()
    else:
        rows = conn.execute(query + " ORDER BY loans.id DESC").fetchall()
    conn.close()
    return rows

def get_loan(loan_id):
    conn = get_db_connection()
    row = conn.execute(
        """SELECT loans.*, customers.name as customer_name, customers.phone as customer_phone
           FROM loans JOIN customers ON loans.customer_id = customers.id WHERE loans.id = ?""",
        (loan_id,)
    ).fetchone()
    conn.close()
    return row

# ---------------------------------------------------------------------------
# 8. COLLECTIONS — mobile money webhook simulation + client messaging
# ---------------------------------------------------------------------------
def log_message(customer_id, message):
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO messages_log (customer_id, message, sent_at) VALUES (?,?,?)",
        (customer_id, message, datetime.now().strftime('%Y-%m-%d %H:%M'))
    )
    conn.commit()
    conn.close()

def get_messages(limit=20):
    conn = get_db_connection()
    rows = conn.execute(
        """SELECT messages_log.*, customers.name as customer_name FROM messages_log
           JOIN customers ON messages_log.customer_id = customers.id
           ORDER BY messages_log.id DESC LIMIT ?""",
        (limit,)
    ).fetchall()
    conn.close()
    return rows

def record_repayment(loan_id, amount, method="Mobile Money", reference=None):
    """Simulates an automated mobile money webhook: applies the payment,
    updates the ledger, and fires an instant client confirmation message —
    with no manual staff handling in between."""
    loan = get_loan(loan_id)
    if loan is None:
        return None, "Loan not found"
    if amount <= 0:
        return None, "Amount must be greater than zero"

    reference = reference or f"MM-{secrets.token_hex(4).upper()}"
    today = datetime.now().strftime('%Y-%m-%d %H:%M')

    conn = get_db_connection()
    conn.execute(
        "INSERT INTO repayments (loan_id, amount, method, reference, date) VALUES (?,?,?,?,?)",
        (loan_id, amount, method, reference, today)
    )
    new_balance = max(round(loan['balance'] - amount, 2), 0)
    new_status  = 'Closed' if new_balance <= 0 else 'Active'
    conn.execute(
        "UPDATE loans SET balance = ?, status = ? WHERE id = ?",
        (new_balance, new_status, loan_id)
    )
    conn.commit()
    conn.close()

    # Repayment received: cash goes up (debit), receivable goes down (credit)
    post_double_entry("Cash/Bank", "Loans Receivable", amount,
                      f"Repayment for loan #{loan_id}", reference)

    message = (
        f"Dear {loan['customer_name']}, we have received your payment of "
        f"UGX {amount:,.0f} via {method} (Ref: {reference}). "
        f"Your new loan balance is UGX {new_balance:,.0f}. Thank you."
    )
    log_message(loan['customer_id'], message)
    return new_balance, message

def get_repayments(limit=20):
    conn = get_db_connection()
    rows = conn.execute(
        """SELECT repayments.*, customers.name as customer_name FROM repayments
           JOIN loans ON repayments.loan_id = loans.id
           JOIN customers ON loans.customer_id = customers.id
           ORDER BY repayments.id DESC LIMIT ?""",
        (limit,)
    ).fetchall()
    conn.close()
    return rows

# ---------------------------------------------------------------------------
# 9. APP SETUP & AUTHENTICATION
# ---------------------------------------------------------------------------
st.set_page_config(layout="wide", page_title="CommunityFinanceOS", page_icon="🏛️")
init_db()

if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.subheader("🔒 Login Required")
    user_input = st.text_input("Username")
    pwd_input  = st.text_input("Password", type="password")
    if st.button("Login"):
        user = verify_user(user_input, pwd_input)
        if user:
            st.session_state.authenticated = True
            st.session_state.user = user['username']
            st.rerun()
        else:
            st.error("Invalid username or password")
    st.caption("Default login: admin / admin123 — change it after your first login.")
    st.stop()

# ---------------------------------------------------------------------------
# 10. BUSINESS MODULES
# ---------------------------------------------------------------------------
def render_dashboard():
    conn = get_db_connection()
    total_customers = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    active_loans    = conn.execute("SELECT COUNT(*) FROM loans WHERE status='Active'").fetchone()[0]
    outstanding     = conn.execute("SELECT COALESCE(SUM(balance),0) FROM loans WHERE status='Active'").fetchone()[0]
    collected       = conn.execute("SELECT COALESCE(SUM(amount),0) FROM repayments").fetchone()[0]
    conn.close()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Customers",          total_customers)
    col2.metric("Active Loans",       active_loans)
    col3.metric("Outstanding Balance", f"UGX {outstanding:,.0f}")
    col4.metric("Total Collected",    f"UGX {collected:,.0f}")

    st.write("#### Recent Client Messages")
    messages = get_messages(limit=5)
    if not messages:
        st.info("No messages sent yet. Record a repayment in Collections to see auto-generated confirmations here.")
    for m in messages:
        st.write(f"**{m['customer_name']}** — {m['sent_at']}")
        st.caption(m['message'])


def render_customers():
    st.write("#### Add New Customer")
    with st.form("add_customer_form", clear_on_submit=True):
        name        = st.text_input("Full name")
        phone       = st.text_input("Phone number (e.g. 0772xxxxxx)")
        national_id = st.text_input("National ID (optional)")
        submitted   = st.form_submit_button("Add Customer")
        if submitted:
            if name and phone:
                add_customer(name, phone, national_id)
                st.success(f"Customer '{name}' added.")
            else:
                st.error("Name and phone number are required.")

    st.write("#### All Customers")
    customers = get_customers()
    if customers:
        st.dataframe(
            [{"ID": c['id'], "Name": c['name'], "Phone": c['phone'],
              "National ID": c['national_id'], "Joined": c['created_at']} for c in customers],
            use_container_width=True
        )
    else:
        st.info("No customers yet.")


def render_loans():
    customers = get_customers()
    st.write("#### Issue a New Loan")
    if not customers:
        st.warning("Add a customer first before issuing a loan.")
    else:
        with st.form("issue_loan_form", clear_on_submit=True):
            customer_map    = {f"{c['name']} ({c['phone']})": c['id'] for c in customers}
            customer_choice = st.selectbox("Customer", list(customer_map.keys()))
            principal       = st.number_input("Principal amount (UGX)", min_value=0.0, step=10000.0)
            interest_rate   = st.number_input("Flat interest rate (%)", min_value=0.0, step=1.0, value=10.0)
            term_months     = st.number_input("Term (months)", min_value=1, step=1, value=3)
            submitted       = st.form_submit_button("Disburse Loan")
            if submitted:
                if principal <= 0:
                    st.error("Principal must be greater than zero.")
                else:
                    loan_id = issue_loan(customer_map[customer_choice], principal,
                                         interest_rate, int(term_months))
                    st.success(f"Loan #{loan_id} disbursed for {customer_choice}.")

    st.write("#### All Loans")
    loans = get_loans()
    if loans:
        st.dataframe(
            [{"Loan ID": l['id'], "Customer": l['customer_name'], "Principal": l['principal'],
              "Rate %": l['interest_rate'], "Total Due": l['total_due'], "Balance": l['balance'],
              "Status": l['status'], "Disbursed": l['disbursed_date']} for l in loans],
            use_container_width=True
        )
    else:
        st.info("No loans issued yet.")


def render_collections():
    st.write("#### 📲 Mobile Money Webhook Simulation")
    st.caption(
        "Simulates an incoming mobile money payment notification (MTN/Airtel). Submitting this form "
        "applies the payment, updates the ledger, and sends a confirmation message automatically — "
        "no staff handling in between."
    )
    active_loans = get_loans(status='Active')
    if not active_loans:
        st.info("No active loans to collect against.")
    else:
        with st.form("webhook_form", clear_on_submit=True):
            loan_map    = {f"Loan #{l['id']} — {l['customer_name']} (Bal: {l['balance']:,.0f})": l['id']
                           for l in active_loans}
            loan_choice = st.selectbox("Loan", list(loan_map.keys()))
            amount      = st.number_input("Amount received (UGX)", min_value=0.0, step=1000.0)
            method      = st.selectbox("Channel", ["MTN MoMo", "Airtel Money", "Bank Transfer", "Cash"])
            submitted   = st.form_submit_button("Simulate Webhook / Record Payment")
            if submitted:
                if amount <= 0:
                    st.error("Amount must be greater than zero.")
                else:
                    loan_id = loan_map[loan_choice]
                    new_balance, message = record_repayment(loan_id, amount, method)
                    st.success(f"Payment processed automatically. New balance: UGX {new_balance:,.0f}")
                    st.write("**Auto-generated client confirmation:**")
                    st.code(message, language=None)

    st.write("#### Recent Repayments")
    repayments = get_repayments(limit=20)
    if repayments:
        st.dataframe(
            [{"Date": r['date'], "Customer": r['customer_name'], "Loan ID": r['loan_id'],
              "Amount": r['amount'], "Method": r['method'], "Reference": r['reference']}
             for r in repayments],
            use_container_width=True
        )
    else:
        st.info("No repayments recorded yet.")


def render_accounting():
    st.write("#### Double-Entry Ledger")
    st.caption("Every loan disbursement and repayment automatically posts a balanced debit/credit entry here.")
    ledger = get_ledger(limit=200)
    if ledger:
        st.dataframe(
            [{"Date": l['date'], "Account": l['account'], "Debit": l['debit'],
              "Credit": l['credit'], "Description": l['description'], "Reference": l['reference']}
             for l in ledger],
            use_container_width=True
        )
    else:
        st.info("No ledger entries yet.")

    st.write("#### Trial Balance")
    tb = get_trial_balance()
    if tb:
        total_debit  = sum(row['total_debit']  for row in tb)
        total_credit = sum(row['total_credit'] for row in tb)
        st.dataframe(
            [{"Account": row['account'], "Total Debit": row['total_debit'],
              "Total Credit": row['total_credit']} for row in tb],
            use_container_width=True
        )
        st.write(f"**Total Debits: UGX {total_debit:,.0f}  |  Total Credits: UGX {total_credit:,.0f}**")
        if abs(total_debit - total_credit) < 0.01:
            st.success("Books are balanced ✅")
        else:
            st.error("Books are out of balance — check ledger entries.")
    else:
        st.info("No transactions posted yet.")


def render_reporting():
    st.write("#### Portfolio Summary")
    loans  = get_loans()
    active = [l for l in loans if l['status'] == 'Active']
    closed = [l for l in loans if l['status'] == 'Closed']
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Loans Issued", len(loans))
    col2.metric("Active Loans",       len(active))
    col3.metric("Closed Loans",       len(closed))

    if active:
        outstanding_total = sum(l['balance'] for l in active)
        st.write(f"**Total Outstanding Portfolio:** UGX {outstanding_total:,.0f}")

    st.write("#### Client Messages Log")
    messages = get_messages(limit=50)
    if messages:
        st.dataframe(
            [{"Date": m['sent_at'], "Customer": m['customer_name'], "Message": m['message']}
             for m in messages],
            use_container_width=True
        )
    else:
        st.info("No messages sent yet.")


def render_account_settings():
    st.write("#### Change Password")
    new_pwd     = st.text_input("New password",          type="password")
    confirm_pwd = st.text_input("Confirm new password",  type="password")
    if st.button("Update password"):
        if not new_pwd:
            st.error("Password cannot be empty.")
        elif new_pwd != confirm_pwd:
            st.error("Passwords don't match.")
        else:
            update_password(st.session_state.user, new_pwd)
            st.success("Password updated. Use it next time you log in.")

# ---------------------------------------------------------------------------
# 11. NAVIGATION & ROUTER
# ---------------------------------------------------------------------------
st.sidebar.title("🏛️ CommunityFinanceOS")
st.sidebar.write(f"Logged in as: **{st.session_state.user}**")
menu   = ["Dashboard", "Customers", "Loans", "Collections", "Accounting", "Reporting", "Account Settings"]
choice = st.sidebar.selectbox("Select Workspace", menu)

if st.sidebar.button("Logout"):
    st.session_state.authenticated = False
    st.rerun()

st.header(f"💼 {choice}")
if   choice == "Dashboard":        render_dashboard()
elif choice == "Customers":        render_customers()
elif choice == "Loans":            render_loans()
elif choice == "Collections":      render_collections()
elif choice == "Accounting":       render_accounting()
elif choice == "Reporting":        render_reporting()
elif choice == "Account Settings": render_account_settings()
