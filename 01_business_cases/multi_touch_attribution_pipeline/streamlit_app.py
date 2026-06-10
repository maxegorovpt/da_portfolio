from pathlib import Path
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
import sys

st.set_page_config(
    page_title="LTV vs CAC Dashboard",
    page_icon="📊",
    layout="wide",
)

# Setup paths and import your loader
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
from src.loaders import load_ads_data

DATA_DIR = BASE_DIR / "data" / "calculations"
SOURCE_DIR = BASE_DIR / "data" / "source_data"  # Path to your raw ads folder
CAC_FILE = DATA_DIR / "cac.csv"
LTV_FILE = DATA_DIR / "ltv.csv"


@st.cache_data
def load_data():
    cac = pd.read_csv(CAC_FILE)
    ltv = pd.read_csv(LTV_FILE)
    ads = load_ads_data(SOURCE_DIR)

    # 1. Filter everything strictly to 2025
    if "first_purchase_date" in cac.columns:
        cac["first_purchase_date"] = pd.to_datetime(cac["first_purchase_date"], errors="coerce")
        cac = cac[cac["first_purchase_date"].dt.year == 2025]

    if "first_purchase_date" in ltv.columns:
        ltv["first_purchase_date"] = pd.to_datetime(ltv["first_purchase_date"], errors="coerce")
        ltv = ltv[ltv["first_purchase_date"].dt.year == 2025]

    if "campaign_start_date" in ads.columns:
        ads["campaign_start_date"] = pd.to_datetime(ads["campaign_start_date"], errors="coerce")
        ads = ads[ads["campaign_start_date"].dt.year == 2025]

    for df in [cac, ltv, ads]:
        for col in ["country", "platform", "ad_source", "campaign", "campaign_id"]:
            if col in df.columns:
                df[col] = df[col].astype(str)

    numeric_cac = ["new_customers", "total_spend_usd", "cac_usd"]
    numeric_ltv = ["total_revenue", "purchase_count", "ltv_usd"]

    for col in numeric_cac:
        if col in cac.columns:
            cac[col] = pd.to_numeric(cac[col], errors="coerce")

    for col in numeric_ltv:
        if col in ltv.columns:
            ltv[col] = pd.to_numeric(ltv[col], errors="coerce")

    if "user_id" in ltv.columns:
        ltv["user_id"] = ltv["user_id"].astype(str)

    return cac, ltv, ads


def safe_div(a, b):
    if b == 0 or pd.isna(b):
        return np.nan
    return a / b


def format_short_currency(value):
    if pd.isna(value):
        return "-"

    abs_value = abs(value)
    if abs_value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"
    if abs_value >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"
    if abs_value >= 1_000:
        return f"${value / 1_000:.2f}K"

    return f"${value:,.0f}"


def build_summary(cac_df, ltv_df, group_col):
    spend = (
        cac_df.groupby(group_col, as_index=False)
        .agg(
            total_spend=("total_spend_usd", "sum"),
            customers=("new_customers", "sum")
        )
    )
    # CAC = Spend / Customers
    spend["avg_cac"] = np.where(spend["customers"] > 0, spend["total_spend"] / spend["customers"], np.nan)

    revenue = (
        ltv_df.groupby(group_col, as_index=False)
        .agg(
            total_revenue=("total_revenue", "sum"),
            users=("user_id", "nunique"),
        )
    )
    # LTV = Revenue / Customers
    revenue["avg_ltv"] = np.where(revenue["users"] > 0, revenue["total_revenue"] / revenue["users"], np.nan)

    result = spend.merge(revenue, on=group_col, how="outer").fillna(0)

    result["ltv_cac_ratio"] = result.apply(lambda x: safe_div(x["avg_ltv"], x["avg_cac"]), axis=1)
    result["profit"] = result["total_revenue"] - result["total_spend"]
    result = result.sort_values("total_revenue", ascending=False)

    return result


