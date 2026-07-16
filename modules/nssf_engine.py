# modules/nssf_engine.py
# ─────────────────────────────────────────────────────────────
# Pure business logic for NSSF contributions and Gold Points.
# No Streamlit imports here — keep it clean and testable.
# ─────────────────────────────────────────────────────────────

from database import get_db_connection
from datetime import datetime

# ── Gold Points config ────────────────────────────────────────
POINTS = {
    "nssf_enrolled":        50,   # one-time on registration
    "monthly_contribution": 10,   # each month a contribution is made
    "above_default_rate":   10,   # bonus if rate > 5%
    "streak_3_months":      30,   # 3 consecutive months
    "streak_6_months":      75,   # 6 consecutive months (Patriot Badge)
    "referral":             25,   # brings in a new NSSF-registered member
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


# ── Points ────────────────────────────────────────────────────
def award_points(customer_id: int, sacco_id: int, reason_key: str, conn=None):
    """Award points for a named reason. Uses POINTS dict for amounts."""
    points = POINTS.get(reason_key, 0)
    if points == 0:
        return
    close = False
    if conn is None:
        conn = get_db_connection()
        close = True
    conn.execute(
        "INSERT INTO gold_points_ledger (customer_id, sacco_id, points, reason) VALUES (?,?,?,?)",
        (customer_id, sacco_id, points, reason_key)
    )
    conn.commit()
    if close:
        conn.close()


def get_points_balance(customer_id: int) -> int:
    conn = get_db_connection()
    row = conn.execute(
        "SELECT COALESCE(SUM(points), 0) FROM gold_points_ledger WHERE customer_id = ?",
        (customer_id,)
    ).fetchone()
    conn.close()
    return int(row[0]) if row else 0


def get_leaderboard(sacco_id: int, limit: int = 10):
    """Top savers by gold points within a SACCO."""
    conn = get_db_connection()
    rows = conn.execute("""
        SELECT c.id, c.name, COALESCE(SUM(g.points), 0) AS total_points
        FROM customers c
        LEFT JOIN gold_points_ledger g ON g.customer_id = c.id
        WHERE c.sacco_id = ?
        GROUP BY c.id
        ORDER BY total_points DESC
        LIMIT ?
    """, (sacco_id, limit)).fetchall()
    conn.close()
    return rows


# ── NSSF Contributions ────────────────────────────────────────
def record_nssf_contribution(
    customer_id: int,
    sacco_id: int,
    gross_deposit: float,
    rate: float,
    savings_transaction_id: int = None
):
    """
    Split a deposit: calculate NSSF portion, record it, award points.
    Returns (nssf_amount, net_to_sacco).
    """
    nssf_amount = round(gross_deposit * (rate / 100), 2)
    net_to_sacco = round(gross_deposit - nssf_amount, 2)
    period = datetime.now().strftime("%Y-%m")

    conn = get_db_connection()

    conn.execute("""
        INSERT INTO nssf_contributions
            (customer_id, sacco_id, savings_transaction_id,
             gross_deposit, nssf_amount, net_to_sacco,
             contribution_rate, period)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (customer_id, sacco_id, savings_transaction_id,
          gross_deposit, nssf_amount, net_to_sacco, rate, period))

    conn.commit()

    # Award gold points for this month's contribution
    award_points(customer_id, sacco_id, "monthly_contribution", conn=conn)

    # Bonus if saving above the default 5% rate
    if rate > 5.0:
        award_points(customer_id, sacco_id, "above_default_rate", conn=conn)

    # Check for streaks (3 and 6 consecutive months)
    _check_and_award_streak(customer_id, sacco_id, conn)

    conn.close()
    return nssf_amount, net_to_sacco


def _check_and_award_streak(customer_id: int, sacco_id: int, conn):
    """Check if the member has a 3 or 6 month contribution streak."""
    rows = conn.execute("""
        SELECT DISTINCT period FROM nssf_contributions
        WHERE customer_id = ? AND sacco_id = ?
        ORDER BY period DESC
        LIMIT 6
    """, (customer_id, sacco_id)).fetchall()

    periods = [r[0] for r in rows]

    # Check if streak already awarded to avoid double-awarding
    if len(periods) >= 6:
        already = conn.execute("""
            SELECT id FROM gold_points_ledger
            WHERE customer_id = ? AND reason = 'streak_6_months'
            AND strftime('%Y-%m', created_at) = ?
        """, (customer_id, periods[0])).fetchone()
        if not already:
            award_points(customer_id, sacco_id, "streak_6_months", conn=conn)

    elif len(periods) >= 3:
        already = conn.execute("""
            SELECT id FROM gold_points_ledger
            WHERE customer_id = ? AND reason = 'streak_3_months'
            AND strftime('%Y-%m', created_at) = ?
        """, (customer_id, periods[0])).fetchone()
        if not already:
            award_points(customer_id, sacco_id, "streak_3_months", conn=conn)


def get_nssf_summary(sacco_id: int):
    """For the admin dashboard: total contributions, unremitted amount, member compliance."""
    conn = get_db_connection()

    total_members = conn.execute(
        "SELECT COUNT(*) FROM customers WHERE sacco_id = ?", (sacco_id,)
    ).fetchone()[0]

    nssf_registered = conn.execute(
        "SELECT COUNT(*) FROM customers WHERE sacco_id = ? AND nssf_registered = 1", (sacco_id,)
    ).fetchone()[0]

    unremitted = conn.execute("""
        SELECT COALESCE(SUM(nssf_amount), 0)
        FROM nssf_contributions
        WHERE sacco_id = ? AND remitted = 0
    """, (sacco_id,)).fetchone()[0]

    total_contributed = conn.execute("""
        SELECT COALESCE(SUM(nssf_amount), 0)
        FROM nssf_contributions
        WHERE sacco_id = ?
    """, (sacco_id,)).fetchone()[0]

    conn.close()
    return {
        "total_members": total_members,
        "nssf_registered": nssf_registered,
        "compliance_pct": round((nssf_registered / total_members * 100), 1) if total_members else 0,
        "unremitted_ugx": unremitted,
        "total_contributed_ugx": total_contributed,
  }
