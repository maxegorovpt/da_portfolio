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

EU_CODES = [
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR",
    "DE", "GR", "HU", "IE", "IT", "LV", "LT", "LU", "MT", "NL",
    "PL", "PT", "RO", "SK", "SI", "ES", "SE",
]

EU_ISO3 = {
    "AT": "AUT", "BE": "BEL", "BG": "BGR", "HR": "HRV", "CY": "CYP",
    "CZ": "CZE", "DK": "DNK", "EE": "EST", "FI": "FIN", "FR": "FRA",
    "DE": "DEU", "GR": "GRC", "HU": "HUN", "IE": "IRL", "IT": "ITA",
    "LV": "LVA", "LT": "LTU", "LU": "LUX", "MT": "MLT", "NL": "NLD",
    "PL": "POL", "PT": "PRT", "RO": "ROU", "SK": "SVK", "SI": "SVN",
    "ES": "ESP", "SE": "SWE",
}

EU_NAMES = {
    "AT": "Austria", "BE": "Belgium", "BG": "Bulgaria", "HR": "Croatia", "CY": "Cyprus",
    "CZ": "Czechia", "DK": "Denmark", "EE": "Estonia", "FI": "Finland", "FR": "France",
    "DE": "Germany", "GR": "Greece", "HU": "Hungary", "IE": "Ireland", "IT": "Italy",
    "LV": "Latvia", "LT": "Lithuania", "LU": "Luxembourg", "MT": "Malta", "NL": "Netherlands",
    "PL": "Poland", "PT": "Portugal", "RO": "Romania", "SK": "Slovakia", "SI": "Slovenia",
    "ES": "Spain", "SE": "Sweden",
}


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
        [data-testid="stMetricValue"] { color: #f8fafc; font-weight: 700; }
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
    total_spend = cac_f["total_spend_usd"].sum()
    total_revenue = ltv_f["total_revenue"].sum()
    total_customers = cac_f["new_customers"].sum()
    overall_cac = safe_div(total_spend, total_customers)
    avg_ltv = ltv_f["ltv_usd"].mean()
    ltv_cac_ratio = safe_div(avg_ltv, overall_cac)
    return {
        "total_spend": total_spend,
        "total_revenue": total_revenue,
        "total_customers": total_customers,
        "overall_cac": overall_cac,
        "avg_ltv": avg_ltv,
        "ltv_cac_ratio": ltv_cac_ratio,
    }


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
            avg_ltv_usd=("ltv_usd", "mean"),
            users=("user_id", "nunique"),
        )
    )

    merged = cac_agg.merge(ltv_agg, on=dim, how="outer")
    for col in ["total_spend_usd", "new_customers", "total_revenue", "purchase_count", "users", "cac_usd", "avg_ltv_usd"]:
        if col in merged.columns:
            merged[col] = pd.to_numeric(merged[col], errors="coerce")
    merged[["total_spend_usd", "new_customers", "total_revenue", "purchase_count", "users"]] = merged[["total_spend_usd", "new_customers", "total_revenue", "purchase_count", "users"]].fillna(0)
    merged["ltv_cac_ratio"] = np.where(
        merged["cac_usd"] > 0,
        merged["avg_ltv_usd"] / merged["cac_usd"],
        np.nan,
    )
    merged["profit_gap"] = merged["avg_ltv_usd"] - merged["cac_usd"]
    return merged.sort_values("total_revenue", ascending=False)


def make_bar(df, x, y, title, color=None, text_auto=".2s"):
    fig = px.bar(
        df,
        x=x,
        y=y,
        color=color,
        text_auto=text_auto,
        title=title,
        template="plotly_white",
    )
    fig.update_traces(marker_line_width=0, hovertemplate="<b>%{x}</b><br>%{y:$,.2f}<extra></extra>")
    fig.update_layout(
        height=430,
        margin=dict(l=10, r=10, t=60, b=10),
        title_font=dict(size=18),
        legend_title_text="",
    )
    return fig


