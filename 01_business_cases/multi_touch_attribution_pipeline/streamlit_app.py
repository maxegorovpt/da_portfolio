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


def inject_css():
    st.markdown(
        """
        <style>
        .block-container {padding-top: 1.2rem; padding-bottom: 2rem;}
        [data-testid="stMetric"] {
            background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
            border: 1px solid rgba(15, 23, 42, 0.08);
            padding: 0.85rem 1rem;
            border-radius: 16px;
            box-shadow: 0 2px 10px rgba(15, 23, 42, 0.04);
        }
        .section-card {
            background: #ffffff;
            border: 1px solid rgba(15, 23, 42, 0.08);
            border-radius: 18px;
            padding: 1rem 1rem 0.5rem 1rem;
            box-shadow: 0 2px 10px rgba(15, 23, 42, 0.04);
            margin-bottom: 1rem;
        }
        .small-note {
            color: #475569;
            font-size: 0.9rem;
            margin-top: -0.2rem;
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

    for df in [cac, ltv]:
        for col in ["country", "platform", "ad_source"]:
            if col in df.columns:
                df[col] = df[col].astype(str).fillna("unknown")

    for col in ["first_purchase_date", "last_purchase_date"]:
        if col in cac.columns:
            cac[col] = pd.to_datetime(cac[col], errors="coerce")
        if col in ltv.columns:
            ltv[col] = pd.to_datetime(ltv[col], errors="coerce")

    numeric_cols_cac = ["new_customers", "total_spend_usd", "cac_usd"]
    numeric_cols_ltv = ["total_revenue", "purchase_count", "ltv_usd"]

    for col in numeric_cols_cac:
        if col in cac.columns:
            cac[col] = pd.to_numeric(cac[col], errors="coerce")

    for col in numeric_cols_ltv:
        if col in ltv.columns:
            ltv[col] = pd.to_numeric(ltv[col], errors="coerce")

    return cac, ltv


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
    if pd.isna(x):
        return "—"
    return f"${x:,.2f}"


def fmt_num(x):
    if pd.isna(x):
        return "—"
    return f"{x:,.0f}"


def safe_div(a, b):
    if b in [0, None] or pd.isna(b):
        return np.nan
    return a / b


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
    merged["total_spend_usd"] = pd.to_numeric(merged["total_spend_usd"], errors="coerce").fillna(0)
    merged["new_customers"] = pd.to_numeric(merged["new_customers"], errors="coerce").fillna(0)
    merged["total_revenue"] = pd.to_numeric(merged["total_revenue"], errors="coerce").fillna(0)
    merged["purchase_count"] = pd.to_numeric(merged["purchase_count"], errors="coerce").fillna(0)
    merged["avg_ltv_usd"] = pd.to_numeric(merged["avg_ltv_usd"], errors="coerce")
    merged["users"] = pd.to_numeric(merged["users"], errors="coerce").fillna(0)
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
    fig.update_layout(height=420, margin=dict(l=10, r=10, t=50, b=10))
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
        labels={
            "cac_usd": "CAC ($)",
            "avg_ltv_usd": "Avg LTV ($)",
            "ltv_cac_ratio": "LTV/CAC",
        },
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
                line=dict(color="gray", dash="dash"),
            )
        )
    fig.update_layout(height=440, margin=dict(l=10, r=10, t=50, b=10))
    return fig


def top_table(df, dim):
    out = df.copy()
    out["total_spend_usd"] = out["total_spend_usd"].round(2)
    out["cac_usd"] = out["cac_usd"].round(2)
    out["total_revenue"] = out["total_revenue"].round(2)
    out["avg_ltv_usd"] = out["avg_ltv_usd"].round(2)
    out["ltv_cac_ratio"] = out["ltv_cac_ratio"].round(2)
    out["profit_gap"] = out["profit_gap"].round(2)
    cols = [
        dim, "new_customers", "total_spend_usd", "cac_usd",
        "total_revenue", "avg_ltv_usd", "ltv_cac_ratio", "profit_gap"
    ]
    return out[cols]


def main():
    inject_css()
    st.title("📈 Marketing Dashboard: LTV vs CAC")
    st.caption("Compare acquisition efficiency and customer value across country, platform, and ad source.")

    if not CAC_FILE.exists() or not LTV_FILE.exists():
        st.error(f"Missing files. Expected: {CAC_FILE} and {LTV_FILE}")
        st.stop()

    cac, ltv = load_data(CAC_FILE, LTV_FILE)

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

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Total Spend", fmt_money(kpis["total_spend"]))
    c2.metric("Total Revenue", fmt_money(kpis["total_revenue"]))
    c3.metric("New Customers", fmt_num(kpis["total_customers"]))
    c4.metric("Overall CAC", fmt_money(kpis["overall_cac"]))
    c5.metric("Avg LTV", fmt_money(kpis["avg_ltv"]))
    c6.metric("LTV:CAC", f"{kpis['ltv_cac_ratio']:.2f}x" if pd.notna(kpis["ltv_cac_ratio"]) else "—")

    st.markdown(
        '<div class="small-note">A commonly used rule of thumb is LTV:CAC around 3:1 or better, though the right target depends on business model and growth stage.</div>',
        unsafe_allow_html=True,
    )

    dims = {
        "Ad Source": "ad_source",
        "Platform": "platform",
        "Country": "country",
    }

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

    with st.expander("Metric definitions"):
        st.markdown(
            """
            - **Total Spend** = sum of `total_spend_usd` from `cac.csv`
            - **Total Revenue** = sum of `total_revenue` from `ltv.csv`
            - **Overall CAC** = total spend / total new customers
            - **Avg LTV** = average `ltv_usd` for filtered users
            - **LTV:CAC** = average LTV / overall CAC
            - **Profit Gap** = avg LTV - CAC
            """
        )


if __name__ == "__main__":
    main()