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

    # "campaign" is used here because loaders.py renames "campaign_name" to "campaign"
    for df in [cac, ltv, ads]:
        for col in [
            "country",
            "platform",
            "ad_source",
            "campaign",
            "campaign_id",
        ]:
            if col in df.columns:
                df[col] = df[col].astype(str)

    numeric_cac = [
        "new_customers",
        "total_spend_usd",
        "cac_usd",
    ]

    numeric_ltv = [
        "total_revenue",
        "purchase_count",
        "ltv_usd",
    ]

    for col in numeric_cac:
        if col in cac.columns:
            cac[col] = pd.to_numeric(cac[col], errors="coerce")

    for col in numeric_ltv:
        if col in ltv.columns:
            ltv[col] = pd.to_numeric(ltv[col], errors="coerce")

    if "user_id" in ltv.columns:
        ltv["user_id"] = ltv["user_id"].astype(str)

    if "campaign_start_date" in ads.columns:
        ads["campaign_start_date"] = pd.to_datetime(ads["campaign_start_date"], errors="coerce")

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
            customers=("new_customers", "sum"),
            avg_cac=("cac_usd", "mean"),
        )
    )
    revenue = (
        ltv_df.groupby(group_col, as_index=False)
        .agg(
            total_revenue=("total_revenue", "sum"),
            total_ltv=("ltv_usd", "sum"),
            purchases=("purchase_count", "sum"),
            users=("user_id", "nunique"),
        )
    )
    result = spend.merge(
        revenue,
        on=group_col,
        how="outer",
    ).fillna(0)

    result["ltv_cac_ratio"] = result.apply(
        lambda x: safe_div(
            x["total_ltv"],
            x["total_spend"],
        ),
        axis=1,
    )
    result["profit"] = (
            result["total_ltv"] - result["total_spend"]
    )
    result = result.sort_values(
        "total_ltv",
        ascending=False,
    )
    return result


def draw_chart(df, group_col):
    chart = df.melt(
        id_vars=group_col,
        value_vars=[
            "total_spend",
            "total_ltv",
        ],
        var_name="metric",
        value_name="value",
    )
    chart["metric"] = chart["metric"].replace(
        {
            "total_spend": "Spend",
            "total_ltv": "LTV",
        }
    )
    fig = px.bar(
        chart,
        x=group_col,
        y="value",
        color="metric",
        barmode="group",
        template="plotly_white",
    )
    fig.update_layout(
        height=450,
        yaxis_title="USD",
        xaxis_title="",
    )
    return fig


