/*
  int_touchpoints
  ---------------
  Unions all ad platform staging models into a single touchpoints table.
  One row per campaign / ad group / day with a unified schema.
  Used downstream by int_sessions and fct_attribution.
*/

with google_ads as (

    select
        campaign_id,
        ad_group_id,
        date_day,
        campaign_name,
        ad_group_name,
        channel,
        source_system,
        impressions,
        clicks,
        spend_usd,
        conversions,
        ctr,
        cpc_usd,
        cpa_usd
    from {{ ref('stg_google_ads') }}

),

meta_ads as (

    select
        campaign_id,
        ad_group_id,
        date_day,
        campaign_name,
        ad_group_name,
        channel,
        source_system,
        impressions,
        clicks,
        spend_usd,
        conversions,
        ctr,
        cpc_usd,
        cpa_usd
    from {{ ref('stg_meta_ads') }}

),

linkedin_ads as (

    select
        campaign_id,
        ad_group_id,
        date_day,
        campaign_name,
        ad_group_name,
        channel,
        source_system,
        impressions,
        clicks,
        spend_usd,
        conversions,
        ctr,
        cpc_usd,
        cpa_usd
    from {{ ref('stg_linkedin_ads') }}

),

unioned as (

    select * from google_ads
    union all
    select * from meta_ads
    union all
    select * from linkedin_ads

),

with_surrogate_key as (

    select
        {{ dbt_utils.generate_surrogate_key([
            'source_system',
            'campaign_id',
            'ad_group_id',
            'date_day'
        ]) }}                               as touchpoint_id,
        *
    from unioned

)

select * from with_surrogate_key
