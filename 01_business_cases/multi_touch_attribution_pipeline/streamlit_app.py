from pathlib import Path
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Marketing LTV vs CAC Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "calculations"
CAC_FILE = DATA_DIR / "cac.csv"
LTV_FILE = DATA_DIR / "ltv.csv"

CHART_TEMPLATE = "plotly_white"
CHART_MARGIN = dict(l=10, r=10, t=60, b=10)


# ── CSS ──────────────────────────────────────────────────────────────────────

def inject_css():
    st.markdown(
        """
        <style>
        .block-container { padding-top: 1rem; padding-bottom: 1.5rem; }
        [data-testid="stMetric"] {
            background: linear-gradient(180deg, rgba(15,23,42,0.92), rgba(30,41,59,0.88));
            border: 1px solid rgba(148,163,184,0.22);
            padding: 0.9rem 1rem;
            border-radius: 18px;
            box-shadow: 0 6px 22px rgba(0,0,0,0.18);
        }
        [data-testid="stMetricLabel"] { color: rgba(226,232,240,0.82); }
        [data-testid="stMetricValue"] { color: #f8fafc; font-weight: 700; }
        .small-note { color: #94a3b8; font-size: 0.9rem; margin-top: -0.15rem; margin-bottom: 0.6rem; }
        .section-divider { border: none; border-top: 1px solid rgba(148,163,184,0.2); margin: 1.5rem 0; }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ── Data loading ─────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=False)
def load_data(cac_path: Path, ltv_path: Path):
    cac = pd.read_csv(cac_path)
    ltv = pd.read_csv(ltv_path)

    for df in (cac, ltv):
        for col in ["country", "platform", "ad_source", "campaign", "campaign_id"]:
            if col in df.columns:
                df[col] = df[col].replace("nan", pd.NA)

    for col in ["first_purchase_date", "last_purchase_date", "campaign_start_date"]:
        if col in cac.columns:
            cac[col] = pd.to_datetime(cac[col], errors="coerce")
        if col in ltv.columns:
            ltv[col] = pd.to_datetime(ltv[col], errors="coerce")

    for col in ["new_customers", "total_spend_usd", "cac_usd"]:
        if col in cac.columns:
            cac[col] = pd.to_numeric(cac[col], errors="coerce")
    for col in ["total_revenue", "purchase_count", "ltv_usd"]:
        if col in ltv.columns:
            ltv[col] = pd.to_numeric(ltv[col], errors="coerce")

    return cac, ltv


def normalize_country_codes(df):
    out = df.copy()
    if "country" in out.columns:
        out["country"] = out["country"].astype(str).str.strip().str.upper()
        out["country"] = out["country"].replace({"<NA>": pd.NA, "NAN": pd.NA, "": pd.NA})
    return out


def apply_filters(cac, ltv, countries, platforms, sources):
    cac_f, ltv_f = cac.copy(), ltv.copy()
    if countries:
        cac_f = cac_f[cac_f["country"].isin(countries)]
        ltv_f = ltv_f[ltv_f["country"].isin(countries)]
    if platforms:
        cac_f = cac_f[cac_f["platform"].isin(platforms)]
        ltv_f = ltv_f[ltv_f["platform"].isin(platforms)]
    if sources:
        cac_f = cac_f[cac_f["ad_source"].isin(sources)]
        ltv_f = ltv_f[ltv_f["ad_source"].isin(sources)]
    return cac_f, ltv_f


# ── Formatting ────────────────────────────────────────────────────────────────

def fmt_short(x, prefix="$"):
    if pd.isna(x):
        return "—"
    if abs(x) >= 1_000_000:
        return f"{prefix}{x/1_000_000:.1f}M"
    if abs(x) >= 1_000:
        return f"{prefix}{x/1_000:.1f}K"
    return f"{prefix}{x:.2f}"


def fmt_short_rounded(x, prefix="$"):
    """Like fmt_short but rounds to whole dollars for CAC / LTV."""
    if pd.isna(x):
        return "—"
    if abs(x) >= 1_000_000:
        return f"{prefix}{x/1_000_000:.1f}M"
    if abs(x) >= 1_000:
        return f"{prefix}{x/1_000:.1f}K"
    return f"{prefix}{round(x)}"


def fmt_num_short(x):
    if pd.isna(x):
        return "—"
    if abs(x) >= 1_000_000:
        return f"{x/1_000_000:.1f}M"
    if abs(x) >= 1_000:
        return f"{x/1_000:.1f}K"
    return f"{x:,.0f}"


def safe_div(a, b):
    return np.nan if pd.isna(b) or b == 0 else a / b


# ── KPI calculation ───────────────────────────────────────────────────────────

def build_kpis(cac_f, ltv_f):
    total_spend = cac_f["total_spend_usd"].sum()
    total_revenue = ltv_f["total_revenue"].sum()
    total_customers = cac_f["new_customers"].sum()
    overall_cac = safe_div(total_spend, total_customers)
    total_users = ltv_f["user_id"].nunique() if "user_id" in ltv_f.columns else 0
    if total_users == 0:
        total_users = total_customers
    avg_ltv = safe_div(total_revenue, total_users)
    ltv_cac_ratio = safe_div(avg_ltv, overall_cac)
    gross_profit = total_revenue - total_spend
    roas = safe_div(total_revenue, total_spend)
    return dict(
        total_spend=total_spend,
        total_revenue=total_revenue,
        total_customers=total_customers,
        overall_cac=overall_cac,
        avg_ltv=avg_ltv,
        ltv_cac_ratio=ltv_cac_ratio,
        gross_profit=gross_profit,
        roas=roas,
    )


# ── Dimension aggregation ─────────────────────────────────────────────────────

def aggregate_dim(cac_f, ltv_f, dim):
    cac_agg = (
        cac_f.groupby(dim, as_index=False)
        .agg(
            total_spend_usd=("total_spend_usd", "sum"),
            new_customers=("new_customers", "sum"),
            first_purchase_date=("first_purchase_date", "min"),
            last_purchase_date=("last_purchase_date", "max"),
        )
    )
    cac_agg["cac_usd"] = np.where(
        cac_agg["new_customers"] > 0,
        cac_agg["total_spend_usd"] / cac_agg["new_customers"],
        np.nan,
    )
    ltv_agg = (
        ltv_f.groupby(dim, as_index=False)
        .agg(
            total_revenue=("total_revenue", "sum"),
            purchase_count=("purchase_count", "sum"),
            users=("user_id", "nunique"),
        )
    )
    merged = cac_agg.merge(ltv_agg, on=dim, how="outer")
    for col in ["total_spend_usd", "new_customers", "total_revenue", "purchase_count", "users"]:
        if col in merged.columns:
            merged[col] = pd.to_numeric(merged[col], errors="coerce").fillna(0)
    merged["avg_ltv_usd"] = np.where(
        merged["users"] > 0, merged["total_revenue"] / merged["users"], np.nan
    )
    merged["ltv_cac_ratio"] = np.where(
        merged["cac_usd"] > 0, merged["avg_ltv_usd"] / merged["cac_usd"], np.nan
    )
    merged["profit_gap"] = merged["avg_ltv_usd"] - merged["cac_usd"]
    merged["roas"] = np.where(
        merged["total_spend_usd"] > 0,
        merged["total_revenue"] / merged["total_spend_usd"],
        np.nan,
    )
    return merged.sort_values("total_revenue", ascending=False)


# ── Monthly time-series helpers ──────────────────────────────────────────────

def _monthly_series_by_dim(cac_f, ltv_f, dim, top_n=8):
    """
    Monthly aggregation grouped by (month, dim).
    Returns a long DataFrame or None if date columns are missing.
    Limits to top_n dimensions by total revenue to keep charts readable.
    """
    has_cac_date = "campaign_start_date" in cac_f.columns and not cac_f["campaign_start_date"].isna().all()
    has_ltv_date = "first_purchase_date" in ltv_f.columns and not ltv_f["first_purchase_date"].isna().all()
    if not has_cac_date or not has_ltv_date:
        return None
    if dim not in cac_f.columns or dim not in ltv_f.columns:
        return None

    spend_m = (
        cac_f.dropna(subset=["campaign_start_date", dim])
        .assign(month=lambda d: d["campaign_start_date"].dt.to_period("M").dt.to_timestamp())
        .groupby(["month", dim], as_index=False)
        .agg(spend=("total_spend_usd", "sum"), new_customers=("new_customers", "sum"))
    )
    rev_m = (
        ltv_f.dropna(subset=["first_purchase_date", dim])
        .assign(month=lambda d: d["first_purchase_date"].dt.to_period("M").dt.to_timestamp())
        .groupby(["month", dim], as_index=False)
        .agg(revenue=("total_revenue", "sum"), users=("user_id", "nunique"))
    )
    m = spend_m.merge(rev_m, on=["month", dim], how="outer").fillna(0).sort_values("month")
    if len(m) < 2:
        return None

    # Keep only top_n dims by total revenue
    top_dims = (
        m.groupby(dim)["revenue"].sum()
        .nlargest(top_n).index.tolist()
    )
    m = m[m[dim].isin(top_dims)]

    m["cac"] = np.where(m["new_customers"] > 0, m["spend"] / m["new_customers"], np.nan)
    m["avg_ltv"] = np.where(m["users"] > 0, m["revenue"] / m["users"], np.nan)
    m["ltv_cac_ratio"] = np.where(m["cac"] > 0, m["avg_ltv"] / m["cac"], np.nan)
    m["roas"] = np.where(m["spend"] > 0, m["revenue"] / m["spend"], np.nan)
    m["gross_profit"] = m["revenue"] - m["spend"]
    return m


def _monthly_series(cac_f, ltv_f):
    """
    Returns a merged monthly DataFrame with columns:
    month, spend, revenue, new_customers, cac, avg_ltv, ltv_cac_ratio, roas, gross_profit
    Only returns data if both date columns exist and have ≥2 months.
    """
    has_cac_date = "campaign_start_date" in cac_f.columns and not cac_f["campaign_start_date"].isna().all()
    has_ltv_date = "first_purchase_date" in ltv_f.columns and not ltv_f["first_purchase_date"].isna().all()
    if not has_cac_date or not has_ltv_date:
        return None

    spend_m = (
        cac_f.dropna(subset=["campaign_start_date"])
        .assign(month=lambda d: d["campaign_start_date"].dt.to_period("M").dt.to_timestamp())
        .groupby("month", as_index=False)
        .agg(spend=("total_spend_usd", "sum"), new_customers=("new_customers", "sum"))
    )
    rev_m = (
        ltv_f.dropna(subset=["first_purchase_date"])
        .assign(month=lambda d: d["first_purchase_date"].dt.to_period("M").dt.to_timestamp())
        .groupby("month", as_index=False)
        .agg(revenue=("total_revenue", "sum"), users=("user_id", "nunique"))
    )
    m = spend_m.merge(rev_m, on="month", how="outer").fillna(0).sort_values("month")
    if len(m) < 2:
        return None

    m["cac"] = np.where(m["new_customers"] > 0, m["spend"] / m["new_customers"], np.nan)
    m["avg_ltv"] = np.where(m["users"] > 0, m["revenue"] / m["users"], np.nan)
    m["ltv_cac_ratio"] = np.where(m["cac"] > 0, m["avg_ltv"] / m["cac"], np.nan)
    m["roas"] = np.where(m["spend"] > 0, m["revenue"] / m["spend"], np.nan)
    m["gross_profit"] = m["revenue"] - m["spend"]
    return m


# ── Charts ────────────────────────────────────────────────────────────────────

def make_bar(df, x, y, title, color=None, text_auto=".2s"):
    fig = px.bar(df, x=x, y=y, color=color, text_auto=text_auto,
                 title=title, template=CHART_TEMPLATE)
    fig.update_traces(marker_line_width=0, hovertemplate="<b>%{x}</b><br>%{y:$,.2f}<extra></extra>")
    fig.update_layout(height=430, margin=CHART_MARGIN, title_font=dict(size=18), legend_title_text="")
    return fig


def make_cost_revenue_chart(cac_f, ltv_f):
    spend = cac_f.groupby("country", as_index=False).agg(cost=("total_spend_usd", "sum"))
    rev = ltv_f.groupby("country", as_index=False).agg(revenue=("total_revenue", "sum"))
    merged = spend.merge(rev, on="country", how="outer").fillna(0)
    order = merged.sort_values("revenue", ascending=False)["country"]
    fig = go.Figure()
    fig.add_bar(x=merged["country"], y=merged["cost"], name="Cost", marker_color="#0f766e")
    fig.add_bar(x=merged["country"], y=merged["revenue"], name="Revenue", marker_color="#7c3aed")
    fig.update_layout(
        barmode="group", template=CHART_TEMPLATE,
        title="Cost vs Revenue by Country", height=480, margin=CHART_MARGIN,
        xaxis=dict(categoryorder="array", categoryarray=list(order)),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        title_font=dict(size=18),
    )
    fig.update_yaxes(tickprefix="$", separatethousands=True)
    return fig


def make_roas_chart(breakdown, dim):
    df = breakdown.dropna(subset=["roas"]).sort_values("roas", ascending=False).head(15)
    colors = ["#22c55e" if v >= 3 else "#f59e0b" if v >= 1 else "#ef4444" for v in df["roas"]]
    fig = go.Figure(go.Bar(
        x=df[dim], y=df["roas"], marker_color=colors,
        text=df["roas"].round(2), textposition="outside",
        hovertemplate="<b>%{x}</b><br>ROAS: %{y:.2f}x<extra></extra>",
    ))
    fig.add_hline(y=1, line_dash="dash", line_color="#ef4444", annotation_text="Break-even (1x)")
    fig.add_hline(y=3, line_dash="dot", line_color="#22c55e", annotation_text="Healthy (3x)")
    fig.update_layout(
        title=f"ROAS by {dim.replace('_', ' ').title()}",
        template=CHART_TEMPLATE, height=430, margin=CHART_MARGIN,
        title_font=dict(size=18), yaxis_title="ROAS (Revenue / Spend)",
    )
    return fig


def make_profit_gap_chart(breakdown, dim):
    df = breakdown.dropna(subset=["profit_gap"]).sort_values("profit_gap", ascending=False).head(15)
    colors = ["#22c55e" if v > 0 else "#ef4444" for v in df["profit_gap"]]
    fig = go.Figure(go.Bar(
        x=df[dim], y=df["profit_gap"], marker_color=colors,
        text=df["profit_gap"].round(2), texttemplate="$%{text}", textposition="outside",
        hovertemplate="<b>%{x}</b><br>LTV − CAC: $%{y:.2f}<extra></extra>",
    ))
    fig.add_hline(y=0, line_dash="dash", line_color="#64748b", annotation_text="Break-even")
    fig.update_layout(
        title=f"Profit Gap (LTV − CAC) by {dim.replace('_', ' ').title()}",
        template=CHART_TEMPLATE, height=430, margin=CHART_MARGIN,
        title_font=dict(size=18), yaxis_title="LTV − CAC ($)",
    )
    return fig


def make_ltv_cac_ratio_chart(breakdown, dim):
    df = breakdown.dropna(subset=["ltv_cac_ratio"]).sort_values("ltv_cac_ratio", ascending=False).head(15)
    colors = ["#22c55e" if v >= 3 else "#f59e0b" if v >= 1 else "#ef4444" for v in df["ltv_cac_ratio"]]
    fig = go.Figure(go.Bar(
        x=df[dim], y=df["ltv_cac_ratio"], marker_color=colors,
        text=df["ltv_cac_ratio"].round(2), texttemplate="%{text}x", textposition="outside",
        hovertemplate="<b>%{x}</b><br>LTV:CAC %{y:.2f}x<extra></extra>",
    ))
    fig.add_hline(y=1, line_dash="dash", line_color="#ef4444", annotation_text="1x")
    fig.add_hline(y=3, line_dash="dot", line_color="#22c55e", annotation_text="Target 3x")
    fig.update_layout(
        title=f"LTV:CAC Ratio by {dim.replace('_', ' ').title()}",
        template=CHART_TEMPLATE, height=430, margin=CHART_MARGIN,
        title_font=dict(size=18), yaxis_title="LTV:CAC Ratio",
    )
    return fig


def make_cac_ltv_grouped(breakdown, dim):
    df = breakdown.dropna(subset=["cac_usd", "avg_ltv_usd"]).head(12)
    if df.empty:
        return None
    fig = go.Figure()
    fig.add_bar(x=df[dim], y=df["cac_usd"], name="CAC", marker_color="#f59e0b")
    fig.add_bar(x=df[dim], y=df["avg_ltv_usd"], name="Avg LTV", marker_color="#6366f1")
    fig.update_layout(
        barmode="group", template=CHART_TEMPLATE,
        title=f"CAC vs Avg LTV by {dim.replace('_', ' ').title()}",
        height=430, margin=CHART_MARGIN,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        title_font=dict(size=18),
    )
    fig.update_yaxes(tickprefix="$", separatethousands=True)
    return fig


# ── Line / trend charts ───────────────────────────────────────────────────────

def _line_layout(fig, title, y_prefix="$"):
    fig.update_layout(
        title=title, template=CHART_TEMPLATE, height=380, margin=CHART_MARGIN,
        title_font=dict(size=18),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
    )
    if y_prefix:
        fig.update_yaxes(tickprefix=y_prefix, separatethousands=True)
    return fig


def make_trend_spend_revenue(m):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=m["month"], y=m["spend"], name="Spend",
        mode="lines+markers", fill="tozeroy",
        line=dict(color="#0f766e", width=2), fillcolor="rgba(15,118,110,0.12)",
        hovertemplate="Spend: $%{y:,.0f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=m["month"], y=m["revenue"], name="Revenue",
        mode="lines+markers", fill="tozeroy",
        line=dict(color="#7c3aed", width=2), fillcolor="rgba(124,58,237,0.12)",
        hovertemplate="Revenue: $%{y:,.0f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=m["month"], y=m["gross_profit"], name="Gross Profit",
        mode="lines+markers",
        line=dict(color="#0ea5e9", width=2, dash="dot"),
        hovertemplate="Gross Profit: $%{y:,.0f}<extra></extra>",
    ))
    return _line_layout(fig, "Monthly Spend, Revenue & Gross Profit")


def make_trend_customers(m):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=m["month"], y=m["new_customers"], name="New Customers",
        mode="lines+markers", fill="tozeroy",
        line=dict(color="#f59e0b", width=2), fillcolor="rgba(245,158,11,0.12)",
        hovertemplate="New Customers: %{y:,.0f}<extra></extra>",
    ))
    fig.update_layout(
        title="Monthly New Customers", template=CHART_TEMPLATE, height=320,
        margin=CHART_MARGIN, title_font=dict(size=18), hovermode="x unified",
    )
    fig.update_yaxes(separatethousands=True)
    return fig


def make_trend_cac_ltv(m):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=m["month"], y=m["cac"], name="CAC",
        mode="lines+markers",
        line=dict(color="#f59e0b", width=2),
        hovertemplate="CAC: $%{y:,.0f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=m["month"], y=m["avg_ltv"], name="Avg LTV",
        mode="lines+markers",
        line=dict(color="#6366f1", width=2),
        hovertemplate="Avg LTV: $%{y:,.0f}<extra></extra>",
    ))
    return _line_layout(fig, "Monthly CAC vs Avg LTV")


def make_trend_ratios(m):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=m["month"], y=m["ltv_cac_ratio"], name="LTV:CAC",
        mode="lines+markers",
        line=dict(color="#6366f1", width=2),
        hovertemplate="LTV:CAC: %{y:.2f}x<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=m["month"], y=m["roas"], name="ROAS",
        mode="lines+markers",
        line=dict(color="#0ea5e9", width=2),
        hovertemplate="ROAS: %{y:.2f}x<extra></extra>",
    ))
    fig.add_hline(y=3, line_dash="dot", line_color="#22c55e", annotation_text="Target 3x")
    fig.add_hline(y=1, line_dash="dash", line_color="#ef4444", annotation_text="Break-even 1x")
    return _line_layout(fig, "Monthly LTV:CAC & ROAS Trends", y_prefix="")


# ── Multi-line per-dimension trend charts ────────────────────────────────────

_COLORS = [
    "#6366f1", "#0ea5e9", "#22c55e", "#f59e0b", "#ef4444",
    "#a855f7", "#14b8a6", "#f97316", "#ec4899", "#84cc16",
]


def _multi_line(md, dim, y_col, title, y_fmt="$", ref_lines=None):
    """Generic multi-line chart: one line per dim value, x=month."""
    fig = go.Figure()
    dims_in = md[dim].unique()
    for i, d in enumerate(dims_in):
        sub = md[md[dim] == d].sort_values("month")
        hover = f"$%{{y:,.0f}}" if y_fmt == "$" else "%{y:.2f}x" if y_fmt == "x" else "%{y:,.0f}"
        fig.add_trace(go.Scatter(
            x=sub["month"], y=sub[y_col],
            name=str(d), mode="lines+markers",
            line=dict(color=_COLORS[i % len(_COLORS)], width=2),
            hovertemplate=f"<b>{d}</b><br>{hover}<extra></extra>",
        ))
    if ref_lines:
        for val, dash, color, label in ref_lines:
            fig.add_hline(y=val, line_dash=dash, line_color=color, annotation_text=label)
    prefix = "$" if y_fmt == "$" else ""
    fig.update_layout(
        title=title, template=CHART_TEMPLATE, height=420, margin=CHART_MARGIN,
        title_font=dict(size=18), hovermode="x unified",
        legend=dict(orientation="h", yanchor="top", y=-0.15, xanchor="left", x=0),
    )
    if prefix:
        fig.update_yaxes(tickprefix=prefix, separatethousands=True)
    return fig


def make_dim_trend_spend(md, dim, label):
    return _multi_line(md, dim, "spend", f"Monthly Spend by {label}")


def make_dim_trend_revenue(md, dim, label):
    return _multi_line(md, dim, "revenue", f"Monthly Revenue by {label}")


def make_dim_trend_customers(md, dim, label):
    return _multi_line(md, dim, "new_customers", f"Monthly New Customers by {label}", y_fmt="n")


def make_dim_trend_cac(md, dim, label):
    return _multi_line(md, dim, "cac", f"Monthly CAC by {label}")


def make_dim_trend_ltv(md, dim, label):
    return _multi_line(md, dim, "avg_ltv", f"Monthly Avg LTV by {label}")


def make_dim_trend_roas(md, dim, label):
    return _multi_line(
        md, dim, "roas", f"Monthly ROAS by {label}", y_fmt="x",
        ref_lines=[(3, "dot", "#22c55e", "Target 3x"), (1, "dash", "#ef4444", "Break-even 1x")],
    )


def make_dim_trend_ltv_cac(md, dim, label):
    return _multi_line(
        md, dim, "ltv_cac_ratio", f"Monthly LTV:CAC by {label}", y_fmt="x",
        ref_lines=[(3, "dot", "#22c55e", "Target 3x"), (1, "dash", "#ef4444", "Break-even 1x")],
    )


def make_dim_trend_profit(md, dim, label):
    return _multi_line(md, dim, "gross_profit", f"Monthly Gross Profit by {label}")


# ── Table ─────────────────────────────────────────────────────────────────────

def top_table(df, dim):
    out = df.copy()
    for col in ["total_spend_usd", "cac_usd", "total_revenue", "avg_ltv_usd",
                "ltv_cac_ratio", "profit_gap", "roas"]:
        if col in out.columns:
            out[col] = out[col].round(2)
    cols = [dim, "new_customers", "users", "total_spend_usd", "cac_usd",
            "total_revenue", "avg_ltv_usd", "ltv_cac_ratio", "profit_gap", "roas"]
    return out[[c for c in cols if c in out.columns]]


# ── KPI header ────────────────────────────────────────────────────────────────

def render_kpis(kpis):
    m1, m2, m3, m4, m5, m6, m7, m8 = st.columns(8)
    m1.metric("Total Spend",    fmt_short(kpis["total_spend"]))
    m2.metric("Total Revenue",  fmt_short(kpis["total_revenue"]))
    m3.metric("Gross Profit",   fmt_short(kpis["gross_profit"]))
    m4.metric("New Customers",  fmt_num_short(kpis["total_customers"]))
    m5.metric("Overall CAC",    fmt_short_rounded(kpis["overall_cac"]))   # rounded
    m6.metric("Avg LTV",        fmt_short_rounded(kpis["avg_ltv"]))       # rounded
    m7.metric("LTV:CAC",  f"{kpis['ltv_cac_ratio']:.2f}x" if pd.notna(kpis["ltv_cac_ratio"]) else "—")
    m8.metric("ROAS",     f"{kpis['roas']:.2f}x"          if pd.notna(kpis["roas"])           else "—")

    status_ltv = (
        "🟢 Healthy (≥3x)"    if pd.notna(kpis["ltv_cac_ratio"]) and kpis["ltv_cac_ratio"] >= 3
        else "🟡 Marginal (1–3x)" if pd.notna(kpis["ltv_cac_ratio"]) and kpis["ltv_cac_ratio"] >= 1
        else "🔴 Unprofitable (<1x)"
    )
    status_roas = (
        "🟢 Healthy (≥3x)"    if pd.notna(kpis["roas"]) and kpis["roas"] >= 3
        else "🟡 Marginal (1–3x)" if pd.notna(kpis["roas"]) and kpis["roas"] >= 1
        else "🔴 Unprofitable (<1x)"
    )
    st.markdown(
        f'<div class="small-note">LTV:CAC: {status_ltv} &nbsp;|&nbsp; ROAS: {status_roas} &nbsp;|&nbsp; Healthy target is often 3:1 or better.</div>',
        unsafe_allow_html=True,
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def divider():
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)


def main():
    inject_css()
    st.title("📈 Marketing Dashboard: LTV vs CAC")
    st.caption("Compare acquisition efficiency and customer value across countries, platforms, and ad sources.")

    if not CAC_FILE.exists() or not LTV_FILE.exists():
        st.error(f"Missing files. Expected:\n- {CAC_FILE}\n- {LTV_FILE}")
        st.stop()

    cac, ltv = load_data(CAC_FILE, LTV_FILE)
    cac = normalize_country_codes(cac)
    ltv = normalize_country_codes(ltv)

    all_countries = sorted(set(cac["country"].dropna().unique()).union(set(ltv["country"].dropna().unique())))
    all_platforms = sorted(set(cac["platform"].dropna().unique()).union(set(ltv["platform"].dropna().unique())))
    all_sources   = sorted(set(cac["ad_source"].dropna().unique()).union(set(ltv["ad_source"].dropna().unique())))

    st.sidebar.header("Filters")
    with st.sidebar.form("filters_form"):
        selected_countries = st.multiselect("Country",    all_countries, default=all_countries)
        selected_platforms = st.multiselect("Platform",   all_platforms, default=all_platforms)
        selected_sources   = st.multiselect("Ad source",  all_sources,   default=all_sources)
        st.form_submit_button("Apply filters", use_container_width=True)

    cac_f, ltv_f = apply_filters(cac, ltv, selected_countries, selected_platforms, selected_sources)
    kpis = build_kpis(cac_f, ltv_f)

    # ── KPIs ─────────────────────────────────────────────────────────────────
    render_kpis(kpis)

    # ── Trends (shown only when date data is available) ───────────────────────
    monthly = _monthly_series(cac_f, ltv_f)
    if monthly is not None:
        divider()
        st.subheader("Trends Over Time")

        st.plotly_chart(make_trend_spend_revenue(monthly), use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(make_trend_customers(monthly), use_container_width=True)
        with col2:
            st.plotly_chart(make_trend_ratios(monthly), use_container_width=True)

        st.plotly_chart(make_trend_cac_ltv(monthly), use_container_width=True)

    # ── Per-dimension trends ──────────────────────────────────────────────────
    divider()
    st.subheader("Metric Trends by Segment")
    st.caption("Track how each ad source, platform, or country moves over time. Top 8 segments by revenue are shown.")

    trend_dims = {"Ad Source": "ad_source", "Platform": "platform", "Country": "country"}
    tdim_label = st.radio("Segment by", list(trend_dims.keys()), horizontal=True, key="trend_dim_radio")
    tdim = trend_dims[tdim_label]
    md = _monthly_series_by_dim(cac_f, ltv_f, tdim)

    if md is not None:
        metric_options = {
            "Revenue": make_dim_trend_revenue,
            "Spend": make_dim_trend_spend,
            "Gross Profit": make_dim_trend_profit,
            "New Customers": make_dim_trend_customers,
            "CAC": make_dim_trend_cac,
            "Avg LTV": make_dim_trend_ltv,
            "ROAS": make_dim_trend_roas,
            "LTV:CAC Ratio": make_dim_trend_ltv_cac,
        }
        selected_metrics = st.multiselect(
            "Metrics to display",
            list(metric_options.keys()),
            default=["Revenue", "Spend", "CAC", "ROAS"],
            key="trend_metric_select",
        )
        for i in range(0, len(selected_metrics), 2):
            cols = st.columns(2)
            for j, metric in enumerate(selected_metrics[i : i + 2]):
                with cols[j]:
                    fig = metric_options[metric](md, tdim, tdim_label)
                    st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Date columns (`campaign_start_date` in CAC, `first_purchase_date` in LTV) are required to show trends.")

    # ── Country overview ──────────────────────────────────────────────────────
    divider()
    st.subheader("Country Overview")
    st.plotly_chart(make_cost_revenue_chart(cac_f, ltv_f), use_container_width=True)

    # ── Dimension breakdown ───────────────────────────────────────────────────
    divider()
    st.subheader("Breakdown by Dimension")

    dims = {"Ad Source": "ad_source", "Platform": "platform", "Country": "country"}
    selected_dim_label = st.radio("Breakdown", list(dims.keys()), horizontal=True)
    dim = dims[selected_dim_label]
    breakdown = aggregate_dim(cac_f, ltv_f, dim)

    # Row 1: Spend / Revenue bars
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(
            make_bar(breakdown.sort_values("total_spend_usd", ascending=False).head(15),
                     x=dim, y="total_spend_usd", title=f"Total Spend by {selected_dim_label}", color=dim),
            use_container_width=True,
        )
    with col2:
        st.plotly_chart(
            make_bar(breakdown.sort_values("total_revenue", ascending=False).head(15),
                     x=dim, y="total_revenue", title=f"Total Revenue by {selected_dim_label}", color=dim),
            use_container_width=True,
        )

    # Row 2: CAC vs LTV grouped + ROAS
    col1, col2 = st.columns(2)
    with col1:
        cac_ltv_fig = make_cac_ltv_grouped(breakdown, dim)
        if cac_ltv_fig:
            st.plotly_chart(cac_ltv_fig, use_container_width=True)
    with col2:
        st.plotly_chart(make_roas_chart(breakdown, dim), use_container_width=True)

    # Row 3: LTV:CAC ratio + Profit Gap
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(make_ltv_cac_ratio_chart(breakdown, dim), use_container_width=True)
    with col2:
        st.plotly_chart(make_profit_gap_chart(breakdown, dim), use_container_width=True)

    # ── Table + download ──────────────────────────────────────────────────────
    divider()
    st.subheader(f"{selected_dim_label} Performance Table")
    st.dataframe(top_table(breakdown, dim), use_container_width=True, hide_index=True)

    csv = top_table(breakdown, dim).to_csv(index=False).encode("utf-8")
    st.download_button(
        label=f"Download {selected_dim_label.lower()} breakdown CSV",
        data=csv,
        file_name=f"marketing_breakdown_{dim}.csv",
        mime="text/csv",
    )


if __name__ == "__main__":
    main()