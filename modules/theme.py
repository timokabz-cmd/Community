"""
Visual identity for CommunityFinanceOS.

Design concept: the SACCO passbook. Every member-owned savings group in
Uganda runs on a physical booklet, hand-stamped at every deposit — it's the
actual artifact of trust in this world, more than any banking-app cliche.
This theme borrows that vocabulary: ledger-ink indigo, a stamped-gold accent,
a warm paper backdrop instead of clinical white, tabular monospace for money
so figures actually align in a column, and a literal rubber-stamp badge for
status tags (Active / Overdue / High Risk, etc).

Two-part split, because Streamlit's [theme] in config.toml only reaches
native widgets (buttons, inputs, the sidebar shell, dataframes). Anything
bespoke — the header band, the stamp badges, the sidebar wordmark — needs
real CSS, injected once per page via inject_css() below.

WHERE THIS PLUGS IN:
- .streamlit/config.toml  -> base color/font theme (ships with the repo, no code needed)
- modules/theme.py (this file) -> inject_css() + the two layout helpers below
- app.py -> calls inject_css() once at the top, and render_brand_header()
  inside the sidebar, right under st.sidebar.title(...)
"""

import streamlit as st

INK = "#1B3358"        # deep ledger indigo — headers, sidebar
INK_SOFT = "#234070"   # lighter indigo — sidebar hover/active state
GOLD = "#C99A3B"       # stamped gold — primary accent, used sparingly
PAPER = "#FAF6EE"      # warm paper background (not stark white)
PAPER_DIM = "#F1E9D8"  # card / secondary surface
INK_TEXT = "#2B2823"   # body text — warm near-black, not pure #000
LINE = "#D9CDB0"       # hairline borders on paper surfaces
CREAM_TEXT = "#F3EFE3" # text on indigo surfaces

STATUS_COLORS = {
    "active":   ("#3F7A4D", "#E4EFE3"),  # (ink, soft background) — green family
    "closed":   ("#5C5747", "#EDE7D8"),  # neutral stone — done and filed away
    "low":      ("#3F7A4D", "#E4EFE3"),
    "medium":   ("#A4732B", "#F6E9CE"),
    "high":     ("#B0492E", "#F6DCD3"),
    "overdue":  ("#B0492E", "#F6DCD3"),
    "pending":  ("#7C8A99", "#E9EDF0"),
}


def inject_css():
    """Call once near the top of app.py, after st.set_page_config()."""
    st.markdown(f"""
    <style>
    /* Tabular numerals for anything money-shaped: st.metric, dataframes, st.code —
       so digits line up in a column instead of a serif font's proportional widths. */
    [data-testid="stMetricValue"], [data-testid="stDataFrame"], code {{
        font-variant-numeric: tabular-nums;
    }}

    /* Sidebar wordmark block — see render_brand_header() below, this styles it */
    .cfos-brand {{
        padding: 0.9rem 0.6rem 1.1rem 0.6rem;
        border-bottom: 1px solid {INK_SOFT};
        margin-bottom: 0.75rem;
    }}
    .cfos-brand-mark {{
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 2.1rem;
        height: 2.1rem;
        border-radius: 0.5rem;
        background: {GOLD};
        color: {INK};
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 700;
        font-size: 1.05rem;
        margin-right: 0.6rem;
        flex-shrink: 0;
    }}
    .cfos-brand-row {{
        display: flex;
        align-items: center;
    }}
    .cfos-brand-name {{
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 600;
        font-size: 1.05rem;
        color: {CREAM_TEXT};
        line-height: 1.15;
    }}
    .cfos-brand-sub {{
        font-size: 0.74rem;
        color: {GOLD};
        letter-spacing: 0.06em;
        text-transform: uppercase;
        margin-top: 0.1rem;
    }}

    /* Page header band — see render_page_header() below */
    .cfos-header {{
        display: flex;
        align-items: baseline;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 0.5rem 1.2rem;
        padding-bottom: 0.6rem;
        margin-bottom: 1.1rem;
        border-bottom: 2px solid {INK};
    }}
    .cfos-header-title {{
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 600;
        font-size: 1.7rem;
        color: {INK};
        margin: 0;
    }}
    .cfos-header-meta {{
        font-family: 'IBM Plex Mono', monospace;
        font-size: 0.8rem;
        color: #7C8A99;
        white-space: nowrap;
    }}

    /* Stamp badge — a rotated-rubber-stamp look for status text.
       Use via status_badge_html() rather than writing the markup by hand. */
    .cfos-stamp {{
        display: inline-block;
        font-family: 'Space Grotesk', sans-serif;
        font-weight: 600;
        font-size: 0.72rem;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        padding: 0.18rem 0.6rem;
        border-radius: 0.3rem;
        border: 1.5px solid currentColor;
    }}

    /* Section dividers a touch warmer than Streamlit's default gray hairline */
    hr {{ border-color: {LINE} !important; }}
    </style>
    """, unsafe_allow_html=True)


def render_brand_header():
    """Sidebar wordmark. Call right under st.sidebar.title(), or instead of it."""
    st.sidebar.markdown(f"""
    <div class="cfos-brand">
      <div class="cfos-brand-row">
        <div class="cfos-brand-mark">CF</div>
        <div>
          <div class="cfos-brand-name">CommunityFinanceOS</div>
          <div class="cfos-brand-sub">SACCO Operations</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)


def render_page_header(title, sacco_name=None):
    """Replaces a bare st.header(choice) call with a ruled header band that
    also shows which SACCO you're currently looking at, so it's never
    ambiguous which book you're working in."""
    meta = f"📘 {sacco_name}" if sacco_name else ""
    st.markdown(f"""
    <div class="cfos-header">
      <h1 class="cfos-header-title">{title}</h1>
      <div class="cfos-header-meta">{meta}</div>
    </div>
    """, unsafe_allow_html=True)


def status_badge_html(label, kind="pending"):
    """Returns the HTML string for one stamp badge. Pass to st.markdown(..., unsafe_allow_html=True).
    kind is matched case-insensitively against STATUS_COLORS; unknown kinds fall back to neutral."""
    ink, bg = STATUS_COLORS.get(kind.lower(), STATUS_COLORS["pending"])
    return f'<span class="cfos-stamp" style="color:{ink}; background:{bg};">{label}</span>'


def money_column(label=None):
    """Column config for st.dataframe that displays comma-separated thousands
    (e.g. 1,824,000) while keeping the value numeric — unlike converting to a
    formatted string, this keeps click-to-sort in the dataframe UI correct
    (numeric order, not alphabetical order on the formatted text)."""
    return st.column_config.NumberColumn(label=label, format="%,d")
