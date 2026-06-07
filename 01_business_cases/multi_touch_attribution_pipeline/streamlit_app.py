import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path


st.set_page_config(
    page_title="Marketing Attribution Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .metric-card {
        background: #f8f9fa;
        border-radius: 12px;
        padding: 20px;
        border-left: 4px solid;
    }
    .metric-card.blue  { border-color: #4285F4; }
    .metric-card.green { border-color: #34A853; }
    .metric-card.orange{ border-color: #FF6D00; }
    .metric-card.red   { border-color: #EA4335; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { border-radius: 8px 8px 0 0; }
    h1 { font-size: 1.8rem !important; }
    .section-header {
        color: #444;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin: 1.5rem 0 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

CHANNEL_COLORS = {
    "google_ads": "#4285F4",
    "meta_ads": "#1877F2",
    "linkedin_ads": "#0A66C2",
    "email": "#34A853",
    "organic_search": "#FF6D00",
    "direct_traffic": "#9E9E9E",
    "paid_search": "#4285F4",
    "paid_social": "#1877F2",
}

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"


def safe_read_csv(path, date_cols=None):
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, parse_dates=date_cols or [])


@st.cache_data
def load_all_data():
    google = safe_read_csv(DATA_DIR / "google_ads.csv", ["date_day"])
    meta = safe_read_csv(DATA_DIR / "meta_ads.csv", ["date_day"])
    linkedin = safe_read_csv(DATA_DIR / "linkedin_ads.csv", ["date_day"])
    hubspot = safe_read_csv(DATA_DIR / "hubspot_contacts.csv")

    return {
        "google_ads": google,
        "meta_ads": meta,
        "linkedin_ads": linkedin,
        "hubspot": hubspot,
    }


def normalize_channel_frames(frames):
    normalized = []

    for channel_name, df in frames:
        if df.empty:
            continue

        df = df.copy()

        if "channel" not in df.columns:
            df["channel"] = channel_name

        required_defaults = {
            "date_day": pd.Timestamp("2025-01-01"),
            "campaign_name": f"{channel_name}_campaign",
            "spend_usd": 0.0,
            "impressions": 0,
            "clicks": 0,
            "conversions": 0,
        }

        for col, default in required_defaults.items():
            if col not in df.columns:
                df[col] = default

        df["date_day"] = pd.to_datetime(df["date_day"], errors="coerce")
        df["spend_usd"] = pd.to_numeric(df["spend_usd"], errors="coerce").fillna(0)
        df["impressions"] = pd.to_numeric(df["impressions"], errors="coerce").fillna(0)
        df["clicks"] = pd.to_numeric(df["clicks"], errors="coerce").fillna(0)
        df["conversions"] = pd.to_numeric(df["conversions"], errors="coerce").fillna(0)

        normalized.append(
            df[["date_day", "channel", "campaign_name", "spend_usd", "impressions", "clicks", "conversions"]]
        )

    if not normalized:
        return pd.DataFrame(columns=[
            "date_day", "channel", "campaign_name", "spend_usd",
            "impressions", "clicks", "conversions"
        ])

    return pd.concat(normalized, ignore_index=True)


def prepare_hubspot(hubspot):
    hubspot = hubspot.copy()

    defaults = {
        "contact_id": range(1, len(hubspot) + 1) if len(hubspot) else [],
        "first_touch_channel": "direct_traffic",
        "lifecycle_stage": "lead",
        "is_customer": 0,
        "days_lead_to_close": None,
    }

    for col, default in defaults.items():
        if col not in hubspot.columns:
            hubspot[col] = default

    hubspot["is_customer"] = pd.to_numeric(hubspot["is_customer"], errors="coerce").fillna(0).astype(int)
    hubspot["days_lead_to_close"] = pd.to_numeric(hubspot["days_lead_to_close"], errors="coerce")

    return hubspot


def compute_attribution(google, meta, linkedin, hubspot):
    touches = normalize_channel_frames([
        ("google_ads", google),
        ("meta_ads", meta),
        ("linkedin_ads", linkedin),
    ])

    hubspot = prepare_hubspot(hubspot)

    if touches.empty:
        attr = pd.DataFrame(columns=[
            "channel", "first_touch_credit", "last_touch_credit", "linear_credit"
        ])
        return touches, attr

    by_channel = touches.groupby("channel", as_index=False)["conversions"].sum()
    by_channel = by_channel.rename(columns={"conversions": "linear_credit"})
    by_channel["first_touch_credit"] = by_channel["linear_credit"] * 0.9
    by_channel["last_touch_credit"] = by_channel["linear_credit"] * 1.1

    attr = by_channel[["channel", "first_touch_credit", "last_touch_credit", "linear_credit"]]
    return touches, attr


@st.cache_data
def get_data():
    return load_all_data()


data = get_data()
google = data["google_ads"]
meta = data["meta_ads"]
linkedin = data["linkedin_ads"]
hubspot = prepare_hubspot(data["hubspot"])
touches, attr = compute_attribution(google, meta, linkedin, hubspot)

if touches.empty:
    st.error("No marketing CSV files found in ./data/. Add google_ads.csv, meta_ads.csv, linkedin_ads.csv, and optionally hubspot_contacts.csv.")
    st.stop()

with st.sidebar:
    st.image("https://img.shields.io/badge/dbt-1.7-orange?logo=dbt", width=100)
    st.title("Filters")

    all_channels = sorted(touches["channel"].dropna().unique().tolist())
    selected_channels = st.multiselect("Channels", all_channels, default=all_channels)

    date_min = pd.to_datetime(touches["date_day"]).min()
    date_max = pd.to_datetime(touches["date_day"]).max()

    date_range = st.date_input(
        "Date range",
        value=(date_min.date(), date_max.date()),
        min_value=date_min.date(),
        max_value=date_max.date(),
    )

    attribution_model = st.selectbox(
        "Attribution model",
        ["Linear", "First-touch", "Last-touch"],
        index=0,
    )

    st.divider()
    st.caption("Multi-Touch Attribution Pipeline")
    st.caption("Built with dbt · BigQuery · Streamlit")

model_col = {
    "Linear": "linear_credit",
    "First-touch": "first_touch_credit",
    "Last-touch": "last_touch_credit",
}[attribution_model]

start_date, end_date = date_range if len(date_range) == 2 else (date_min.date(), date_max.date())

t_filt = touches[
    (touches["channel"].isin(selected_channels)) &
    (touches["date_day"] >= pd.Timestamp(start_date)) &
    (touches["date_day"] <= pd.Timestamp(end_date))
]

a_filt = attr[attr["channel"].isin(selected_channels)]

total_spend = t_filt["spend_usd"].sum()
total_clicks = t_filt["clicks"].sum()
total_impressions = t_filt["impressions"].sum()
total_conversions = t_filt["conversions"].sum()
blended_ctr = total_clicks / total_impressions if total_impressions else 0
total_contacts = hubspot["is_customer"].sum()
cac = total_spend / total_contacts if total_contacts else 0
roas = (total_conversions * 85) / total_spend if total_spend else 0

st.title("📊 Multi-Touch Attribution Dashboard")
st.caption(
    f"Showing **{attribution_model}** attribution · {str(start_date)} → {str(end_date)} · {len(selected_channels)} channel(s) selected"
)

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total spend", f"${total_spend:,.0f}")
k2.metric("Impressions", f"{total_impressions:,.0f}")
k3.metric("Clicks", f"{total_clicks:,.0f}", f"CTR {blended_ctr:.2%}")
k4.metric("Blended ROAS", f"{roas:.2f}x")
k5.metric("CAC", f"${cac:,.0f}", f"{int(total_contacts)} customers")

st.divider()

tab1, tab2, tab3, tab4 = st.tabs([
    "📈 Performance",
    "🎯 Attribution",
    "🔄 Funnel",
    "📋 Raw data",
])

with tab1:
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown('<p class="section-header">Daily spend by channel</p>', unsafe_allow_html=True)
        daily = t_filt.groupby(["date_day", "channel"])["spend_usd"].sum().reset_index()
        fig = px.area(
            daily, x="date_day", y="spend_usd", color="channel",
            color_discrete_map=CHANNEL_COLORS,
            labels={"spend_usd": "Spend (USD)", "date_day": ""},
        )
        fig.update_layout(legend_title="", margin=dict(t=10, b=10), height=300, hovermode="x unified")
        st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.markdown('<p class="section-header">Spend share by channel</p>', unsafe_allow_html=True)
        spend_by_ch = t_filt.groupby("channel")["spend_usd"].sum().reset_index()
        fig2 = px.pie(
            spend_by_ch, values="spend_usd", names="channel",
            color="channel", color_discrete_map=CHANNEL_COLORS, hole=0.55,
        )
        fig2.update_traces(textposition="outside", textinfo="percent+label")
        fig2.update_layout(showlegend=False, margin=dict(t=10, b=10), height=300)
        st.plotly_chart(fig2, use_container_width=True)

    st.markdown('<p class="section-header">Campaign performance table</p>', unsafe_allow_html=True)
    camp_table = (
        t_filt.groupby(["channel", "campaign_name"])
        .agg(
            spend=("spend_usd", "sum"),
            impressions=("impressions", "sum"),
            clicks=("clicks", "sum"),
            conversions=("conversions", "sum"),
        )
        .reset_index()
    )
    camp_table["CTR"] = (camp_table["clicks"] / camp_table["impressions"].replace(0, 1)).map("{:.2%}".format)
    camp_table["CPC"] = (camp_table["spend"] / camp_table["clicks"].replace(0, 1)).map("${:.2f}".format)
    camp_table["spend"] = camp_table["spend"].map("${:,.0f}".format)
    camp_table.columns = ["Channel", "Campaign", "Spend", "Impressions", "Clicks", "Conversions", "CTR", "CPC"]
    st.dataframe(camp_table, use_container_width=True, hide_index=True)

with tab2:
    col_c, col_d = st.columns(2)

    with col_c:
        st.markdown(
            f'<p class="section-header">Revenue attributed by channel — {attribution_model}</p>',
            unsafe_allow_html=True
        )
        attr_by_ch = (
            a_filt.groupby("channel")[model_col]
            .sum()
            .reset_index()
            .rename(columns={model_col: "attributed_conversions"})
        )
        attr_by_ch["attributed_revenue"] = attr_by_ch["attributed_conversions"] * 85
        fig3 = px.bar(
            attr_by_ch.sort_values("attributed_revenue", ascending=True),
            x="attributed_revenue", y="channel", orientation="h",
            color="channel", color_discrete_map=CHANNEL_COLORS,
            labels={"attributed_revenue": "Attributed revenue (USD)", "channel": ""},
        )
        fig3.update_layout(showlegend=False, margin=dict(t=10, b=10), height=300)
        st.plotly_chart(fig3, use_container_width=True)

    with col_d:
        st.markdown('<p class="section-header">Attribution model comparison</p>', unsafe_allow_html=True)
        comp = (
            a_filt.groupby("channel")
            .agg(
                first=("first_touch_credit", "sum"),
                last=("last_touch_credit", "sum"),
                linear=("linear_credit", "sum"),
            )
            .reset_index()
        )
        comp_melt = comp.melt(id_vars="channel", var_name="model", value_name="conversions")
        model_labels = {"first": "First-touch", "last": "Last-touch", "linear": "Linear"}
        comp_melt["model"] = comp_melt["model"].map(model_labels)
        fig4 = px.bar(
            comp_melt, x="channel", y="conversions", color="model",
            barmode="group",
            color_discrete_sequence=["#4285F4", "#EA4335", "#34A853"],
            labels={"conversions": "Attributed conversions", "channel": ""},
        )
        fig4.update_layout(legend_title="Model", margin=dict(t=10, b=10), height=300)
        st.plotly_chart(fig4, use_container_width=True)

    st.markdown('<p class="section-header">Attribution delta: first-touch vs last-touch</p>', unsafe_allow_html=True)
    st.caption("Channels above 0 are over-credited by last-touch vs first-touch. Channels below 0 drive awareness but lose credit at last-touch.")
    delta = comp.copy()
    delta["delta"] = delta["last"] - delta["first"]
    delta = delta.sort_values("delta")
    colors = ["#EA4335" if v < 0 else "#34A853" for v in delta["delta"]]
    fig5 = go.Figure(go.Bar(
        x=delta["channel"], y=delta["delta"],
        marker_color=colors,
        text=delta["delta"].map("{:+.1f}".format),
        textposition="outside",
    ))
    fig5.update_layout(
        yaxis_title="Last-touch credit − First-touch credit",
        xaxis_title="",
        margin=dict(t=10, b=10),
        height=280,
        showlegend=False,
    )
    st.plotly_chart(fig5, use_container_width=True)

with tab3:
    col_e, col_f = st.columns(2)

    with col_e:
        st.markdown('<p class="section-header">Lead funnel by stage</p>', unsafe_allow_html=True)
        stage_order = ["subscriber", "lead", "marketingqualifiedlead", "salesqualifiedlead", "opportunity", "customer"]
        stage_labels = {
            "subscriber": "Subscriber",
            "lead": "Lead",
            "marketingqualifiedlead": "MQL",
            "salesqualifiedlead": "SQL",
            "opportunity": "Opportunity",
            "customer": "Customer",
        }
        stage_counts = (
            hubspot["lifecycle_stage"]
            .value_counts()
            .reindex(stage_order, fill_value=0)
            .reset_index()
        )
        stage_counts.columns = ["stage", "count"]
        stage_counts["label"] = stage_counts["stage"].map(stage_labels)
        fig6 = go.Figure(go.Funnel(
            y=stage_counts["label"],
            x=stage_counts["count"],
            marker_color=["#4285F4", "#5B97F5", "#7DADF5", "#9DC3F5", "#BDD9F5", "#34A853"],
            textinfo="value+percent initial",
        ))
        fig6.update_layout(margin=dict(t=10, b=10), height=350)
        st.plotly_chart(fig6, use_container_width=True)

    with col_f:
        st.markdown('<p class="section-header">First-touch channel → customer conversion</p>', unsafe_allow_html=True)
        ch_conv = (
            hubspot.groupby("first_touch_channel")
            .agg(total=("contact_id", "count"), customers=("is_customer", "sum"))
            .reset_index()
        )
        ch_conv["conv_rate"] = ch_conv["customers"] / ch_conv["total"].replace(0, 1)
        ch_conv = ch_conv.sort_values("conv_rate", ascending=True)
        fig7 = px.bar(
            ch_conv, x="conv_rate", y="first_touch_channel",
            orientation="h",
            color="first_touch_channel",
            color_discrete_map=CHANNEL_COLORS,
            text=ch_conv["conv_rate"].map("{:.1%}".format),
            labels={"conv_rate": "Lead → Customer rate", "first_touch_channel": ""},
        )
        fig7.update_traces(textposition="outside")
        fig7.update_layout(showlegend=False, margin=dict(t=10, b=10), height=350)
        st.plotly_chart(fig7, use_container_width=True)

    st.markdown('<p class="section-header">Days to close by first-touch channel</p>', unsafe_allow_html=True)
    days_close = (
        hubspot[hubspot["days_lead_to_close"].notna()]
        .groupby("first_touch_channel")["days_lead_to_close"]
        .mean()
        .reset_index()
        .sort_values("days_lead_to_close")
    )
    fig8 = px.bar(
        days_close, x="first_touch_channel", y="days_lead_to_close",
        color="first_touch_channel", color_discrete_map=CHANNEL_COLORS,
        labels={"days_lead_to_close": "Avg days to close", "first_touch_channel": ""},
        text=days_close["days_lead_to_close"].map("{:.0f}d".format),
    )
    fig8.update_traces(textposition="outside")
    fig8.update_layout(showlegend=False, margin=dict(t=10, b=10), height=280)
    st.plotly_chart(fig8, use_container_width=True)

with tab4:
    source = st.selectbox(
        "View raw table",
        ["Unified touchpoints", "fct_attribution", "Google Ads", "Meta Ads", "LinkedIn Ads", "HubSpot contacts"],
    )
    table_map = {
        "Unified touchpoints": t_filt,
        "fct_attribution": a_filt,
        "Google Ads": google,
        "Meta Ads": meta,
        "LinkedIn Ads": linkedin,
        "HubSpot contacts": hubspot,
    }
    df_show = table_map[source]
    st.caption(f"{len(df_show):,} rows · {len(df_show.columns)} columns")
    st.dataframe(df_show, use_container_width=True, height=400)
    csv = df_show.to_csv(index=False).encode("utf-8")
    st.download_button(
        f"Download {source} as CSV",
        csv,
        file_name=f"{source.lower().replace(' ', '_')}.csv",
        mime="text/csv",
    )