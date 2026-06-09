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

TEMPLATE = "plotly_white"
MARGIN   = dict(l=10, r=10, t=50, b=10)
PALETTE  = ["#6366f1", "#0ea5e9", "#22c55e", "#f59e0b", "#ef4444",
            "#a855f7", "#14b8a6", "#f97316", "#ec4899", "#84cc16"]


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
    .status-bar {
        background: rgba(15,23,42,0.5);
        border: 1px solid rgba(148,163,184,0.15);
        border-radius: 10px;
        padding: 0.55rem 1rem;
        font-size: 0.85rem;
        color: #94a3b8;
        margin: 0.5rem 0 1.2rem;
    }
    .divider { border: none; border-top: 1px solid rgba(148,163,184,0.15); margin: 1.4rem 0 1rem; }
    </style>
    """, unsafe_allow_html=True)


# ── Data ──────────────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def load_data(cac_path, ltv_path):
    cac = pd.read_csv(cac_path)
    ltv = pd.read_csv(ltv_path)
    for df in (cac, ltv):
        for col in ["country", "platform", "ad_source"]:
            if col in df.columns:
                df[col] = df[col].replace("nan", pd.NA)
    for col in ["first_purchase_date", "last_purchase_date"]:
        for df in (cac, ltv):
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")
    if "purchase_date" in ltv.columns:
        ltv["purchase_date"] = pd.to_datetime(ltv["purchase_date"], errors="coerce")
    for col in ["new_customers", "total_spend_usd"]:
        if col in cac.columns:
            cac[col] = pd.to_numeric(cac[col], errors="coerce")
    # support both pre-aggregated (total_revenue) and raw (purchase_amount)
    for col in ["total_revenue", "purchase_amount"]:
        if col in ltv.columns:
            ltv[col] = pd.to_numeric(ltv[col], errors="coerce")
    # normalise: always expose a "revenue" column on ltv
    if "total_revenue" not in ltv.columns and "purchase_amount" in ltv.columns:
        ltv["total_revenue"] = ltv["purchase_amount"]
    # normalise: use purchase_date as first_purchase_date if missing
    if "first_purchase_date" not in ltv.columns and "purchase_date" in ltv.columns:
        ltv["first_purchase_date"] = ltv["purchase_date"]
    return cac, ltv


def normalize(df):
    if "country" in df.columns:
        df = df.copy()
        df["country"] = df["country"].astype(str).str.strip().str.upper()
        df["country"] = df["country"].replace({"<NA>": pd.NA, "NAN": pd.NA, "": pd.NA})
    return df


def apply_filters(cac, ltv, countries, platforms, sources):
    cf, lf = cac.copy(), ltv.copy()
    if countries: cf = cf[cf["country"].isin(countries)]; lf = lf[lf["country"].isin(countries)]
    if platforms: cf = cf[cf["platform"].isin(platforms)]; lf = lf[lf["platform"].isin(platforms)]
    if sources:   cf = cf[cf["ad_source"].isin(sources)];  lf = lf[lf["ad_source"].isin(sources)]
    return cf, lf


# ── Calculations ──────────────────────────────────────────────────────────────

def safe_div(a, b):
    return np.nan if (pd.isna(b) or b == 0) else a / b


def build_kpis(cf, lf):
    spend     = cf["total_spend_usd"].sum()
    revenue   = lf["total_revenue"].sum()
    customers = cf["new_customers"].sum()
    users     = lf["user_id"].nunique() if "user_id" in lf.columns else customers
    cac       = safe_div(spend, customers)
    ltv       = safe_div(revenue, users or customers)
    return dict(spend=spend, revenue=revenue, customers=customers,
                cac=cac, ltv=ltv, ratio=safe_div(ltv, cac))


def aggregate(cf, lf, dim):
    ca = (cf.groupby(dim, as_index=False)
            .agg(spend=("total_spend_usd", "sum"), customers=("new_customers", "sum")))
    ca["cac"] = np.where(ca["customers"] > 0, ca["spend"] / ca["customers"], np.nan)
    agg_dict = {"total_revenue": ("total_revenue", "sum")}
    if "user_id" in lf.columns:
        agg_dict["users"] = ("user_id", "nunique")
    la = lf.groupby(dim, as_index=False).agg(**agg_dict)
    if "users" not in la.columns:
        la["users"] = la["total_revenue"].gt(0).astype(int)  # fallback
    la = la.rename(columns={"total_revenue": "revenue"})
    m = ca.merge(la, on=dim, how="outer")
    for col in ["spend", "customers", "revenue", "users"]:
        m[col] = pd.to_numeric(m.get(col, 0), errors="coerce").fillna(0)
    m["ltv"]   = np.where(m["users"] > 0, m["revenue"] / m["users"], np.nan)
    m["ratio"] = np.where(m["cac"]   > 0, m["ltv"]    / m["cac"],   np.nan)
    return m.sort_values("revenue", ascending=False)


def monthly_overall(cf, lf):
    ok_c = "first_purchase_date" in cf.columns and not cf["first_purchase_date"].isna().all()
    ok_l = "first_purchase_date" in lf.columns and not lf["first_purchase_date"].isna().all()
    if not ok_c or not ok_l:
        return None
    sm = (cf.dropna(subset=["first_purchase_date"])
            .assign(month=lambda d: d["first_purchase_date"].dt.to_period("M").dt.to_timestamp())
            .groupby("month", as_index=False)
            .agg(spend=("total_spend_usd", "sum"), customers=("new_customers", "sum")))
    rm = (lf.dropna(subset=["first_purchase_date"])
            .assign(month=lambda d: d["first_purchase_date"].dt.to_period("M").dt.to_timestamp())
            .groupby("month", as_index=False)
            .agg(revenue=("total_revenue", "sum"), users=("user_id", "nunique")))
    m = sm.merge(rm, on="month", how="outer").fillna(0).sort_values("month")
    if len(m) < 2:
        return None
    m["cac"]   = np.where(m["customers"] > 0, m["spend"]   / m["customers"], np.nan)
    m["ltv"]   = np.where(m["users"]     > 0, m["revenue"] / m["users"],     np.nan)
    m["ratio"] = np.where(m["cac"]       > 0, m["ltv"]     / m["cac"],       np.nan)
    return m


def monthly_by_dim(cf, lf, dim, top_n=6):
    ok_c = "first_purchase_date" in cf.columns and not cf["first_purchase_date"].isna().all()
    ok_l = "first_purchase_date" in lf.columns and not lf["first_purchase_date"].isna().all()
    if not ok_c or not ok_l:
        return None
    sm = (cf.dropna(subset=["first_purchase_date", dim])
            .assign(month=lambda d: d["first_purchase_date"].dt.to_period("M").dt.to_timestamp())
            .groupby(["month", dim], as_index=False)
            .agg(spend=("total_spend_usd", "sum"), customers=("new_customers", "sum")))
    rm = (lf.dropna(subset=["first_purchase_date", dim])
            .assign(month=lambda d: d["first_purchase_date"].dt.to_period("M").dt.to_timestamp())
            .groupby(["month", dim], as_index=False)
            .agg(revenue=("total_revenue", "sum"), users=("user_id", "nunique")))
    m = sm.merge(rm, on=["month", dim], how="outer").fillna(0).sort_values("month")
    if len(m) < 2:
        return None
    top = m.groupby(dim)["revenue"].sum().nlargest(top_n).index
    m = m[m[dim].isin(top)].copy()
    m["cac"]   = np.where(m["customers"] > 0, m["spend"]   / m["customers"], np.nan)
    m["ltv"]   = np.where(m["users"]     > 0, m["revenue"] / m["users"],     np.nan)
    m["ratio"] = np.where(m["cac"]       > 0, m["ltv"]     / m["cac"],       np.nan)
    return m


# ── Formatting ────────────────────────────────────────────────────────────────

def fmt(x):
    if pd.isna(x): return "—"
    if abs(x) >= 1_000_000: return f"${x/1_000_000:.1f}M"
    if abs(x) >= 1_000:     return f"${x/1_000:.1f}K"
    return f"${round(x)}"

def fmt_n(x):
    if pd.isna(x): return "—"
    if abs(x) >= 1_000_000: return f"{x/1_000_000:.1f}M"
    if abs(x) >= 1_000:     return f"{x/1_000:.1f}K"
    return f"{int(round(x)):,}"


# ── Charts ────────────────────────────────────────────────────────────────────

def bar_overview(df, dim, label):
    """Grouped bar: Spend / Revenue / CAC / Avg LTV per segment."""
    d = df.sort_values("revenue", ascending=False).head(15)
    fig = go.Figure()
    fig.add_bar(x=d[dim], y=d["spend"],   name="Spend",   marker_color="#0f766e",
                hovertemplate="<b>%{x}</b><br>Spend: $%{y:,.0f}<extra></extra>")
    fig.add_bar(x=d[dim], y=d["revenue"], name="Revenue", marker_color="#7c3aed",
                hovertemplate="<b>%{x}</b><br>Revenue: $%{y:,.0f}<extra></extra>")
    fig.add_bar(x=d[dim], y=d["cac"],     name="CAC",     marker_color="#f59e0b",
                hovertemplate="<b>%{x}</b><br>CAC: $%{y:,.0f}<extra></extra>")
    fig.add_bar(x=d[dim], y=d["ltv"],     name="Avg LTV", marker_color="#6366f1",
                hovertemplate="<b>%{x}</b><br>Avg LTV: $%{y:,.0f}<extra></extra>")
    fig.update_layout(
        barmode="group", template=TEMPLATE, height=400, margin=MARGIN,
        title=f"Key Metrics by {label}", title_font_size=16,
        legend=dict(orientation="h", y=1.1, x=1, xanchor="right"),
        yaxis=dict(tickprefix="$", separatethousands=True),
    )
    return fig


def line_metric(md, dim, metric, title, y_prefix="$", ref_lines=None):
    """Multi-line chart for a single metric, one line per segment."""
    fig = go.Figure()
    for i, seg in enumerate(md[dim].unique()):
        sub = md[md[dim] == seg].sort_values("month")
        ht  = f"$%{{y:,.0f}}" if y_prefix == "$" else "%{y:.2f}x"
        fig.add_trace(go.Scatter(
            x=sub["month"], y=sub[metric], name=str(seg),
            mode="lines+markers",
            line=dict(color=PALETTE[i % len(PALETTE)], width=2),
            hovertemplate=f"<b>{seg}</b>: {ht}<extra></extra>",
        ))
    if ref_lines:
        for val, dash, color, label in ref_lines:
            fig.add_hline(y=val, line_dash=dash, line_color=color, annotation_text=label)
    fig.update_layout(
        template=TEMPLATE, height=360, margin=MARGIN,
        title=title, title_font_size=16,
        hovermode="x unified",
        legend=dict(orientation="h", y=-0.25, x=0),
        yaxis=dict(tickprefix=y_prefix if y_prefix == "$" else "",
                   separatethousands=True),
    )
    return fig


# ── KPI row ───────────────────────────────────────────────────────────────────

def render_kpis(k):
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Total Spend",   fmt(k["spend"]))
    c2.metric("Total Revenue", fmt(k["revenue"]))
    c3.metric("New Customers", fmt_n(k["customers"]))
    c4.metric("Overall CAC",   fmt(k["cac"]))
    c5.metric("Avg LTV",       fmt(k["ltv"]))
    c6.metric("LTV:CAC", f"{k['ratio']:.1f}x" if pd.notna(k["ratio"]) else "—")

    r = k["ratio"]
    if pd.notna(r):
        if r >= 3:   badge, note = "🟢", f"Healthy — every $1 spent returns ${r:.1f} in lifetime value"
        elif r >= 1: badge, note = "🟡", "Marginal — LTV covers CAC but margin is thin"
        else:        badge, note = "🔴", "Unprofitable — CAC exceeds customer lifetime value"
    else:
        badge, note = "⚪", "Insufficient data"
    st.markdown(f'<div class="status-bar">{badge} &nbsp;{note}</div>', unsafe_allow_html=True)


# ── Main ──────────────────────────────────────────────────────────────────────

def divider():
    st.markdown('<hr class="divider">', unsafe_allow_html=True)


def main():
    inject_css()
    st.title("📈 Customer Acquisition Dashboard")
    st.caption("Spend, Revenue, CAC and LTV — across platforms, countries and ad sources.")

    if not CAC_FILE.exists() or not LTV_FILE.exists():
        st.error(f"Missing data files.\n- {CAC_FILE}\n- {LTV_FILE}")
        st.stop()

    cac, ltv = load_data(CAC_FILE, LTV_FILE)
    cac, ltv = normalize(cac), normalize(ltv)

    all_countries = sorted(set(cac["country"].dropna()) | set(ltv["country"].dropna()))
    all_platforms = sorted(set(cac["platform"].dropna()) | set(ltv["platform"].dropna()))
    all_sources   = sorted(set(cac["ad_source"].dropna()) | set(ltv["ad_source"].dropna()))

    st.sidebar.header("Filters")
    with st.sidebar.form("filters"):
        sel_c = st.multiselect("Country",   all_countries, default=all_countries)
        sel_p = st.multiselect("Platform",  all_platforms, default=all_platforms)
        sel_s = st.multiselect("Ad source", all_sources,   default=all_sources)
        st.form_submit_button("Apply", width="stretch")

    cf, lf = apply_filters(cac, ltv, sel_c, sel_p, sel_s)

    # ── KPIs ──────────────────────────────────────────────────────────────────
    render_kpis(build_kpis(cf, lf))

    # ── Overall trend (single lines) ──────────────────────────────────────────
    mo = monthly_overall(cf, lf)
    if mo is not None:
        divider()
        st.subheader("Overall Trends")
        c1, c2, c3 = st.columns(3)
        with c1:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=mo["month"], y=mo["spend"],   name="Spend",
                                     mode="lines+markers", line=dict(color="#0f766e", width=2),
                                     hovertemplate="Spend: $%{y:,.0f}<extra></extra>"))
            fig.add_trace(go.Scatter(x=mo["month"], y=mo["revenue"], name="Revenue",
                                     mode="lines+markers", line=dict(color="#7c3aed", width=2),
                                     hovertemplate="Revenue: $%{y:,.0f}<extra></extra>"))
            fig.update_layout(template=TEMPLATE, height=300, margin=MARGIN,
                              title="Spend vs Revenue", title_font_size=15,
                              hovermode="x unified",
                              legend=dict(orientation="h", y=1.12, x=1, xanchor="right"),
                              yaxis=dict(tickprefix="$", separatethousands=True))
            st.plotly_chart(fig, width="stretch")
        with c2:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=mo["month"], y=mo["cac"], name="CAC",
                                     mode="lines+markers", line=dict(color="#f59e0b", width=2),
                                     hovertemplate="CAC: $%{y:,.0f}<extra></extra>"))
            fig.add_trace(go.Scatter(x=mo["month"], y=mo["ltv"], name="Avg LTV",
                                     mode="lines+markers", line=dict(color="#6366f1", width=2),
                                     hovertemplate="Avg LTV: $%{y:,.0f}<extra></extra>"))
            fig.update_layout(template=TEMPLATE, height=300, margin=MARGIN,
                              title="CAC vs Avg LTV", title_font_size=15,
                              hovermode="x unified",
                              legend=dict(orientation="h", y=1.12, x=1, xanchor="right"),
                              yaxis=dict(tickprefix="$", separatethousands=True))
            st.plotly_chart(fig, width="stretch")
        with c3:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=mo["month"], y=mo["ratio"], name="LTV:CAC",
                                     mode="lines+markers", line=dict(color="#6366f1", width=2),
                                     hovertemplate="LTV:CAC: %{y:.2f}x<extra></extra>",
                                     fill="tozeroy", fillcolor="rgba(99,102,241,0.1)"))
            fig.add_hline(y=3, line_dash="dot",  line_color="#22c55e", annotation_text="Target 3x")
            fig.add_hline(y=1, line_dash="dash", line_color="#ef4444", annotation_text="Break-even")
            fig.update_layout(template=TEMPLATE, height=300, margin=MARGIN,
                              title="LTV:CAC Ratio", title_font_size=15,
                              hovermode="x unified",
                              showlegend=False)
            st.plotly_chart(fig, width="stretch")

    # ── Breakdown tabs ─────────────────────────────────────────────────────────
    divider()
    st.subheader("Breakdown")

    DIMS   = {"Platform": "platform", "Country": "country", "Ad Source": "ad_source"}
    tabs   = st.tabs(list(DIMS.keys()))

    for tab, (label, dim) in zip(tabs, DIMS.items()):
        with tab:
            df = aggregate(cf, lf, dim)
            md = monthly_by_dim(cf, lf, dim)

            # Bar overview
            st.plotly_chart(bar_overview(df, dim, label), width="stretch")

            # Line charts
            if md is not None:
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.plotly_chart(
                        line_metric(md, dim, "revenue", f"Revenue Over Time — {label}"),
                        width="stretch")
                with c2:
                    st.plotly_chart(
                        line_metric(md, dim, "cac", f"CAC Over Time — {label}"),
                        width="stretch")
                with c3:
                    st.plotly_chart(
                        line_metric(md, dim, "ratio", f"LTV:CAC Over Time — {label}",
                                    y_prefix="",
                                    ref_lines=[(3, "dot", "#22c55e", "3x"),
                                               (1, "dash", "#ef4444", "1x")]),
                        width="stretch")

            # Table
            display = df[[dim, "customers", "spend", "cac", "revenue", "ltv", "ratio"]].copy()
            display.columns = [label, "Customers", "Spend ($)", "CAC ($)", "Revenue ($)", "Avg LTV ($)", "LTV:CAC"]
            for col in ["Spend ($)", "CAC ($)", "Revenue ($)", "Avg LTV ($)"]:
                display[col] = display[col].round(0)
            display["LTV:CAC"] = display["LTV:CAC"].round(2)

            def color_ratio(val):
                try:
                    v = float(val)
                    if v >= 3:  return "background-color: rgba(34,197,94,0.20); color: #86efac"
                    if v >= 1:  return "background-color: rgba(245,158,11,0.20); color: #fcd34d"
                    return           "background-color: rgba(239,68,68,0.20); color: #fca5a5"
                except (ValueError, TypeError):
                    return ""

            st.dataframe(
                display.style.map(color_ratio, subset=["LTV:CAC"]),
                width="stretch", hide_index=True,
            )

            csv = display.to_csv(index=False).encode("utf-8")
            st.download_button(f"Download {label} CSV", data=csv,
                               file_name=f"breakdown_{dim}.csv", mime="text/csv",
                               key=f"dl_{dim}")


if __name__ == "__main__":
    main()