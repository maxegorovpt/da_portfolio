from pathlib import Path
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="Marketing Overview Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "calculations"
CAC_FILE = DATA_DIR / "cac.csv"
LTV_FILE = DATA_DIR / "ltv.csv"


def inject_css():
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1rem;
            padding-bottom: 1.5rem;
        }
        [data-testid="stMetric"] {
            background: linear-gradient(180deg, rgba(15,23,42,0.92), rgba(30,41,59,0.88));
            border: 1px solid rgba(148,163,184,0.22);
            padding: 0.9rem 1rem;
            border-radius: 18px;
            box-shadow: 0 6px 22px rgba(0,0,0,0.18);
        }
        [data-testid="stMetricLabel"] { color: rgba(226,232,240,0.82); }
        [data-testid="stMetricValue"] {
            color: #f8fafc;
            font-weight: 700;
            font-variant-numeric: tabular-nums;
        }
        .small-note {
            color: #94a3b8;
            font-size: 0.9rem;
            margin-top: -0.15rem;
            margin-bottom: 0.6rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


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

    # user_id in LTV should stay as string for nunique counting
    if "user_id" in ltv.columns:
        ltv["user_id"] = ltv["user_id"].astype(str)

    return cac, ltv


def normalize_country_codes(df):
    out = df.copy()
    if "country" in out.columns:
        out["country"] = out["country"].astype(str).str.strip().str.upper()
        out["country"] = out["country"].replace({"<NA>": pd.NA, "NAN": pd.NA, "": pd.NA})
    return out


def apply_filters(cac, ltv, countries, platforms, sources):
    cac_f = cac.copy()
    ltv_f = ltv.copy()
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


def fmt_money(x):
    return "—" if pd.isna(x) else f"${x:,.2f}"


def fmt_num(x):
    return "—" if pd.isna(x) else f"{x:,.0f}"


def safe_div(a, b):
    return np.nan if pd.isna(b) or b == 0 else a / b


def build_kpis(cac_f, ltv_f):
    total_spend = cac_f["total_spend_usd"].sum() if "total_spend_usd" in cac_f.columns else 0
    total_revenue = ltv_f["total_revenue"].sum() if "total_revenue" in ltv_f.columns else 0
    total_ltv = ltv_f["ltv_usd"].sum() if "ltv_usd" in ltv_f.columns else total_revenue
    total_customers = cac_f["new_customers"].sum() if "new_customers" in cac_f.columns else 0

    # FIX: user_id is kept as string now — nunique works correctly
    total_users = ltv_f["user_id"].nunique() if "user_id" in ltv_f.columns else 0
    if total_users == 0:
        total_users = total_customers

    overall_cac = safe_div(total_spend, total_customers)
    avg_ltv = safe_div(total_ltv, total_users)
    ltv_cac_ratio = safe_div(avg_ltv, overall_cac)

    return {
        "total_spend": total_spend,
        "total_revenue": total_revenue,
        "total_ltv": total_ltv,
        "total_customers": total_customers,
        "overall_cac": overall_cac,
        "avg_ltv": avg_ltv,
        "ltv_cac_ratio": ltv_cac_ratio,
    }


def build_overview_data(cac_f, ltv_f):
    spend_by_source = (
        cac_f.groupby("ad_source", as_index=False)
        .agg(total_spend_usd=("total_spend_usd", "sum"))
        .sort_values("total_spend_usd", ascending=False)
    )

    revenue_by_source = (
        ltv_f.groupby("ad_source", as_index=False)
        .agg(total_revenue=("total_revenue", "sum"))
        .sort_values("total_revenue", ascending=False)
    )

    ltv_by_source = (
        ltv_f.groupby("ad_source", as_index=False)
        .agg(total_ltv_usd=("ltv_usd", "sum"))
        .sort_values("total_ltv_usd", ascending=False)
    )

    overview = spend_by_source.merge(revenue_by_source, on="ad_source", how="outer")
    overview = overview.merge(ltv_by_source, on="ad_source", how="outer").fillna(0)
    overview["net_value"] = overview["total_ltv_usd"] - overview["total_spend_usd"]
    overview = overview.sort_values("total_ltv_usd", ascending=False)
    return overview


def build_time_series(cac_f, ltv_f):
    """
    Build a monthly time series of spend, revenue, and LTV.
    Buckets by month so sparse date data still produces a readable trend line,
    and avoids the mismatch between exact CAC dates and exact LTV dates.
    """
    def _monthly(df, date_candidates, agg_spec, label):
        for col in date_candidates:
            if col in df.columns and df[col].notna().any():
                tmp = df.copy()
                tmp["month"] = (
                    pd.to_datetime(tmp[col], errors="coerce")
                    .dt.to_period("M")
                    .dt.to_timestamp()
                )
                return (
                    tmp.dropna(subset=["month"])
                    .groupby("month", as_index=False)
                    .agg(**agg_spec)
                    .rename(columns={"month": "date"})
                )
        return pd.DataFrame(columns=["date"] + list(agg_spec.keys()))

    spend_ts = _monthly(
        cac_f,
        ["first_purchase_date", "campaign_start_date"],
        {"total_spend_usd": ("total_spend_usd", "sum")},
        "spend",
    )

    revenue_ts = _monthly(
        ltv_f,
        ["first_purchase_date", "last_purchase_date"],
        {
            "total_revenue": ("total_revenue", "sum"),
            "total_ltv_usd": ("ltv_usd", "sum"),
        },
        "revenue",
    )

    ts = spend_ts.merge(revenue_ts, on="date", how="outer").fillna(0)
    if ts.empty:
        return ts

    ts["date"] = pd.to_datetime(ts["date"], errors="coerce")
    ts = ts.dropna(subset=["date"]).sort_values("date")
    ts["net_value"] = ts["total_ltv_usd"] - ts["total_spend_usd"]
    return ts


def make_overview_bar(overview):
    melted = overview.melt(
        id_vars="ad_source",
        value_vars=["total_spend_usd", "total_ltv_usd"],
        var_name="metric",
        value_name="value",
    )
    metric_map = {
        "total_spend_usd": "Spend",
        "total_ltv_usd": "LTV",
    }
    melted["metric"] = melted["metric"].map(metric_map)

    fig = px.bar(
        melted,
        x="ad_source",
        y="value",
        color="metric",
        barmode="group",
        title="Overview by Ad Source",
        template="plotly_white",
        color_discrete_map={"Spend": "#0f766e", "LTV": "#7c3aed"},
    )
    fig.update_traces(
        hovertemplate="<b>%{x}</b><br>%{fullData.name}: %{y:$,.2f}<extra></extra>"
    )
    fig.update_layout(
        height=430,
        margin=dict(l=10, r=10, t=60, b=10),
        title_font=dict(size=18),
        legend_title_text="",
        yaxis_title=None,
        xaxis_title=None,
    )
    fig.update_yaxes(tickprefix="$", separatethousands=True)
    return fig


def make_tracking_line(ts):
    melted = ts.melt(
        id_vars="date",
        value_vars=["total_spend_usd", "total_ltv_usd", "net_value"],
        var_name="metric",
        value_name="value",
    )
    metric_map = {
        "total_spend_usd": "Spend",
        "total_ltv_usd": "LTV",
        "net_value": "Net Value",
    }
    melted["metric"] = melted["metric"].map(metric_map)

    fig = px.line(
        melted,
        x="date",
        y="value",
        color="metric",
        title="Monthly Tracking",
        template="plotly_white",
        color_discrete_map={
            "Spend": "#0f766e",
            "LTV": "#7c3aed",
            "Net Value": "#ea580c",
        },
        markers=True,
    )
    fig.update_traces(
        mode="lines+markers",
        hovertemplate="<b>%{x|%Y-%m}</b><br>%{fullData.name}: %{y:$,.2f}<extra></extra>"
    )
    fig.update_layout(
        height=430,
        margin=dict(l=10, r=10, t=60, b=10),
        title_font=dict(size=18),
        legend_title_text="",
        yaxis_title=None,
        xaxis_title=None,
    )
    fig.update_yaxes(tickprefix="$", separatethousands=True)
    return fig


def top_table(overview):
    out = overview.copy()
    for col in ["total_spend_usd", "total_revenue", "total_ltv_usd", "net_value"]:
        if col in out.columns:
            out[col] = out[col].round(2)
    return out[["ad_source", "total_spend_usd", "total_revenue", "total_ltv_usd", "net_value"]]


def main():
    inject_css()
    st.title("📈 Marketing Overview Dashboard")
    st.caption("LTV and CAC comparison by platform, ad source, and country.")

    # ── File existence check ──────────────────────────────────────────────────
    if not CAC_FILE.exists() or not LTV_FILE.exists():
        missing = [str(f) for f in (CAC_FILE, LTV_FILE) if not f.exists()]
        st.error(f"Missing data file(s): {', '.join(missing)}\n\nRe-run the calculation scripts to generate them.")
        st.stop()

    cac, ltv = load_data(CAC_FILE, LTV_FILE)
    cac = normalize_country_codes(cac)
    ltv = normalize_country_codes(ltv)

    # ── Data health checks ────────────────────────────────────────────────────
    if cac.empty:
        st.error(
            "cac.csv loaded but contains no rows. "
            "Re-run `cac_calculation.py` and check that purchases.csv is populated."
        )
        st.stop()

    if ltv.empty:
        st.error(
            "ltv.csv loaded but contains no rows. "
            "This usually means none of the purchase `campaign_id` values matched "
            "those in your ads files. Re-run `ltv_calculation.py` — the updated "
            "`metrics.py` keeps unmatched purchases rather than dropping them."
        )
        st.stop()

    # ── Sidebar filters ───────────────────────────────────────────────────────
    all_countries = sorted(
        set(cac["country"].dropna().unique()).union(set(ltv["country"].dropna().unique()))
    )
    all_platforms = sorted(
        set(cac["platform"].dropna().unique()).union(set(ltv["platform"].dropna().unique()))
    )
    all_sources = sorted(
        set(cac["ad_source"].dropna().unique()).union(set(ltv["ad_source"].dropna().unique()))
    )

    st.sidebar.header("Filters")
    with st.sidebar.form("filters_form"):
        selected_countries = st.multiselect("Country", all_countries, default=all_countries)
        selected_platforms = st.multiselect("Platform", all_platforms, default=all_platforms)
        selected_sources = st.multiselect("Ad source", all_sources, default=all_sources)
        st.form_submit_button("Apply filters", use_container_width=True)

    cac_f, ltv_f = apply_filters(cac, ltv, selected_countries, selected_platforms, selected_sources)

    if cac_f.empty and ltv_f.empty:
        st.warning("No data matches the selected filters. Try broadening your selection.")
        st.stop()

    # ── KPIs ──────────────────────────────────────────────────────────────────
    kpis = build_kpis(cac_f, ltv_f)
    overview = build_overview_data(cac_f, ltv_f)
    ts = build_time_series(cac_f, ltv_f)

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Total Spend", fmt_money(kpis["total_spend"]))
    m2.metric("Total Revenue", fmt_money(kpis["total_revenue"]))
    m3.metric("Total LTV", fmt_money(kpis["total_ltv"]))
    m4.metric("New Customers", fmt_num(kpis["total_customers"]))
    m5.metric("Overall CAC", fmt_money(kpis["overall_cac"]))
    m6.metric("Avg LTV", fmt_money(kpis["avg_ltv"]))

    # ── Dynamic status note (replaces the hardcoded dev comment) ─────────────
    ltv_record_count = len(ltv_f)
    st.markdown(
        f'<div class="small-note">'
        f'{ltv_record_count:,} LTV records · '
        f'{fmt_num(kpis["total_customers"])} new customers · '
        f'LTV/CAC ratio: {fmt_num(kpis["ltv_cac_ratio"])}x'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Charts ────────────────────────────────────────────────────────────────
    left, right = st.columns(2)
    with left:
        st.plotly_chart(make_overview_bar(overview), use_container_width=True)
    with right:
        if ts.empty:
            st.info("No date data available for the monthly tracking chart.")
        else:
            st.plotly_chart(make_tracking_line(ts), use_container_width=True)

    # ── Overview table ────────────────────────────────────────────────────────
    st.subheader("Overview table")
    table_df = top_table(overview)
    st.dataframe(table_df, use_container_width=True, hide_index=True)

    csv = table_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Download overview CSV",
        data=csv,
        file_name="marketing_overview.csv",
        mime="text/csv",
        use_container_width=False,
    )


if __name__ == "__main__":
    main()