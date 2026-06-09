from pathlib import Path
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Customer Acquisition Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "calculations"
CAC_FILE = DATA_DIR / "cac.csv"
LTV_FILE = DATA_DIR / "ltv.csv"

CHART_TEMPLATE = "plotly_white"
CHART_MARGIN = dict(l=10, r=10, t=50, b=10)

COLORS = {
    "spend":   "#0f766e",
    "revenue": "#7c3aed",
    "cac":     "#f59e0b",
    "ltv":     "#6366f1",
    "profit":  "#22c55e",
    "loss":    "#ef4444",
    "neutral": "#64748b",
}

SEG_PALETTE = [
    "#6366f1", "#0ea5e9", "#22c55e", "#f59e0b",
    "#ef4444", "#a855f7", "#14b8a6", "#f97316",
]


# ── CSS ───────────────────────────────────────────────────────────────────────

def inject_css():
    st.markdown("""
    <style>
    .block-container { padding-top: 1.2rem; padding-bottom: 2rem; }
    [data-testid="stMetric"] {
        background: linear-gradient(160deg, rgba(15,23,42,0.94), rgba(30,41,59,0.90));
        border: 1px solid rgba(148,163,184,0.18);
        padding: 1rem 1.1rem;
        border-radius: 16px;
        box-shadow: 0 4px 18px rgba(0,0,0,0.15);
    }
    [data-testid="stMetricLabel"] { color: rgba(226,232,240,0.75); font-size: 0.82rem; }
    [data-testid="stMetricValue"] { color: #f8fafc; font-weight: 700; font-size: 1.35rem; }
    [data-testid="stMetricDelta"] { font-size: 0.8rem; }
    .status-bar {
        background: rgba(15,23,42,0.5);
        border: 1px solid rgba(148,163,184,0.15);
        border-radius: 10px;
        padding: 0.55rem 1rem;
        font-size: 0.85rem;
        color: #94a3b8;
        margin: 0.5rem 0 0.2rem;
    }
    .divider { border: none; border-top: 1px solid rgba(148,163,184,0.15); margin: 1.6rem 0 1rem; }
    </style>
    """, unsafe_allow_html=True)


# ── Data ──────────────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def load_data(cac_path, ltv_path):
    cac = pd.read_csv(cac_path)
    ltv = pd.read_csv(ltv_path)
    for df in (cac, ltv):
        for col in ["country", "platform", "ad_source", "campaign", "campaign_id"]:
            if col in df.columns:
                df[col] = df[col].replace("nan", pd.NA)
    for col in ["first_purchase_date", "last_purchase_date"]:
        for df in (cac, ltv):
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")
    for col in ["new_customers", "total_spend_usd", "cac_usd"]:
        if col in cac.columns:
            cac[col] = pd.to_numeric(cac[col], errors="coerce")
    for col in ["total_revenue", "purchase_count", "ltv_usd"]:
        if col in ltv.columns:
            ltv[col] = pd.to_numeric(ltv[col], errors="coerce")
    return cac, ltv


def normalize(df):
    out = df.copy()
    if "country" in out.columns:
        out["country"] = out["country"].astype(str).str.strip().str.upper()
        out["country"] = out["country"].replace({"<NA>": pd.NA, "NAN": pd.NA, "": pd.NA})
    return out


def apply_filters(cac, ltv, countries, platforms, sources):
    cf, lf = cac.copy(), ltv.copy()
    if countries:
        cf = cf[cf["country"].isin(countries)]
        lf = lf[lf["country"].isin(countries)]
    if platforms:
        cf = cf[cf["platform"].isin(platforms)]
        lf = lf[lf["platform"].isin(platforms)]
    if sources:
        cf = cf[cf["ad_source"].isin(sources)]
        lf = lf[lf["ad_source"].isin(sources)]
    return cf, lf


# ── Calculations ──────────────────────────────────────────────────────────────

def safe_div(a, b):
    return np.nan if (pd.isna(b) or b == 0) else a / b


def kpis(cf, lf):
    spend = cf["total_spend_usd"].sum()
    revenue = lf["total_revenue"].sum()
    customers = cf["new_customers"].sum()
    users = lf["user_id"].nunique() if "user_id" in lf.columns else customers
    cac = safe_div(spend, customers)
    ltv = safe_div(revenue, users or customers)
    return dict(
        spend=spend,
        revenue=revenue,
        customers=customers,
        cac=cac,
        ltv=ltv,
        ratio=safe_div(ltv, cac),
    )


