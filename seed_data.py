#!/usr/bin/env python3
"""
seed_data.py  —  Populate CommunityFinanceOS with 50 sample profiles.

Place this file in the same folder as app.py and finance.db, then run:
    python seed_data.py

Safe to re-run: skips seeding if 50+ customers already exist.
"""

import sqlite3
import secrets
from datetime import datetime
import random

DB_PATH = 'finance.db'

# ── Minimal DB helpers (no Streamlit dependency) ─────────────────────────────

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def post_double_entry(conn, account_debit, account_credit, amount, description, reference=None):
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    conn.execute(
        "INSERT INTO ledger (date, account, debit, credit, description, reference) VALUES (?,?,?,?,?,?)",
        (now, account_debit, amount, 0, description, reference)
    )
    conn.execute(
        "INSERT INTO ledger (date, account, debit, credit, description, reference) VALUES (?,?,?,?,?,?)",
        (now, account_credit, 0, amount, description, reference)
    )

# ── 50 Ugandan customer profiles ─────────────────────────────────────────────
# Names drawn from Buganda, Acholi, Langi, Ankole, Toro, and Eastern Uganda.
# Phone format: 9-digit (077XXXXXXX / 075XXXXXXX / 076XXXXXXX / 078XXXXXXX)

CUSTOMERS = [
    # (Full Name,                Phone,       National ID)
    ("Nakato Sarah",             "077255977",  "CM920012345YDRE"),
    ("Wasswa John",              "077255978",  "CM930023456ABCD"),
    ("Namukasa Florence",        "077255979",  "CM890034567EFGH"),
    ("Ssemakula Robert",         "075255980",  "CM910045678IJKL"),
    ("Namusoke Grace",           "077255981",  "CM940056789MNOP"),
    ("Kato Emmanuel",            "075255982",  "CM900067890QRST"),
    ("Nalubega Harriet",         "076255983",  "CM950078901UVWX"),
    ("Mukasa David",             "077255984",  "CM880089012YZAB"),
    ("Namubiru Prossy",          "075255985",  "CM920090123CDEF"),
    ("Ssali Fred",               "077255986",  "CM910001234GHIJ"),
    ("Akello Mary",              "078255987",  "CM930012345KLMN"),
    ("Oryem Patrick",            "077255988",  "CM900023456OPQR"),
    ("Apio Immaculate",          "075255989",  "CM940034567STUV"),
    ("Okello Geoffrey",          "076255990",  "CM920045678WXYZ"),
    ("Achola Joyce",             "077255991",  "CM910056789ABCD"),
    ("Muwanga Alex",             "077255992",  "CM950067890EFGH"),
    ("Nakyagaba Agnes",          "075255993",  "CM890078901IJKL"),
    ("Kibuuka Moses",            "077255994",  "CM930089012MNOP"),
    ("Zawedde Phiona",           "076255995",  "CM900090123QRST"),
    ("Nsubuga Ivan",             "077255996",  "CM920001234UVWX"),
    ("Atim Christine",           "078255997",  "CM940012345YZAB"),
    ("Olweny Samuel",            "077255998",  "CM910023456CDEF"),
    ("Aber Sandra",              "075255999",  "CM950034567GHIJ"),
    ("Ojok Richard",             "077256000",  "CM900045678KLMN"),
    ("Adong Lillian",            "076256001",  "CM930056789OPQR"),
    ("Mugisha Peter",            "077256002",  "CM920067890STUV"),
    ("Tumuhimbise Rose",         "075256003",  "CM910078901WXYZ"),
    ("Kabagambe Joseph",         "077256004",  "CM940089012ABCD"),
    ("Kobusingye Judith",        "078256005",  "CM890090123EFGH"),
    ("Rwaheru Daniel",           "077256006",  "CM930001234IJKL"),
    ("Asingwire Eunice",         "075256007",  "CM900012345MNOP"),
    ("Byaruhanga Isaac",         "076256008",  "CM920023456QRST"),
    ("Kamugisha Annet",          "077256009",  "CM910034567UVWX"),
    ("Tusiime Simon",            "077256010",  "CM950045678YZAB"),
    ("Birungi Consolata",        "075256011",  "CM900056789CDEF"),
    ("Muhindo Vincent",          "077256012",  "CM930067890GHIJ"),
    ("Kabugho Gertrude",         "076256013",  "CM920078901KLMN"),
    ("Masereka Julius",          "077256014",  "CM910089012OPQR"),
    ("Baluku Beatrice",          "078256015",  "CM940090123STUV"),
    ("Mukirane Stephen",         "077256016",  "CM890001234WXYZ"),
    ("Nabirye Irene",            "075256017",  "CM930012345ABCD"),
    ("Wanyama Brian",            "077256018",  "CM900023456EFGH"),
    ("Chemutai Jane",            "076256019",  "CM920034567IJKL"),
    ("Chepkoech David",          "077256020",  "CM910045678MNOP"),
    ("Ouma Lawrence",            "075256021",  "CM950056789QRST"),
    ("Aduku Patience",           "077256022",  "CM900067890UVWX"),
    ("Ocen Benard",              "077256023",  "CM930078901YZAB"),
    ("Awor Dorcus",              "076256024",  "CM920089012CDEF"),
    ("Mwaka Ruth",               "078256025",  "CM910090123GHIJ"),
    ("Kitimbo Gerald",           "077256026",  "CM940001234IJKL"),
]

# ── Loan parameters: (principal UGX, flat interest %, term months) ────────────
# Amounts intentionally vary to reflect a realistic microfinance portfolio.

