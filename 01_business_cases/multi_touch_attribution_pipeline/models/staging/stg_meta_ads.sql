with source as (

    select * from {{ source('meta_ads', 'ad_insights') }}

),

renamed as (

    select
        -- keys
        cast(campaign_id as string)                         as campaign_id,
        cast(adset_id as string)                            as ad_group_id,

        -- dimensions
        cast(date_start as date)                            as date_day,
        campaign_name,
        adset_name                                          as ad_group_name,
        lower(objective)                                    as campaign_objective,
        'meta_ads'                                          as channel,
        'meta_ads'                                          as source_system,

        -- metrics: Meta reports spend in account currency (USD assumed)
        impressions,
        clicks,
        cast(spend as numeric)                              as spend_usd,
        -- Meta stores conversions inside a JSON array; extract purchase action
        cast(
            json_extract_scalar(
                (select value from unnest(actions) where action_type = 'purchase' limit 1),
                '$.value'
            ) as numeric
        )                                                   as conversions,
        reach,
        frequency,

        -- derived
        safe_divide(clicks, impressions)                    as ctr,
        safe_divide(cast(spend as numeric), clicks)         as cpc_usd,
        safe_divide(
            cast(spend as numeric),
            cast(
                json_extract_scalar(
                    (select value from unnest(actions) where action_type = 'purchase' limit 1),
                    '$.value'
                ) as numeric
            )
        )                                                   as cpa_usd,

        -- metadata
        _fivetran_synced                                    as synced_at

    from source

    where _fivetran_deleted is false

)

select * from renamed