def aggregate(cf, lf, dim):
    ca = (
        cf.groupby(dim, as_index=False)
        .agg(spend=("total_spend_usd", "sum"), customers=("new_customers", "sum"))
    )
    ca["cac"] = np.where(ca["customers"] > 0, ca["spend"] / ca["customers"], np.nan)
    la = (
        lf.groupby(dim, as_index=False)
        .agg(revenue=("total_revenue", "sum"), users=("user_id", "nunique"))
    )
    m = ca.merge(la, on=dim, how="outer")
    for col in ["spend", "customers", "revenue", "users"]:
        m[col] = pd.to_numeric(m.get(col, 0), errors="coerce").fillna(0)
    m["ltv"]   = np.where(m["users"] > 0, m["revenue"] / m["users"], np.nan)
    m["ratio"] = np.where(m["cac"] > 0, m["ltv"] / m["cac"], np.nan)
    m["gap"]   = m["ltv"] - m["cac"]
    m["roas"]  = np.where(m["spend"] > 0, m["revenue"] / m["spend"], np.nan)
    return m.sort_values("revenue", ascending=False)


def monthly_by_dim(cf, lf, dim, top_n=6):
    ok_c = "first_purchase_date" in cf.columns and not cf["first_purchase_date"].isna().all()
    ok_l = "first_purchase_date" in lf.columns and not lf["first_purchase_date"].isna().all()
    if not ok_c or not ok_l or dim not in cf.columns or dim not in lf.columns:
        return None
    sm = (
        cf.dropna(subset=["first_purchase_date", dim])
        .assign(month=lambda d: d["first_purchase_date"].dt.to_period("M").dt.to_timestamp())
        .groupby(["month", dim], as_index=False)
        .agg(spend=("total_spend_usd", "sum"), customers=("new_customers", "sum"))
    )
    rm = (
        lf.dropna(subset=["first_purchase_date", dim])
        .assign(month=lambda d: d["first_purchase_date"].dt.to_period("M").dt.to_timestamp())
        .groupby(["month", dim], as_index=False)
        .agg(revenue=("total_revenue", "sum"), users=("user_id", "nunique"))
    )
    m = sm.merge(rm, on=["month", dim], how="outer").fillna(0).sort_values("month")
    if len(m) < 2:
        return None
    top = m.groupby(dim)["revenue"].sum().nlargest(top_n).index
    m = m[m[dim].isin(top)]
    m["cac"] = np.where(m["customers"] > 0, m["spend"] / m["customers"], np.nan)
    m["ltv"] = np.where(m["users"] > 0, m["revenue"] / m["users"], np.nan)
    m["ratio"] = np.where(m["cac"] > 0, m["ltv"] / m["cac"], np.nan)
    return m


# ── Formatting ────────────────────────────────────────────────────────────────

def fmt(x, prefix="$", decimals=0):
    if pd.isna(x):
        return "—"
    if abs(x) >= 1_000_000:
        return f"{prefix}{x/1_000_000:.1f}M"
    if abs(x) >= 1_000:
        return f"{prefix}{x/1_000:.1f}K"
    return f"{prefix}{round(x)}" if decimals == 0 else f"{prefix}{x:.{decimals}f}"


def fmt_n(x):
    if pd.isna(x): return "—"
    if abs(x) >= 1_000_000: return f"{x/1_000_000:.1f}M"
    if abs(x) >= 1_000: return f"{x/1_000:.1f}K"
    return f"{int(round(x)):,}"


# ── Charts ────────────────────────────────────────────────────────────────────

def chart_cac_ltv(df, dim, label):
    """Grouped bar: CAC vs Avg LTV per segment."""
    d = df.dropna(subset=["cac", "ltv"]).head(12)
    fig = go.Figure()
    fig.add_bar(x=d[dim], y=d["cac"], name="CAC",     marker_color=COLORS["cac"],
                hovertemplate="<b>%{x}</b><br>CAC: $%{y:,.0f}<extra></extra>")
    fig.add_bar(x=d[dim], y=d["ltv"], name="Avg LTV", marker_color=COLORS["ltv"],
                hovertemplate="<b>%{x}</b><br>Avg LTV: $%{y:,.0f}<extra></extra>")
    fig.update_layout(
        barmode="group", template=CHART_TEMPLATE, height=380, margin=CHART_MARGIN,
        title=f"CAC vs Avg LTV — by {label}", title_font_size=16,
        legend=dict(orientation="h", y=1.08, x=1, xanchor="right"),
        yaxis=dict(tickprefix="$", separatethousands=True),
    )
    return fig