LOAN_PARAMS = [
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

METHODS = ["MTN MoMo", "Airtel Money", "Bank Transfer", "Cash"]

# ── Main seed function ────────────────────────────────────────────────────────

def seed():
    conn = get_conn()

    # ── Guard: skip if already seeded ────────────────────────────────────────
    existing = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    if existing >= 50:
        print(f"⚠️  Database already has {existing} customers — skipping seed.")
        conn.close()
        return

    today = datetime.now().strftime('%Y-%m-%d')
    now   = datetime.now().strftime('%Y-%m-%d %H:%M')

    # ── Step 1: Insert 50 customers ──────────────────────────────────────────
    print("Inserting 50 customers …")
    customer_ids = []
    for name, phone, nid in CUSTOMERS:
        cur = conn.execute(
            "INSERT INTO customers (name, phone, national_id, created_at) VALUES (?,?,?,?)",
            (name, phone, nid, today)
        )
        customer_ids.append(cur.lastrowid)
    conn.commit()
    print(f"  ✅ {len(customer_ids)} customers added.")

    # ── Step 2: Issue one loan per customer ──────────────────────────────────
    print("Issuing 50 loans …")
    loans = []   # (loan_id, total_due, customer_id, customer_name)

    for i, cid in enumerate(customer_ids):
        principal, rate, term = LOAN_PARAMS[i]
        total_due = round(principal * (1 + rate / 100), 2)

        cur = conn.execute(
            """INSERT INTO loans
               (customer_id, principal, interest_rate, term_months,
                total_due, balance, status, disbursed_date)
               VALUES (?,?,?,?,?,?,?,?)""",
            (cid, principal, rate, term, total_due, total_due, 'Active', today)
        )
        lid = cur.lastrowid
        loans.append((lid, total_due, cid, CUSTOMERS[i][0]))

        # Ledger: disbursement
        post_double_entry(
            conn,
            "Loans Receivable", "Cash/Bank",
            principal,
            f"Loan #{lid} disbursed — {CUSTOMERS[i][0]}",
            f"LOAN-{lid}"
        )

    conn.commit()
    print(f"  ✅ {len(loans)} loans issued.")

    # ── Step 3: Record repayments for 35 of the 50 loans ────────────────────
    # Loans  0–9  → fully repaid (Closed)
    # Loans 10–24 → one partial payment (~50 % of total)
    # Loans 25–34 → two partial payments
    # Loans 35–49 → no payments yet (freshly disbursed)

    print("Recording repayments …")
    repayment_count = 0

    for idx, (lid, total_due, cid, cname) in enumerate(loans):
        method = METHODS[idx % len(METHODS)]

        if idx < 10:
            # ── Full repayment: loan closed ──────────────────────────────────
            amount = total_due
            ref    = f"MM-{secrets.token_hex(4).upper()}"
            conn.execute(
                "INSERT INTO repayments (loan_id, amount, method, reference, date) VALUES (?,?,?,?,?)",
                (lid, amount, method, ref, now)
            )
            conn.execute(
                "UPDATE loans SET balance = 0, status = 'Closed' WHERE id = ?", (lid,)
            )
            post_double_entry(
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
            repayment_count += 1

        elif idx < 25:
            # ── One partial payment (40–60 % of total due) ───────────────────
            frac   = round(random.uniform(0.40, 0.60), 2)
            amount = round(total_due * frac / 1000) * 1000   # round to nearest 1,000
            amount = max(amount, 50_000)
            new_bal = round(total_due - amount, 2)
            ref     = f"MM-{secrets.token_hex(4).upper()}"

            conn.execute(
                "INSERT INTO repayments (loan_id, amount, method, reference, date) VALUES (?,?,?,?,?)",
                (lid, amount, method, ref, now)
            )
            conn.execute(
                "UPDATE loans SET balance = ? WHERE id = ?", (new_bal, lid)
            )
            post_double_entry(
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
            repayment_count += 1

        elif idx < 35:
            # ── Two partial payments ─────────────────────────────────────────
            frac1    = round(random.uniform(0.25, 0.35), 2)
            amount1  = round(total_due * frac1 / 1000) * 1000
            amount1  = max(amount1, 50_000)
            bal_1    = round(total_due - amount1, 2)

            frac2    = round(random.uniform(0.20, 0.30), 2)
            amount2  = round(bal_1 * frac2 / 1000) * 1000
            amount2  = max(amount2, 50_000)
            bal_2    = round(bal_1 - amount2, 2)

            for amt, bal in [(amount1, bal_1), (amount2, bal_2)]:
                ref = f"MM-{secrets.token_hex(4).upper()}"
                conn.execute(
                    "INSERT INTO repayments (loan_id, amount, method, reference, date) VALUES (?,?,?,?,?)",
                    (lid, amt, method, ref, now)
                )
                post_double_entry(
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
                repayment_count += 1

            conn.execute(
                "UPDATE loans SET balance = ? WHERE id = ?", (bal_2, lid)
            )
        # else: loans 35–49 have no repayments (newly disbursed)

    conn.commit()
    conn.close()

    print(f"  ✅ {repayment_count} repayment transactions recorded.")
    print()
    print("══════════════════════════════════════════════════════════")
    print("  🎉  Seed complete!")
    print()
    print("  Portfolio summary:")
    print(f"    Customers    : {len(CUSTOMERS)}")
    print(f"    Loans issued : {len(loans)}")
    print(f"      ↳ Closed   : 10  (fully repaid)")
    print(f"      ↳ Active   : 40  (25 with partial payments, 15 fresh)")
    print(f"    Repayments   : {repayment_count}")
    print()
    print("  Launch Streamlit and log in with admin / admin123")
    print("══════════════════════════════════════════════════════════")


if __name__ == "__main__":
    seed()
