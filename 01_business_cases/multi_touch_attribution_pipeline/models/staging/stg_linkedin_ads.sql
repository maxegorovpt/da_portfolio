with source as (

    select * from {{ source('linkedin_ads', 'ad_analytics_by_campaign') }}

),

renamed as (

    select
        -- keys
        cast(campaign_id as string)                         as campaign_id,
        -- LinkedIn does not have an ad group concept; use campaign as surrogate
        cast(campaign_id as string)                         as ad_group_id,

        -- dimensions
        cast(day as date)                                   as date_day,
        campaign_name,
        null                                                as ad_group_name,
        'linkedin_ads'                                      as channel,
        'linkedin_ads'                                      as source_system,

        -- metrics: LinkedIn reports cost in USD cents — convert to dollars
        impressions,
        clicks,
        round(cost_in_usd / 100.0, 4)                      as spend_usd,
        -- LinkedIn counts external_website_conversions as the closest to purchases
        external_website_conversions                        as conversions,
        video_views,
        likes,
        shares,
        comments,

        -- derived
        safe_divide(clicks, impressions)                    as ctr,
        safe_divide(round(cost_in_usd / 100.0, 4), clicks) as cpc_usd,
        safe_divide(
            round(cost_in_usd / 100.0, 4),
            external_website_conversions
        )                                                   as cpa_usd,

        -- metadata
        _fivetran_synced                                    as synced_at

    from source

    where _fivetran_deleted is false

)

select * from renamed