def chart_ratio(df, dim, label):
    """Horizontal bar: LTV:CAC ratio, color-coded."""
    d = df.dropna(subset=["ratio"]).sort_values("ratio", ascending=True).tail(12)
    colors = [COLORS["profit"] if v >= 3 else COLORS["cac"] if v >= 1 else COLORS["loss"]
              for v in d["ratio"]]
    fig = go.Figure(go.Bar(
        x=d["ratio"], y=d[dim], orientation="h",
        marker_color=colors,
        text=d["ratio"].apply(lambda v: f"{v:.1f}x" if pd.notna(v) else ""),
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>LTV:CAC: %{x:.2f}x<extra></extra>",
    ))
    fig.add_vline(x=1, line_dash="dash",  line_color=COLORS["loss"],    annotation_text="1x")
    fig.add_vline(x=3, line_dash="dot",   line_color=COLORS["profit"],  annotation_text="3x target")
    fig.update_layout(
        template=CHART_TEMPLATE, height=380, margin=CHART_MARGIN,
        title=f"LTV:CAC Ratio — by {label}", title_font_size=16,
        xaxis_title="LTV:CAC",
    )
    return fig


def chart_trend(md, dim, label):
    """Multi-line: monthly CAC and LTV per top segments."""
    fig = go.Figure()
    segments = md[dim].unique()
    for i, seg in enumerate(segments):
        sub = md[md[dim] == seg].sort_values("month")
        c = SEG_PALETTE[i % len(SEG_PALETTE)]
        fig.add_trace(go.Scatter(
            x=sub["month"], y=sub["cac"], name=f"{seg} — CAC",
            mode="lines+markers", line=dict(color=c, width=2, dash="dot"),
            hovertemplate=f"<b>{seg}</b> CAC: $%{{y:,.0f}}<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=sub["month"], y=sub["ltv"], name=f"{seg} — LTV",
            mode="lines+markers", line=dict(color=c, width=2),
            hovertemplate=f"<b>{seg}</b> LTV: $%{{y:,.0f}}<extra></extra>",
        ))
    fig.update_layout(
        template=CHART_TEMPLATE, height=400, margin=CHART_MARGIN,
        title=f"CAC & LTV Over Time — by {label}", title_font_size=16,
        hovermode="x unified",
        yaxis=dict(tickprefix="$", separatethousands=True),
        legend=dict(orientation="h", y=-0.22, x=0),
    )
    return fig


def chart_ratio_trend(md, dim, label):
    """Multi-line: monthly LTV:CAC ratio per top segments."""
    fig = go.Figure()
    segments = md[dim].unique()
    for i, seg in enumerate(segments):
        sub = md[md[dim] == seg].sort_values("month")
        fig.add_trace(go.Scatter(
            x=sub["month"], y=sub["ratio"], name=str(seg),
            mode="lines+markers", line=dict(color=SEG_PALETTE[i % len(SEG_PALETTE)], width=2),
            hovertemplate=f"<b>{seg}</b>: %{{y:.2f}}x<extra></extra>",
        ))
    fig.add_hline(y=3, line_dash="dot",  line_color=COLORS["profit"], annotation_text="Target 3x")
    fig.add_hline(y=1, line_dash="dash", line_color=COLORS["loss"],   annotation_text="Break-even")
    fig.update_layout(
        template=CHART_TEMPLATE, height=400, margin=CHART_MARGIN,
        title=f"LTV:CAC Ratio Over Time — by {label}", title_font_size=16,
        hovermode="x unified",
        legend=dict(orientation="h", y=-0.22, x=0),
    )
    return fig


# ── KPI row ───────────────────────────────────────────────────────────────────

