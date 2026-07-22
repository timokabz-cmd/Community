import streamlit as st
from database import get_db_connection
from modules.nssf_engine import get_leaderboard, get_points_balance, get_tier, TIERS, POINTS

GOLD = "#C99A3B"; INK = "#1A1A2E"; INK_TEXT = "#1A1A2E"
PAPER_DIM = "#F5F0E8"; LINE = "#DDD5C4"

TIER_META = {
    "🏆 National Builder": {"color":"#C99A3B","bg":"#FDF6E3","border":"#C99A3B","desc":"An exceptional patriot. Consistently saving and building Uganda's future.","min":600},
    "🥇 Gold Champion":    {"color":"#A4732B","bg":"#F9F0DC","border":"#C99A3B","desc":"A proven saver. NSSF contributions are growing Uganda's social safety net.","min":300},
    "🥈 Silver Patriot":   {"color":"#5C748A","bg":"#EDF1F5","border":"#7C9AB5","desc":"Building momentum. Each deposit brings this member closer to Gold.","min":100},
    "🥉 Bronze Saver":     {"color":"#7C6A4F","bg":"#F3EDE0","border":"#B8A07A","desc":"Just getting started. Every shilling saved is a brick for Uganda.","min":0},
}

def _member_card_html(rank, name, points, tier):
    meta         = TIER_META.get(tier, TIER_META["🥉 Bronze Saver"])
    rank_display = ["🥇","🥈","🥉"][rank-1] if rank <= 3 else f"#{rank}"
    return f"""
    <div style="background:{meta['bg']};border:1.5px solid {meta['border']};border-radius:8px;
                padding:0.75rem 1rem;margin-bottom:0.6rem;display:flex;
                align-items:center;justify-content:space-between;">
      <div style="display:flex;align-items:center;gap:0.8rem;">
        <span style="font-size:1.4rem;">{rank_display}</span>
        <div>
          <div style="font-weight:600;color:{INK_TEXT};font-size:0.95rem;">{name}</div>
          <div style="font-size:0.75rem;color:{meta['color']};margin-top:2px;">{tier}</div>
        </div>
      </div>
      <div style="font-weight:700;color:{GOLD};font-size:1.1rem;font-variant-numeric:tabular-nums;">
        {points:,} pts
      </div>
    </div>"""

def _progress_bar_html(points, next_threshold, color=GOLD):
    pct = min(int(points/next_threshold*100), 100) if next_threshold > 0 else 100
    return f"""
    <div style="background:{LINE};border-radius:4px;height:8px;width:100%;margin-top:4px;">
      <div style="background:{color};border-radius:4px;height:8px;width:{pct}%;"></div>
    </div>
    <div style="font-size:0.72rem;color:#7C8A99;margin-top:3px;">{pct}% to next tier</div>"""

def render():
    sacco_id = st.session_state.get('current_sacco_id')
    if sacco_id is None:
        st.warning("No SACCO selected.")
        return

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#1A1A2E 0%,#2A4F82 100%);border-radius:12px;
                padding:1.4rem 1.8rem;margin-bottom:1.4rem;border-left:5px solid {GOLD};">
      <div style="color:{GOLD};font-size:0.78rem;letter-spacing:0.1em;text-transform:uppercase;font-weight:600;">
        🇺🇬 Uganda National Savings Programme
      </div>
      <div style="color:#FFFFFF;font-size:1.45rem;font-weight:700;margin:0.3rem 0 0.2rem;line-height:1.3;">
        Save with your SACCO.<br>Build with Uganda.
      </div>
      <div style="color:#B8CCDF;font-size:0.88rem;margin-top:0.4rem;">
        Every shilling saved in your SACCO, a piece goes to build the nation.<br>
        Earn Gold Points for every NSSF contribution — climb from Bronze Saver to National Builder.
      </div>
    </div>""", unsafe_allow_html=True)

    with st.expander("🏅 How Gold Points work", expanded=False):
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("**Earn points by:**")
            labels = {
                "nssf_enrolled":"Joining NSSF-registered","monthly_contribution":"Monthly NSSF contribution",
                "above_default_rate":"Saving above 5% default rate","streak_3_months":"3-month saving streak",
                "streak_6_months":"6-month streak (Patriot Badge)","referral":"Referring a new NSSF-registered member",
            }
            for key, pts in POINTS.items():
                st.markdown(f"• {labels.get(key,key)} — **{pts} pts**")
        with col_b:
            st.markdown("**Tier thresholds:**")
            for tier_name, meta in TIER_META.items():
                st.markdown(f"{tier_name} — **{meta['min']}+ pts**")
                st.caption(meta['desc'])

    st.divider()
    st.markdown("#### 🏆 SACCO Leaderboard")
    leaderboard = get_leaderboard(sacco_id, limit=10)
    if not leaderboard:
        st.info("No members yet. Enroll members and start recording deposits to see the leaderboard.")
        return

    for rank, row in enumerate(leaderboard, start=1):
        member_id = row['id']; name = row['name']; points = int(row['total_points'])
        tier = get_tier(points)
        st.markdown(_member_card_html(rank, name, points, tier), unsafe_allow_html=True)

    st.divider()
    st.markdown("#### 🔍 Member Points Detail")
    conn = get_db_connection()
    cur  = conn.cursor()
    cur.execute("SELECT id, name, phone FROM customers WHERE sacco_id = %s ORDER BY name", (sacco_id,))
    members = cur.fetchall()
    cur.close()
    conn.close()
    if not members:
        return

    member_map = {f"{m['name']} ({m['phone']})": m['id'] for m in members}
    choice     = st.selectbox("Select a member", list(member_map.keys()))
    cid        = member_map[choice]
    points     = get_points_balance(cid)
    tier       = get_tier(points)
    meta       = TIER_META.get(tier, TIER_META["🥉 Bronze Saver"])

    next_thresh = 0
    for threshold, label in reversed(TIERS):
        if points < threshold:
            next_thresh = threshold

    col1, col2, col3 = st.columns(3)
    col1.metric("Gold Points",     f"{points:,}")
    col2.metric("Current Tier",    tier)
    col3.metric("Points to Next",  f"{max(next_thresh-points,0):,}" if next_thresh > points else "Max tier 🏆")

    if next_thresh > points:
        st.markdown(_progress_bar_html(points, next_thresh, meta['color']), unsafe_allow_html=True)
    st.caption(meta['desc'])

    conn = get_db_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT reason, points, created_at FROM gold_points_ledger
        WHERE customer_id = %s ORDER BY created_at DESC LIMIT 20
    """, (cid,))
    history = cur.fetchall()
    cur.close()
    conn.close()

    if history:
        st.markdown("**Points history (last 20 events):**")
        reason_labels = {
            "nssf_enrolled":"🇺🇬 Joined NSSF-registered","monthly_contribution":"💰 Monthly NSSF contribution",
            "above_default_rate":"⬆️ Above-default rate","streak_3_months":"🔥 3-month streak",
            "streak_6_months":"🔥🔥 6-month Patriot streak","referral":"🤝 Referral bonus",
        }
        st.dataframe(
            [{"Date": h['created_at'], "Reason": reason_labels.get(h['reason'], h['reason']),
              "Points": f"+{h['points']}"} for h in history],
            use_container_width=True, hide_index=True
        )