def draw_chart(df, group_col):
    # Totals Chart
    chart = df.melt(
        id_vars=group_col,
        value_vars=["total_spend", "total_revenue"],
        var_name="metric",
        value_name="value",
    )
    chart["metric"] = chart["metric"].replace({"total_spend": "Spend", "total_revenue": "Revenue"})
    fig = px.bar(
        chart, x=group_col, y="value", color="metric", barmode="group", template="plotly_white"
    )
    fig.update_layout(height=400, yaxis_title="Total USD", xaxis_title="")
    return fig


def draw_unit_chart(df, group_col):
    # Separate CAC vs LTV Unit Chart
    chart = df.melt(
        id_vars=group_col,
        value_vars=["avg_cac", "avg_ltv"],
        var_name="metric",
        value_name="value",
    )
    chart["metric"] = chart["metric"].replace({"avg_cac": "CAC", "avg_ltv": "LTV"})
    fig = px.bar(
        chart, x=group_col, y="value", color="metric", barmode="group", template="plotly_white",
        color_discrete_sequence=["#EF553B", "#00CC96"]
    )
    fig.update_layout(height=400, yaxis_title="USD per User", xaxis_title="")
    return fig


def draw_tracking_charts(ads_df, ltv_df, granularity="Month"):
    freq_map = {"Day": "D", "Week": "W", "Month": "M", "Quarter": "Q"}
    freq = freq_map.get(granularity, "M")

    # 1. Group LTV data (Revenue & Unique Users)
    ltv_df = ltv_df.copy()
    ltv_df["date_group"] = pd.to_datetime(ltv_df["first_purchase_date"]).dt.to_period(freq).dt.to_timestamp()
    ltv_trend = ltv_df.groupby("date_group", as_index=False).agg(
        total_revenue=("total_revenue", "sum"),
        users=("user_id", "nunique")
    )

    # 2. Group Ads data (Spend)
    ads_df = ads_df.copy()
    ads_df["date_group"] = pd.to_datetime(ads_df["campaign_start_date"]).dt.to_period(freq).dt.to_timestamp()
    cac_trend = ads_df.groupby("date_group", as_index=False)["spend_usd"].sum()
    cac_trend = cac_trend.rename(columns={"spend_usd": "total_spend"})

    # 3. Merge
    trend = pd.merge(cac_trend, ltv_trend, on="date_group", how="outer").fillna(0).sort_values("date_group")

    # 4. Calculate unit economics dynamically over time (LTV = rev/users, CAC = spend/users)
    trend["CAC"] = np.where(trend["users"] > 0, trend["total_spend"] / trend["users"], np.nan)
    trend["LTV"] = np.where(trend["users"] > 0, trend["total_revenue"] / trend["users"], np.nan)

    # --- Chart 1: Totals (Spend vs Revenue) ---
    chart1_data = trend.melt(id_vars="date_group", value_vars=["total_spend", "total_revenue"], var_name="Metric",
                             value_name="Value")
    chart1_data["Metric"] = chart1_data["Metric"].replace({"total_spend": "Spend", "total_revenue": "Revenue"})

    fig1 = px.line(chart1_data, x="date_group", y="Value", color="Metric", template="plotly_white",
                   markers=(granularity != "Day"))
    fig1.update_layout(height=350, yaxis_title="Total USD", xaxis_title="",
                       legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))

    # --- Chart 2: Unit Economics (CAC vs LTV) ---
    chart2_data = trend.melt(id_vars="date_group", value_vars=["CAC", "LTV"], var_name="Metric", value_name="Value")

    fig2 = px.line(
        chart2_data, x="date_group", y="Value", color="Metric", template="plotly_white", markers=(granularity != "Day"),
        color_discrete_sequence=["#EF553B", "#00CC96"]
    )
    fig2.update_layout(height=350, yaxis_title="USD per User", xaxis_title="",
                       legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))

    for fig in [fig1, fig2]:
        if granularity == "Month":
            fig.update_xaxes(dtick="M1", tickformat="%b %Y")
        elif granularity == "Quarter":
            fig.update_xaxes(dtick="M3", tickformat="Q%q %Y")
        else:
            fig.update_xaxes(dtick=None, tickformat=None)

    return fig1, fig2


st.title("📊 LTV vs CAC Dashboard")