def render_kpis(k):
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Total Spend",    fmt(k["spend"]))
    c2.metric("Total Revenue",  fmt(k["revenue"]))
    c3.metric("New Customers",  fmt_n(k["customers"]))
    c4.metric("Overall CAC",    fmt(k["cac"]))
    c5.metric("Avg LTV",        fmt(k["ltv"]))
    c6.metric("LTV:CAC",
              f"{k['ratio']:.1f}x" if pd.notna(k["ratio"]) else "—")

    ratio = k["ratio"]
    if pd.notna(ratio):
        if ratio >= 3:
            badge, note = "🟢", f"Healthy — every $1 spent acquires ${ratio:.1f} in lifetime value"
        elif ratio >= 1:
            badge, note = "🟡", f"Marginal — LTV covers CAC but leaves thin margin"
        else:
            badge, note = "🔴", f"Unprofitable — CAC exceeds customer lifetime value"
    else:
        badge, note = "⚪", "Insufficient data"

    st.markdown(
        f'<div class="status-bar">{badge} &nbsp;{note}</div>',
        unsafe_allow_html=True,
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    inject_css()
    st.title("📈 Customer Acquisition Dashboard")
    st.caption("CAC vs LTV efficiency across ad sources, platforms, and countries.")

    if not CAC_FILE.exists() or not LTV_FILE.exists():
        st.error(f"Missing data files.\nExpected:\n- {CAC_FILE}\n- {LTV_FILE}")
        st.stop()

    cac, ltv = load_data(CAC_FILE, LTV_FILE)
    cac, ltv = normalize(cac), normalize(ltv)

    all_countries = sorted(set(cac["country"].dropna()) | set(ltv["country"].dropna()))
    all_platforms = sorted(set(cac["platform"].dropna()) | set(ltv["platform"].dropna()))
    all_sources   = sorted(set(cac["ad_source"].dropna()) | set(ltv["ad_source"].dropna()))

    # Sidebar filters
    st.sidebar.header("Filters")
    with st.sidebar.form("filters"):
        sel_countries = st.multiselect("Country",   all_countries, default=all_countries)
        sel_platforms = st.multiselect("Platform",  all_platforms, default=all_platforms)
        sel_sources   = st.multiselect("Ad source", all_sources,   default=all_sources)
        st.form_submit_button("Apply", use_container_width=True)

    cf, lf = apply_filters(cac, ltv, sel_countries, sel_platforms, sel_sources)
    k = kpis(cf, lf)

    # ── KPIs ──────────────────────────────────────────────────────────────────
    render_kpis(k)

    # ── Breakdown ─────────────────────────────────────────────────────────────
    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    DIMS = {"Ad Source": "ad_source", "Platform": "platform", "Country": "country"}
    dim_label = st.radio("Break down by", list(DIMS.keys()), horizontal=True)
    dim = DIMS[dim_label]
    df = aggregate(cf, lf, dim)

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(chart_cac_ltv(df, dim, dim_label), use_container_width=True)
    with col2:
        st.plotly_chart(chart_ratio(df, dim, dim_label), use_container_width=True)

    # ── Trends ────────────────────────────────────────────────────────────────
    md = monthly_by_dim(cf, lf, dim, top_n=6)
    if md is not None:
        st.markdown('<hr class="divider">', unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(chart_trend(md, dim, dim_label), use_container_width=True)
        with col2:
            st.plotly_chart(chart_ratio_trend(md, dim, dim_label), use_container_width=True)

    # ── Table ─────────────────────────────────────────────────────────────────
    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    display = df[[dim, "customers", "spend", "cac", "revenue", "ltv", "ratio", "gap", "roas"]].copy()
    display.columns = [dim_label, "Customers", "Spend ($)", "CAC ($)", "Revenue ($)", "Avg LTV ($)", "LTV:CAC", "LTV−CAC ($)", "ROAS"]
    for col in ["Spend ($)", "CAC ($)", "Revenue ($)", "Avg LTV ($)", "LTV−CAC ($)"]:
        display[col] = display[col].round(0)
    for col in ["LTV:CAC", "ROAS"]:
        display[col] = display[col].round(2)

    st.dataframe(
        display.style.background_gradient(subset=["LTV:CAC"], cmap="RdYlGn", vmin=0, vmax=5),
        use_container_width=True, hide_index=True,
    )

    csv = display.to_csv(index=False).encode("utf-8")
    st.download_button(
        f"Download {dim_label} breakdown",
        data=csv,
        file_name=f"cac_ltv_{dim}.csv",
        mime="text/csv",
    )


if __name__ == "__main__":
    main()