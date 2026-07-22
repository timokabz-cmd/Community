"""
modules/nssf_engine.py
Pure business logic for NSSF contributions and Gold Points.
No Streamlit imports — clean and testable.
PostgreSQL version: uses %s placeholders via psycopg2.
"""
from database import get_db_connection
from datetime import datetime

POINTS = {
    "nssf_enrolled":        50,
    "monthly_contribution": 10,
    "above_default_rate":   10,
    "streak_3_months":      30,
    "streak_6_months":      75,
    "referral":             25,
}

TIERS = [
    (600, "🏆 National Builder"),
    (300, "🥇 Gold Champion"),
    (100, "🥈 Silver Patriot"),
    (0,   "🥉 Bronze Saver"),
]

def get_tier(points: int) -> str:
    for threshold, label in TIERS:
        if points >= threshold:
            return label
    return "🥉 Bronze Saver"

def award_points(customer_id: int, sacco_id: int, reason_key: str, conn=None):
    points = POINTS.get(reason_key, 0)
    if points == 0:
        return
    close = False
    if conn is None:
        conn  = get_db_connection()
        close = True
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO gold_points_ledger (customer_id, sacco_id, points, reason) VALUES (%s,%s,%s,%s)",
        (customer_id, sacco_id, points, reason_key)
    )
    conn.commit()
    cur.close()
    if close:
        conn.close()

def get_points_balance(customer_id: int) -> int:
    conn = get_db_connection()
    cur  = conn.cursor()
    cur.execute(
        "SELECT COALESCE(SUM(points), 0) FROM gold_points_ledger WHERE customer_id = %s",
        (customer_id,)
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return int(list(row.values())[0]) if row else 0

def get_leaderboard(sacco_id: int, limit: int = 10):
    conn = get_db_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT c.id, c.name, COALESCE(SUM(g.points), 0) AS total_points
        FROM customers c
        LEFT JOIN gold_points_ledger g ON g.customer_id = c.id
        WHERE c.sacco_id = %s
        GROUP BY c.id, c.name
        ORDER BY total_points DESC
        LIMIT %s
    """, (sacco_id, limit))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def record_nssf_contribution(customer_id, sacco_id, gross_deposit, rate, savings_transaction_id=None):
    nssf_amount  = round(gross_deposit * (rate / 100), 2)
    net_to_sacco = round(gross_deposit - nssf_amount, 2)
    period       = datetime.now().strftime("%Y-%m")

    conn = get_db_connection()
    cur  = conn.cursor()
    cur.execute("""
        INSERT INTO nssf_contributions
            (customer_id, sacco_id, savings_transaction_id,
             gross_deposit, nssf_amount, net_to_sacco, contribution_rate, period)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
    """, (customer_id, sacco_id, savings_transaction_id,
          gross_deposit, nssf_amount, net_to_sacco, rate, period))
    conn.commit()

    award_points(customer_id, sacco_id, "monthly_contribution", conn=conn)
    if rate > 5.0:
        award_points(customer_id, sacco_id, "above_default_rate", conn=conn)
    _check_and_award_streak(customer_id, sacco_id, conn)

    cur.close()
    conn.close()
    return nssf_amount, net_to_sacco

def _check_and_award_streak(customer_id: int, sacco_id: int, conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT period FROM nssf_contributions
        WHERE customer_id = %s AND sacco_id = %s
        ORDER BY period DESC LIMIT 6
    """, (customer_id, sacco_id))
    periods = [r['period'] for r in cur.fetchall()]
    if len(periods) >= 6:
        cur.execute("""
            SELECT id FROM gold_points_ledger
            WHERE customer_id = %s AND reason = 'streak_6_months'
              AND TO_CHAR(created_at::timestamp, 'YYYY-MM') = %s
        """, (customer_id, periods[0]))
        if not cur.fetchone():
            award_points(customer_id, sacco_id, "streak_6_months", conn=conn)
    elif len(periods) >= 3:
        cur.execute("""
            SELECT id FROM gold_points_ledger
            WHERE customer_id = %s AND reason = 'streak_3_months'
              AND TO_CHAR(created_at::timestamp, 'YYYY-MM') = %s
        """, (customer_id, periods[0]))
        if not cur.fetchone():
            award_points(customer_id, sacco_id, "streak_3_months", conn=conn)
    cur.close()

def get_nssf_summary(sacco_id: int):
    conn = get_db_connection()
    cur  = conn.cursor()
    cur.execute("SELECT COUNT(*) AS c FROM customers WHERE sacco_id = %s", (sacco_id,))
    total_members = list(cur.fetchone().values())[0]
    cur.execute("SELECT COUNT(*) AS c FROM customers WHERE sacco_id = %s AND nssf_registered = 1", (sacco_id,))
    nssf_registered = list(cur.fetchone().values())[0]
    cur.execute("SELECT COALESCE(SUM(nssf_amount),0) AS s FROM nssf_contributions WHERE sacco_id = %s AND remitted = 0", (sacco_id,))
    unremitted = list(cur.fetchone().values())[0]
    cur.execute("SELECT COALESCE(SUM(nssf_amount),0) AS s FROM nssf_contributions WHERE sacco_id = %s", (sacco_id,))
    total_contributed = list(cur.fetchone().values())[0]
    cur.close()
    conn.close()
    return {
        "total_members":        total_members,
        "nssf_registered":      nssf_registered,
        "compliance_pct":       round((nssf_registered / total_members * 100), 1) if total_members else 0,
        "unremitted_ugx":       unremitted,
        "total_contributed_ugx":total_contributed,
    }