if not CAC_FILE.exists() or not LTV_FILE.exists():
    st.error("Missing calculated files.")
    st.stop()

cac, ltv, ads = load_data()

st.sidebar.header("Filters")
countries = sorted(list(set(cac["country"].dropna()) | set(ltv["country"].dropna())))
platforms = sorted(list(set(cac["platform"].dropna()) | set(ltv["platform"].dropna())))
sources = sorted(list(set(cac["ad_source"].dropna()) | set(ltv["ad_source"].dropna())))

selected_country = st.sidebar.multiselect("Country", countries, default=countries)
selected_platform = st.sidebar.multiselect("Platform", platforms, default=platforms)
selected_source = st.sidebar.multiselect("Ad Source", sources, default=sources)

cac = cac[cac["country"].isin(selected_country) & cac["platform"].isin(selected_platform) & cac["ad_source"].isin(
    selected_source)]
ltv = ltv[ltv["country"].isin(selected_country) & ltv["platform"].isin(selected_platform) & ltv["ad_source"].isin(
    selected_source)]
ads = ads[ads["country"].isin(selected_country) & ads["platform"].isin(selected_platform) & ads["ad_source"].isin(
    selected_source)]

total_spend = cac["total_spend_usd"].sum()
total_customers = cac["new_customers"].sum()
overall_cac = safe_div(total_spend, total_customers)

total_revenue = ltv["total_revenue"].sum()
users = ltv["user_id"].nunique()

# LTV is now strictly average revenue per customer
avg_ltv = safe_div(total_revenue, users)
ratio = safe_div(avg_ltv, overall_cac)

c1, c2, c3, c4, c5, c6 = st.columns(6)

c1.metric("Spend", format_short_currency(total_spend))
c2.metric("Revenue", format_short_currency(total_revenue))
c3.metric("Avg LTV", format_short_currency(avg_ltv))
c4.metric("Customers", f"{int(total_customers):,}")
c5.metric("CAC", format_short_currency(overall_cac))
c6.metric("LTV/CAC", f"{ratio:.2f}x" if not pd.isna(ratio) else "-")

st.divider()

col1, col2 = st.columns([1, 2])
with col1:
    st.subheader("📈 Dynamic Tracking")
with col2:
    time_grain = st.radio(
        "Granularity:", ["Day", "Week", "Month", "Quarter"],
        index=2, horizontal=True, label_visibility="collapsed"
    )

fig_totals, fig_unit = draw_tracking_charts(ads, ltv, granularity=time_grain)

st.markdown("**Totals: Spend vs Revenue**")
st.plotly_chart(fig_totals, width="stretch")

st.markdown("**Unit Economics: CAC vs LTV over Time**")
st.plotly_chart(fig_unit, width="stretch")

st.divider()

tab1, tab2, tab3 = st.tabs(["📱 Platform", "📢 Ad Source", "🌍 Country"])

with tab1:
    st.subheader("Platform Breakdown")
    platform_df = build_summary(cac, ltv, "platform")
    colA, colB = st.columns(2)
    with colA:
        st.plotly_chart(draw_chart(platform_df, "platform"), width="stretch")
    with colB:
        st.plotly_chart(draw_unit_chart(platform_df, "platform"), width="stretch")
    st.dataframe(platform_df.round(2), width="stretch", hide_index=True)

with tab2:
    st.subheader("Ad Source Breakdown")
    source_df = build_summary(cac, ltv, "ad_source")
    colA, colB = st.columns(2)
    with colA:
        st.plotly_chart(draw_chart(source_df, "ad_source"), width="stretch")
    with colB:
        st.plotly_chart(draw_unit_chart(source_df, "ad_source"), width="stretch")
    st.dataframe(source_df.round(2), width="stretch", hide_index=True)

with tab3:
    st.subheader("Country Breakdown")
    country_df = build_summary(cac, ltv, "country")
    colA, colB = st.columns(2)
    with colA:
        st.plotly_chart(draw_chart(country_df, "country"), width="stretch")
    with colB:
        st.plotly_chart(draw_unit_chart(country_df, "country"), width="stretch")
    st.dataframe(country_df.round(2), width="stretch", hide_index=True)