def draw_line_chart(ads_df, ltv_df, granularity="Month"):
    # Map selection to pandas frequency strings
    freq_map = {
        "Day": "D",
        "Week": "W",
        "Month": "M",
        "Quarter": "Q"
    }
    freq = freq_map.get(granularity, "M")

    # 1. Group LTV data by the selected frequency
    ltv_df = ltv_df.copy()
    ltv_df["date_group"] = pd.to_datetime(ltv_df["first_purchase_date"]).dt.to_period(freq).dt.to_timestamp()
    ltv_trend = ltv_df.groupby("date_group", as_index=False)[["total_revenue", "ltv_usd"]].sum()

    # 2. Group raw ADS data by the selected frequency for the exact spend spikes
    ads_df = ads_df.copy()
    ads_df["date_group"] = ads_df["campaign_start_date"].dt.to_period(freq).dt.to_timestamp()
    cac_trend = ads_df.groupby("date_group", as_index=False)["spend_usd"].sum()
    cac_trend = cac_trend.rename(columns={"spend_usd": "total_spend_usd"})

    # 3. Merge, sort, and reshape
    trend = pd.merge(cac_trend, ltv_trend, on="date_group", how="outer").fillna(0)
    trend = trend.sort_values("date_group")

    chart_data = trend.melt(
        id_vars="date_group",
        value_vars=["total_spend_usd", "total_revenue", "ltv_usd"],
        var_name="Metric",
        value_name="Value"
    )
    chart_data["Metric"] = chart_data["Metric"].replace({
        "total_spend_usd": "Spend",
        "total_revenue": "Revenue",
        "ltv_usd": "LTV"
    })

    # 4. Draw chart
    fig = px.line(
        chart_data,
        x="date_group",
        y="Value",
        color="Metric",
        template="plotly_white",
        markers=(granularity != "Day")  # Hide markers on 'Day' to prevent clutter
    )

    fig.update_layout(
        height=350,
        yaxis_title="USD",
        xaxis_title="",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    # Dynamic axis formatting based on granularity
    if granularity == "Month":
        fig.update_xaxes(dtick="M1", tickformat="%b %Y")
    elif granularity == "Quarter":
        fig.update_xaxes(dtick="M3", tickformat="Q%q %Y")
    else:
        fig.update_xaxes(dtick=None, tickformat=None)  # Let Plotly handle days/weeks auto-scaling

    return fig


st.title("📊 LTV vs CAC Dashboard")

if not CAC_FILE.exists():
    st.error("cac.csv not found")
    st.stop()

if not LTV_FILE.exists():
    st.error("ltv.csv not found")
    st.stop()

cac, ltv, ads = load_data()

if cac.empty:
    st.error("cac.csv contains no data")
    st.stop()

if ltv.empty:
    st.error("ltv.csv contains no data")
    st.stop()

st.sidebar.header("Filters")
countries = sorted(
    list(
        set(cac["country"].dropna())
        | set(ltv["country"].dropna())
    )
)
platforms = sorted(
    list(
        set(cac["platform"].dropna())
        | set(ltv["platform"].dropna())
    )
)
sources = sorted(
    list(
        set(cac["ad_source"].dropna())
        | set(ltv["ad_source"].dropna())
    )
)

selected_country = st.sidebar.multiselect(
    "Country",
    countries,
    default=countries,
)
selected_platform = st.sidebar.multiselect(
    "Platform",
    platforms,
    default=platforms,
)
selected_source = st.sidebar.multiselect(
    "Ad Source",
    sources,
    default=sources,
)

# Apply filters
cac = cac[
    cac["country"].isin(selected_country)
    & cac["platform"].isin(selected_platform)
    & cac["ad_source"].isin(selected_source)
    ]
ltv = ltv[
    ltv["country"].isin(selected_country)
    & ltv["platform"].isin(selected_platform)
    & ltv["ad_source"].isin(selected_source)
    ]
ads = ads[
    ads["country"].isin(selected_country)
    & ads["platform"].isin(selected_platform)
    & ads["ad_source"].isin(selected_source)
    ]

total_spend = cac["total_spend_usd"].sum()
total_customers = cac["new_customers"].sum()
overall_cac = safe_div(
    total_spend,
    total_customers,
)

total_ltv = ltv["ltv_usd"].sum()
total_revenue = ltv["total_revenue"].sum()
users = ltv["user_id"].nunique()
avg_ltv = safe_div(
    total_ltv,
    users,
)

ratio = safe_div(
    avg_ltv,
    overall_cac,
)

c1, c2, c3, c4, c5, c6 = st.columns(6)

c1.metric(
    "Spend",
    format_short_currency(total_spend),
)
c2.metric(
    "Revenue",
    format_short_currency(total_revenue),
)
c3.metric(
    "LTV",
    format_short_currency(total_ltv),
)
c4.metric(
    "Customers",
    f"{int(total_customers):,}",
)

cac_display = format_short_currency(overall_cac)

ratio_display = (
    f"{ratio:.2f}x"
    if not pd.isna(ratio)
    else "-"
)

c5.metric(
    "CAC",
    cac_display,
)

c6.metric(
    "LTV/CAC",
    ratio_display,
)

st.divider()

# Adding the Granularity Filter UI
col1, col2 = st.columns([1, 2])
with col1:
    st.subheader("📈 Dynamic Tracking")
with col2:
    time_grain = st.radio(
        "Granularity:",
        ["Day", "Week", "Month", "Quarter"],
        index=2,  # Defaults to "Month"
        horizontal=True,
        label_visibility="collapsed"
    )

st.plotly_chart(draw_line_chart(ads, ltv, granularity=time_grain), width="stretch")

st.divider()

tab1, tab2, tab3 = st.tabs(
    [
        "📱 Platform",
        "📢 Ad Source",
        "🌍 Country",
    ]
)

with tab1:
    st.subheader("Platform Breakdown")
    platform_df = build_summary(
        cac,
        ltv,
        "platform",
    )
    st.plotly_chart(
        draw_chart(
            platform_df,
            "platform",
        ),
        width="stretch",
    )
    st.dataframe(
        platform_df.round(2),
        width="stretch",
        hide_index=True,
    )

with tab2:
    st.subheader("Ad Source Breakdown")
    source_df = build_summary(
        cac,
        ltv,
        "ad_source",
    )
    st.plotly_chart(
        draw_chart(
            source_df,
            "ad_source",
        ),
        width="stretch",
    )
    st.dataframe(
        source_df.round(2),
        width="stretch",
        hide_index=True,
    )

with tab3:
    st.subheader("Country Breakdown")
    country_df = build_summary(
        cac,
        ltv,
        "country",
    )
    st.plotly_chart(
        draw_chart(
            country_df,
            "country",
        ),
        width="stretch",
    )
    st.dataframe(
        country_df.round(2),
        width="stretch",
        hide_index=True,
    )