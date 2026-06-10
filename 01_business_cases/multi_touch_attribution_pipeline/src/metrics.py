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

    campaign_level=True further segments by campaign and filters purchases to
    those that occurred on or after the campaign start date.  Purchases whose
    campaign_id has no matching entry in the ads table are kept in a fallback
    group ("unknown" campaign) rather than silently dropped.
    """
    purchases = purchases.copy()
    purchases["purchase_date"] = pd.to_datetime(purchases["purchase_date"], errors="coerce")

    if campaign_level:
        if ads is None:
            raise ValueError("ads is required when campaign_level=True")

        ads = ads.copy()
        if "campaign_start_date" not in ads.columns:
            raise ValueError("ads must contain campaign_start_date for campaign-level LTV")

        ads["campaign_start_date"] = pd.to_datetime(ads["campaign_start_date"], errors="coerce")

        # Keep only the columns we need and deduplicate so the merge stays 1-to-1
        campaign_meta = (
            ads[["ad_source", "campaign", "campaign_id", "country", "platform", "campaign_start_date"]]
            .drop_duplicates()
        )

        join_keys = [
            c for c in ["ad_source", "campaign_id", "campaign", "country", "platform"]
            if c in purchases.columns and c in campaign_meta.columns
        ]
        purchases = purchases.merge(campaign_meta, on=join_keys, how="left")

        # FIX: instead of dropping unmatched rows, assign them a fallback start date
        # so they are still included in the output under their actual ad_source group.
        unmatched = purchases["campaign_start_date"].isna()
        if unmatched.any():
            # Use the purchase date itself as the start date so the >= filter passes
            purchases.loc[unmatched, "campaign_start_date"] = purchases.loc[unmatched, "purchase_date"]
            # Mark campaign as unknown where we had no ads-side match
            if "campaign" in purchases.columns:
                purchases.loc[unmatched, "campaign"] = purchases.loc[unmatched, "campaign"].fillna("unknown")
            if "campaign_id" in purchases.columns:
                purchases.loc[unmatched, "campaign_id"] = purchases.loc[unmatched, "campaign_id"].fillna("unknown")

        # Apply the inclusive start-date filter
        purchases = purchases.loc[purchases["purchase_date"] >= purchases["campaign_start_date"]]

        group_cols = [
            c for c in ["user_id", "ad_source", "campaign", "campaign_id", "platform", "country"]
            if c in purchases.columns
        ]
    else:
        group_cols = ["user_id", "ad_source", "platform", "country"]

    if purchases.empty:
        # Return an empty frame with the expected columns so callers don't crash
        ordered_cols = [
            c for c in [
                "user_id", "ad_source", "campaign", "campaign_id", "platform", "country",
                "total_revenue", "purchase_count", "first_purchase_date", "last_purchase_date", "ltv_usd",
            ]
            if c in group_cols or c in ["total_revenue", "purchase_count", "first_purchase_date", "last_purchase_date", "ltv_usd"]
        ]
        return pd.DataFrame(columns=ordered_cols)

    ltv = (
        purchases.groupby(group_cols, as_index=False, dropna=False)
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