def make_scatter(df, dim):
    fig = px.scatter(
        df,
        x="cac_usd",
        y="avg_ltv_usd",
        size="total_revenue",
        color="ltv_cac_ratio",
        hover_name=dim,
        color_continuous_scale="Tealgrn",
        template="plotly_white",
        title=f"LTV vs CAC by {dim.replace('_', ' ').title()}",
        labels={"cac_usd": "CAC ($)", "avg_ltv_usd": "Avg LTV ($)", "ltv_cac_ratio": "LTV/CAC"},
    )
    max_axis = np.nanmax([
        df["cac_usd"].max() if not df.empty else 0,
        df["avg_ltv_usd"].max() if not df.empty else 0,
    ])
    if pd.notna(max_axis) and max_axis > 0:
        fig.add_trace(
            go.Scatter(
                x=[0, max_axis],
                y=[0, max_axis],
                mode="lines",
                name="LTV = CAC",
                line=dict(color="#64748b", dash="dash"),
            )
        )
    fig.update_layout(
        height=450,
        margin=dict(l=10, r=10, t=60, b=10),
        title_font=dict(size=18),
        coloraxis_colorbar=dict(title="LTV/CAC"),
    )
    return fig


def make_eu_map(cac_f, ltv_f):
    eu_cac = cac_f[cac_f["country"].isin(EU_CODES)]
    eu_ltv = ltv_f[ltv_f["country"].isin(EU_CODES)]
    if eu_cac.empty or eu_ltv.empty:
        return None

    cac_ct = eu_cac.groupby("country", as_index=False).agg(
        total_spend_usd=("total_spend_usd", "sum"),
        new_customers=("new_customers", "sum"),
    )
    cac_ct["cac_usd"] = np.where(
        cac_ct["new_customers"] > 0,
        cac_ct["total_spend_usd"] / cac_ct["new_customers"],
        np.nan,
    )

    ltv_ct = eu_ltv.groupby("country", as_index=False).agg(
        avg_ltv_usd=("ltv_usd", "mean"),
        total_revenue=("total_revenue", "sum"),
    )

    eu = cac_ct.merge(ltv_ct, on="country", how="inner")
    eu["ltv_cac_ratio"] = np.where(
        eu["cac_usd"] > 0,
        eu["avg_ltv_usd"] / eu["cac_usd"],
        np.nan,
    )
    eu["country_name"] = eu["country"].map(EU_NAMES)
    eu["iso3"] = eu["country"].map(EU_ISO3)

    fig = px.choropleth(
        eu,
        locations="iso3",
        locationmode="ISO-3",
        color="ltv_cac_ratio",
        hover_name="country_name",
        hover_data={
            "cac_usd": ":.2f",
            "avg_ltv_usd": ":.2f",
            "ltv_cac_ratio": ":.2f",
            "country": False,
            "iso3": False,
        },
        color_continuous_scale="Viridis",
        projection="mercator",
        title="EU LTV / CAC Ratio",
    )
    fig.update_geos(
        fitbounds="locations",
        visible=False,
        showcoastlines=False,
        showland=True,
        landcolor="rgba(15,23,42,0.03)",
    )
    fig.update_layout(
        height=520,
        margin=dict(l=0, r=0, t=60, b=0),
        title_font=dict(size=18),
        coloraxis_colorbar=dict(title="LTV/CAC"),
    )
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
        barmode="group",
        template="plotly_white",
        title="Costs and Revenue by Country",
        height=480,
        margin=dict(l=10, r=10, t=60, b=10),
        xaxis=dict(categoryorder="array", categoryarray=list(order)),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        title_font=dict(size=18),
    )
    fig.update_yaxes(tickprefix="$", separatethousands=True)
    return fig


def top_table(df, dim):
    out = df.copy()
    for col in ["total_spend_usd", "cac_usd", "total_revenue", "avg_ltv_usd", "ltv_cac_ratio", "profit_gap"]:
        if col in out.columns:
            out[col] = out[col].round(2)
    cols = [dim, "new_customers", "total_spend_usd", "cac_usd", "total_revenue", "avg_ltv_usd", "ltv_cac_ratio", "profit_gap"]
    return out[[c for c in cols if c in out.columns]]


