import numpy as np
import pandas as pd


def calculate_cac(purchases, ads):
    """
    CAC by ad_source / platform / country.

    Affiliate rows are included with ad_source='affiliate', platform='unknown'.
    Use calculate_affiliate_cac() for partner-level breakdown.

    Returns columns:
        ad_source | platform | country | new_customers |
        total_spend_usd | cac_usd | first_purchase_date | last_purchase_date
    """
    group_cols = ["ad_source", "platform", "country"]

    first_purchases = (
        purchases.sort_values(["user_id", "purchase_date"])
        .groupby("user_id", as_index=False)
        .first()
    )

    new_customers = (
        first_purchases.groupby(group_cols, as_index=False)
        .agg(
            new_customers=("user_id", "count"),
            first_purchase_date=("purchase_date", "min"),
            last_purchase_date=("purchase_date", "max"),
        )
    )

    channel_spend = (
        ads.groupby(group_cols, as_index=False)
        .agg(total_spend_usd=("spend_usd", "sum"))
    )

    cac = new_customers.merge(channel_spend, on=group_cols, how="outer")
    cac["new_customers"] = pd.to_numeric(cac["new_customers"], errors="coerce").fillna(0)
    cac["total_spend_usd"] = pd.to_numeric(cac["total_spend_usd"], errors="coerce").fillna(0)
    cac["cac_usd"] = np.where(
        cac["new_customers"] > 0,
        cac["total_spend_usd"] / cac["new_customers"],
        np.nan,
    )
    cac["cac_usd"] = pd.Series(cac["cac_usd"], index=cac.index).round(2)
    cac["total_spend_usd"] = cac["total_spend_usd"].round(2)
    cac["first_purchase_date"] = (
        pd.to_datetime(cac["first_purchase_date"], errors="coerce")
        .dt.strftime("%Y-%m-%d")
    )
    cac["last_purchase_date"] = (
        pd.to_datetime(cac["last_purchase_date"], errors="coerce")
        .dt.strftime("%Y-%m-%d")
    )

    return cac[[
        "ad_source",
        "platform",
        "country",
        "new_customers",
        "total_spend_usd",
        "cac_usd",
        "first_purchase_date",
        "last_purchase_date",
    ]].sort_values(["ad_source", "platform", "country"])


def calculate_affiliate_cac(purchases, ads):
    """
    Granular affiliate CAC by partner / campaign / country.

    Returns columns:
        affiliate_name | affiliate_id | campaign | country |
        new_customers | total_spend_usd | cac_usd
    """
    aff_ads = ads[ads["ad_source"] == "affiliate"].copy()
    if aff_ads.empty:
        return pd.DataFrame(columns=[
            "affiliate_name", "affiliate_id", "campaign", "country",
            "new_customers", "total_spend_usd", "cac_usd",
        ])

    group_cols = ["affiliate_name", "affiliate_id", "campaign", "country"]

    aff_spend = (
        aff_ads.groupby(group_cols, as_index=False)
        .agg(total_spend_usd=("spend_usd", "sum"))
    )

    aff_purchases = purchases[purchases["ad_source"] == "affiliate"].copy()

    if aff_purchases.empty:
        aff_spend["new_customers"] = 0
        aff_spend["cac_usd"] = np.nan
        aff_spend["total_spend_usd"] = pd.to_numeric(
            aff_spend["total_spend_usd"], errors="coerce"
        ).round(2)
        return aff_spend[[
            "affiliate_name", "affiliate_id", "campaign", "country",
            "new_customers", "total_spend_usd", "cac_usd",
        ]].sort_values(["affiliate_name", "country"])

    first_aff = (
        aff_purchases.sort_values(["user_id", "purchase_date"])
        .groupby("user_id", as_index=False)
        .first()
    )

    new_customers = (
        first_aff.groupby(["affiliate_id", "country"], as_index=False)
        .agg(new_customers=("user_id", "count"))
    )

    result = aff_spend.merge(new_customers, on=["affiliate_id", "country"], how="left")
    result["new_customers"] = pd.to_numeric(result["new_customers"], errors="coerce").fillna(0)
    result["total_spend_usd"] = pd.to_numeric(result["total_spend_usd"], errors="coerce").fillna(0)
    result["cac_usd"] = np.where(
        result["new_customers"] > 0,
        result["total_spend_usd"] / result["new_customers"],
        np.nan,
    )
    result["cac_usd"] = pd.Series(result["cac_usd"], index=result.index).round(2)
    result["total_spend_usd"] = result["total_spend_usd"].round(2)

    return result[[
        "affiliate_name",
        "affiliate_id",
        "campaign",
        "country",
        "new_customers",
        "total_spend_usd",
        "cac_usd",
    ]].sort_values(["affiliate_name", "country"])


def calculate_ltv(purchases):
    """
    User-level LTV: total revenue, purchase count, first/last purchase date.

    ltv_usd applies a repeat-purchase multiplier so repeat buyers score higher
    than one-time buyers: total_revenue * (1 + (purchase_count - 1) * 0.5).
    Adjust the 0.5 weight to match your observed retention value.

    Returns columns:
        user_id | ad_source | platform | country |
        total_revenue | purchase_count |
        first_purchase_date | last_purchase_date | ltv_usd
    """
    ltv = (
        purchases.groupby(
            ["user_id", "ad_source", "platform", "country"], as_index=False
        )
        .agg(
            total_revenue=("purchase_amount", "sum"),
            purchase_count=("purchase_amount", "size"),
            first_purchase_date=("purchase_date", "min"),
            last_purchase_date=("purchase_date", "max"),
        )
    )

    ltv["total_revenue"] = pd.to_numeric(ltv["total_revenue"], errors="coerce").fillna(0).round(2)
    ltv["purchase_count"] = pd.to_numeric(ltv["purchase_count"], errors="coerce").fillna(0)
    ltv["ltv_usd"] = (
        ltv["total_revenue"] * (1 + (ltv["purchase_count"] - 1) * 0.5)
    ).round(2)
    ltv["first_purchase_date"] = (
        pd.to_datetime(ltv["first_purchase_date"], errors="coerce")
        .dt.strftime("%Y-%m-%d")
    )
    ltv["last_purchase_date"] = (
        pd.to_datetime(ltv["last_purchase_date"], errors="coerce")
        .dt.strftime("%Y-%m-%d")
    )

    return ltv[[
        "user_id",
        "ad_source",
        "platform",
        "country",
        "total_revenue",
        "purchase_count",
        "first_purchase_date",
        "last_purchase_date",
        "ltv_usd",
    ]].sort_values(["user_id", "first_purchase_date"])