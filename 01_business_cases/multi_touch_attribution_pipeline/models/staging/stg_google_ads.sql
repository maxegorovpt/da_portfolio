with source as (

    select * from {{ source('google_ads', 'ad_performance_report') }}

),

renamed as (

    select
        -- keys
        cast(campaign_id as string)                         as campaign_id,
        cast(ad_group_id as string)                         as ad_group_id,

        -- dimensions
        cast(date as date)                                  as date_day,
        campaign_name,
        ad_group_name,
        'google_ads'                                        as channel,
        'google_ads'                                        as source_system,

        -- metrics: cost_micros is Google's native unit (millionths of a dollar)
        impressions,
        clicks,
        round(cost_micros / 1000000.0, 4)                  as spend_usd,
        conversions,
        view_through_conversions,

        -- derived
        safe_divide(clicks, impressions)                    as ctr,
        safe_divide(cost_micros / 1000000.0, clicks)       as cpc_usd,
        safe_divide(cost_micros / 1000000.0, conversions)  as cpa_usd,

        -- metadata
        _fivetran_synced                                    as synced_at

    from source

    where _fivetran_deleted is false

)

select * from renamed
