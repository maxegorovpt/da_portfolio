import numpy as np
import pandas as pd


def calculate_cac(purchases, ads):
    purchases = purchases.copy()
    ads = ads.copy()

    purchases["purchase_date"] = pd.to_datetime(purchases["purchase_date"], errors="coerce")

    first_purchases = (
        purchases.sort_values(["user_id", "purchase_date"])
        .groupby("user_id", as_index=False)
        .first()
    )

    group_cols = ["ad_source", "platform", "country"]

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
    cac["first_purchase_date"] = pd.to_datetime(
        cac["first_purchase_date"], errors="coerce"
    ).dt.strftime("%Y-%m-%d")
    cac["last_purchase_date"] = pd.to_datetime(
        cac["last_purchase_date"], errors="coerce"
    ).dt.strftime("%Y-%m-%d")

    return cac[[
        "ad_source", "platform", "country", "new_customers",
        "total_spend_usd", "cac_usd", "first_purchase_date", "last_purchase_date",
    ]].sort_values(["ad_source", "platform", "country"])


def calculate_affiliate_cac(purchases, ads):
    aff_ads = ads[ads["ad_source"] == "affiliate"].copy()
    if aff_ads.empty:
        return pd.DataFrame(columns=[
            "affiliate_name", "affiliate_id", "campaign", "country", "platform",
            "new_customers", "total_spend_usd", "cac_usd",
        ])

    group_cols = ["affiliate_name", "affiliate_id", "campaign", "country", "platform"]

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
            "affiliate_name", "affiliate_id", "campaign", "country", "platform",
            "new_customers", "total_spend_usd", "cac_usd",
        ]].sort_values(["affiliate_name", "country", "platform"])

    first_aff = (
        aff_purchases.sort_values(["user_id", "purchase_date"])
        .groupby("user_id", as_index=False)
        .first()
    )

    new_customers = (
        first_aff.groupby(["affiliate_id", "country", "platform"], as_index=False)
        .agg(new_customers=("user_id", "count"))
    )

    result = aff_spend.merge(
        new_customers,
        on=["affiliate_id", "country", "platform"],
        how="left",
    )

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
        "affiliate_name", "affiliate_id", "campaign", "country", "platform",
        "new_customers", "total_spend_usd", "cac_usd",
    ]].sort_values(["affiliate_name", "country", "platform"])


def calculate_ltv(purchases, ads=None, campaign_level=False, inclusive_start=True):
    """
    Calculate LTV per user, grouped by ad source / platform / country.
    campaign_level=True further segments by campaign.
    """
    purchases = purchases.copy()
    purchases["purchase_date"] = pd.to_datetime(purchases["purchase_date"], errors="coerce")

    if campaign_level and ads is not None:
        ads = ads.copy()
        if "campaign_start_date" in ads.columns:
            ads["campaign_start_date"] = pd.to_datetime(ads["campaign_start_date"], errors="coerce")

            # 1. ONLY match on columns that ACTUALLY exist in both files
            join_keys = [
                c for c in ["ad_source", "campaign_id", "campaign", "country", "platform"]
                if c in purchases.columns and c in ads.columns
            ]

            # 2. Group ads EXACTLY by the join keys so it creates a 1-to-1 match
            if join_keys:
                campaign_meta = (
                    ads.groupby(join_keys, as_index=False)
                    .agg(campaign_start_date=("campaign_start_date", "min"))
                )
                purchases = purchases.merge(campaign_meta, on=join_keys, how="left")

                # Fallback start date for unmatched rows
                unmatched = purchases["campaign_start_date"].isna()
                if unmatched.any():
                    purchases.loc[unmatched, "campaign_start_date"] = purchases.loc[unmatched, "purchase_date"]

    # 3. Define grouping columns based on what purchases ACTUALLY has
    group_cols = [
        c for c in ["user_id", "ad_source", "campaign", "campaign_id", "platform", "country"]
        if c in purchases.columns
    ]

    if purchases.empty:
        ordered_cols = [
            c for c in [
                "user_id", "ad_source", "campaign", "campaign_id", "platform", "country",
                "total_revenue", "purchase_count", "first_purchase_date", "last_purchase_date", "ltv_usd",
            ]
            if c in group_cols or c in ["total_revenue", "purchase_count", "first_purchase_date", "last_purchase_date", "ltv_usd"]
        ]
        return pd.DataFrame(columns=ordered_cols)

    ltv = (
        purchases.groupby(group_cols, as_index=False)
        .agg(
            total_revenue=("purchase_amount", "sum"),
            purchase_count=("purchase_amount", "size"),
            first_purchase_date=("purchase_date", "min"),
            last_purchase_date=("purchase_date", "max"),
        )
    )

    ltv["total_revenue"] = pd.to_numeric(ltv["total_revenue"], errors="coerce").fillna(0).round(2)
    ltv["purchase_count"] = pd.to_numeric(ltv["purchase_count"], errors="coerce").fillna(0)
    ltv["ltv_usd"] = (ltv["total_revenue"] * (1 + (ltv["purchase_count"] - 1) * 0.5)).round(2)
    ltv["first_purchase_date"] = pd.to_datetime(
        ltv["first_purchase_date"], errors="coerce"
    ).dt.strftime("%Y-%m-%d")
    ltv["last_purchase_date"] = pd.to_datetime(
        ltv["last_purchase_date"], errors="coerce"
    ).dt.strftime("%Y-%m-%d")

    ordered_cols = [c for c in [
        "user_id", "ad_source", "campaign", "campaign_id", "platform", "country",
        "total_revenue", "purchase_count", "first_purchase_date", "last_purchase_date", "ltv_usd"
    ] if c in ltv.columns]

    return ltv[ordered_cols].sort_values(
        [c for c in ["user_id", "first_purchase_date"] if c in ltv.columns]
    )