from pathlib import Path
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(
    page_title="LTV vs CAC Dashboard",
    page_icon="📊",
    layout="wide",
)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "calculations"
CAC_FILE = DATA_DIR / "cac.csv"
LTV_FILE = DATA_DIR / "ltv.csv"


@st.cache_data
def load_data():
    cac = pd.read_csv(CAC_FILE)
    ltv = pd.read_csv(LTV_FILE)

    # "campaign" is used here because loaders.py renames "campaign_name" to "campaign"
    for df in [cac, ltv]:
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

    return cac, ltv


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


def draw_line_chart(cac_df, ltv_df):
    cac_trend = cac_df.groupby("first_purchase_date", as_index=False)["total_spend_usd"].sum()
    ltv_trend = ltv_df.groupby("first_purchase_date", as_index=False)[["total_revenue", "ltv_usd"]].sum()

    trend = pd.merge(cac_trend, ltv_trend, on="first_purchase_date", how="outer").fillna(0)
    trend = trend.sort_values("first_purchase_date")

    chart_data = trend.melt(
        id_vars="first_purchase_date",
        value_vars=["total_spend_usd", "total_revenue", "ltv_usd"],
        var_name="Metric",
        value_name="Value"
    )
    chart_data["Metric"] = chart_data["Metric"].replace({
        "total_spend_usd": "Spend",
        "total_revenue": "Revenue",
        "ltv_usd": "LTV"
    })

    fig = px.line(
        chart_data,
        x="first_purchase_date",
        y="Value",
        color="Metric",
        template="plotly_white",
    )
    fig.update_layout(
        height=350,
        yaxis_title="USD",
        xaxis_title="",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig


st.title("📊 LTV vs CAC Dashboard")

if not CAC_FILE.exists():
    st.error("cac.csv not found")
    st.stop()

if not LTV_FILE.exists():
    st.error("ltv.csv not found")
    st.stop()

cac, ltv = load_data()

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
st.subheader("📈 Dynamic Tracking")
st.plotly_chart(draw_line_chart(cac, ltv), width="stretch")
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