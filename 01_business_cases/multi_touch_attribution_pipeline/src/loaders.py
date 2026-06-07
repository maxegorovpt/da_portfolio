from pathlib import Path
import pandas as pd


def _get_series(df, col, default="unknown"):
    if col not in df.columns:
        return pd.Series([default] * len(df), index=df.index)
    value = df[col]
    if isinstance(value, pd.DataFrame):
        value = value.iloc[:, 0]
    return value


def _normalize_text(series, lower=False, upper=False):
    s = series.astype(str).str.strip()
    if lower:
        s = s.str.lower()
    if upper:
        s = s.str.upper()
    return s


def _normalize_source(series):
    s = _normalize_text(series, lower=True)
    return s.replace({
        "googleads":          "google_ads",
        "google ads":         "google_ads",
        "facebook":           "facebook",
        "facebook ads":       "facebook",
        "facebook_ads":       "facebook",
        "instagram":          "instagram",
        "instagram ads":      "instagram",
        "instagram_ads":      "instagram",
        "tiktok":             "tiktok",
        "tiktok ads":         "tiktok",
        "tiktok_ads":         "tiktok",
        "twitter":            "twitter",
        "twitter ads":        "twitter",
        "twitter_ads":        "twitter",
        "affiliate":          "affiliate",
        "affiliate_ads":      "affiliate",
        "affiliate_ads_2025": "affiliate",
    })


def _dedup_columns(df):
    return df.loc[:, ~df.columns.duplicated(keep="first")]


_AFFILIATE_MARKERS = {"affiliate_name", "affiliate_id"}


def _is_affiliate_file(df):
    return bool(_AFFILIATE_MARKERS.intersection(df.columns))


def _standardize_affiliate_frame(df):
    df = df.copy()
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_", regex=False)
    )

    df = df.rename(columns={
        "spend":         "spend_usd",
        "cost":          "spend_usd",
        "amount_spent":  "spend_usd",
        "ad_spend":      "spend_usd",
        "campaign_name": "campaign",
    })

    df = _dedup_columns(df)

    df["ad_source"]      = "affiliate"
    df["platform"]       = _normalize_text(_get_series(df, "platform"), lower=True)
    df["affiliate_name"] = _normalize_text(_get_series(df, "affiliate_name"))
    df["affiliate_id"]   = _normalize_text(_get_series(df, "affiliate_id"))
    df["campaign"]       = _normalize_text(_get_series(df, "campaign"), lower=True)
    df["country"]        = _normalize_text(_get_series(df, "country"), upper=True)
    df["spend_usd"]      = pd.to_numeric(
        _get_series(df, "spend_usd", default=0), errors="coerce"
    ).fillna(0)
    df["conversions"]    = pd.to_numeric(
        _get_series(df, "conversions", default=0), errors="coerce"
    ).fillna(0)

    return df[[
        "ad_source", "platform", "country", "campaign",
        "affiliate_name", "affiliate_id", "spend_usd", "conversions",
    ]]


def _standardize_ads_frame(df, filename):
    df = df.copy()
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_", regex=False)
    )

    if _is_affiliate_file(df):
        return _standardize_affiliate_frame(df)

    df = df.rename(columns={
        "source":        "ad_source",
        "channel":       "ad_source",
        "adsource":      "ad_source",
        "campaign_name": "campaign",
        "campaignid":    "campaign",
        "campaign_id":   "campaign",
        "spend":         "spend_usd",
        "cost":          "spend_usd",
        "amount_spent":  "spend_usd",
        "ad_spend":      "spend_usd",
        "device":        "platform",
        "os":            "platform",
        "geo":           "country",
        "country_code":  "country",
    })

    df = _dedup_columns(df)

    if "ad_source" not in df.columns:
        source_name = (
            filename.stem.lower()
            .replace("_ads_2025", "")
            .replace("_ads", "")
        )
        df["ad_source"] = source_name

    if "platform" not in df.columns:
        df["platform"] = "unknown"
    if "country" not in df.columns:
        df["country"] = "unknown"
    if "campaign" not in df.columns:
        df["campaign"] = "unknown"
    if "conversions" not in df.columns:
        df["conversions"] = 0
    if "affiliate_name" not in df.columns:
        df["affiliate_name"] = ""
    if "affiliate_id" not in df.columns:
        df["affiliate_id"] = ""

    if "spend_usd" not in df.columns:
        raise ValueError(f"Missing spend column in file: {filename.name}")

    df["ad_source"]   = _normalize_source(_get_series(df, "ad_source"))
    df["platform"]    = _normalize_text(_get_series(df, "platform"), lower=True)
    df["country"]     = _normalize_text(_get_series(df, "country"), upper=True)
    df["campaign"]    = _normalize_text(_get_series(df, "campaign"), lower=True)
    df["spend_usd"]   = pd.to_numeric(
        _get_series(df, "spend_usd", default=0), errors="coerce"
    ).fillna(0)
    df["conversions"] = pd.to_numeric(
        _get_series(df, "conversions", default=0), errors="coerce"
    ).fillna(0)

    return df[[
        "ad_source", "platform", "country", "campaign",
        "affiliate_name", "affiliate_id", "spend_usd", "conversions",
    ]]


def load_purchases_data(path):
    path = Path(path)
    df = pd.read_csv(path)

    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_", regex=False)
    )

    df = _dedup_columns(df)

    df = df.rename(columns={
        "userid":         "user_id",
        "purchasedate":   "purchase_date",
        "adsource":       "ad_source",
        "purchaseamount": "purchase_amount",
    })

    df["user_id"] = _normalize_text(_get_series(df, "user_id"))
    df["purchase_date"] = pd.to_datetime(
        _get_series(df, "purchase_date").astype(str).str.strip(),
        errors="coerce",
    )
    df["platform"] = _normalize_text(_get_series(df, "platform"), lower=True)
    df["ad_source"] = _normalize_source(_get_series(df, "ad_source"))
    df["country"] = _normalize_text(_get_series(df, "country"), upper=True)
    df["purchase_amount"] = pd.to_numeric(
        _get_series(df, "purchase_amount", default=0), errors="coerce"
    ).fillna(0)

    base_cols = [
        "user_id", "purchase_date", "platform",
        "ad_source", "purchase_amount", "country",
    ]
    optional_cols = [c for c in ("affiliate_id", "affiliate_name") if c in df.columns]

    return df[base_cols + optional_cols]


def load_ads_data(path):
    path = Path(path)
    ad_files = sorted(path.glob("*.csv"))
    if not ad_files:
        raise FileNotFoundError(f"No CSV files found in {path}")

    frames = []
    for file in ad_files:
        raw = pd.read_csv(file)
        frames.append(_standardize_ads_frame(raw, file))

    return pd.concat(frames, ignore_index=True)