def main():
    inject_css()
    st.title("📈 Marketing Dashboard: LTV vs CAC")
    st.caption("Compare acquisition efficiency and customer value across countries, platforms, and ad sources.")

    if not CAC_FILE.exists() or not LTV_FILE.exists():
        st.error(f"Missing files. Expected: {CAC_FILE} and {LTV_FILE}")
        st.stop()

    cac, ltv = load_data(CAC_FILE, LTV_FILE)
    cac = normalize_country_codes(cac)
    ltv = normalize_country_codes(ltv)

    all_countries = sorted(set(cac["country"].dropna().unique()).union(set(ltv["country"].dropna().unique())))
    all_platforms = sorted(set(cac["platform"].dropna().unique()).union(set(ltv["platform"].dropna().unique())))
    all_sources = sorted(set(cac["ad_source"].dropna().unique()).union(set(ltv["ad_source"].dropna().unique())))

    st.sidebar.header("Filters")
    with st.sidebar.form("filters_form"):
        selected_countries = st.multiselect("Country", all_countries, default=all_countries)
        selected_platforms = st.multiselect("Platform", all_platforms, default=all_platforms)
        selected_sources = st.multiselect("Ad source", all_sources, default=all_sources)
        st.form_submit_button("Apply filters", use_container_width=True)

    cac_f, ltv_f = apply_filters(cac, ltv, selected_countries, selected_platforms, selected_sources)
    kpis = build_kpis(cac_f, ltv_f)

    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Total Spend", fmt_money(kpis["total_spend"]))
    m2.metric("Total Revenue", fmt_money(kpis["total_revenue"]))
    m3.metric("New Customers", fmt_num(kpis["total_customers"]))
    m4.metric("Overall CAC", fmt_money(kpis["overall_cac"]))
    m5.metric("Avg LTV", fmt_money(kpis["avg_ltv"]))
    m6.metric("LTV:CAC", f"{kpis['ltv_cac_ratio']:.2f}x" if pd.notna(kpis["ltv_cac_ratio"]) else "—")

    st.markdown(
        '<div class="small-note">A healthy target is often around 3:1 or better, but that depends on growth stage and margin structure.</div>',
        unsafe_allow_html=True,
    )

    eu_map = make_eu_map(cac_f, ltv_f)
    if eu_map is not None:
        st.plotly_chart(eu_map, use_container_width=True)
    else:
        st.info("No EU data available for the current filters.")

    st.plotly_chart(make_cost_revenue_chart(cac_f, ltv_f), use_container_width=True)

    dims = {"Ad Source": "ad_source", "Platform": "platform", "Country": "country"}
    selected_dim_label = st.radio("Breakdown", list(dims.keys()), horizontal=True)
    dim = dims[selected_dim_label]
    breakdown = aggregate_dim(cac_f, ltv_f, dim)

    left, right = st.columns(2)
    with left:
        st.plotly_chart(
            make_bar(
                breakdown.sort_values("total_spend_usd", ascending=False).head(15),
                x=dim,
                y="total_spend_usd",
                title=f"Total Spend by {selected_dim_label}",
                color=dim,
            ),
            use_container_width=True,
        )
    with right:
        st.plotly_chart(
            make_bar(
                breakdown.sort_values("total_revenue", ascending=False).head(15),
                x=dim,
                y="total_revenue",
                title=f"Total Revenue by {selected_dim_label}",
                color=dim,
            ),
            use_container_width=True,
        )

    left, right = st.columns(2)
    with left:
        st.plotly_chart(
            make_bar(
                breakdown.sort_values("cac_usd", ascending=False).head(15),
                x=dim,
                y="cac_usd",
                title=f"CAC by {selected_dim_label}",
                color=dim,
            ),
            use_container_width=True,
        )
    with right:
        st.plotly_chart(make_scatter(breakdown, dim), use_container_width=True)

    st.subheader(f"{selected_dim_label} performance table")
    st.dataframe(top_table(breakdown, dim), use_container_width=True, hide_index=True)

    csv = top_table(breakdown, dim).to_csv(index=False).encode("utf-8")
    st.download_button(
        label=f"Download {selected_dim_label.lower()} breakdown CSV",
        data=csv,
        file_name=f"marketing_breakdown_{dim}.csv",
        mime="text/csv",
        use_container_width=False,
    )


if __name__ == "__main__":
    main()