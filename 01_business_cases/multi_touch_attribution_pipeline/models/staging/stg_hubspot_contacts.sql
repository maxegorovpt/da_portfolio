with source as (

    select * from {{ source('hubspot', 'contact') }}

),

renamed as (

    select
        -- keys
        cast(contact_id as string)                          as contact_id,

        -- dimensions
        email,
        lower(lifecyclestage)                               as lifecycle_stage,

        -- HubSpot attribution: hs_latest_source holds the channel,
        -- hs_latest_source_data_1 holds the campaign identifier
        lower(hs_latest_source)                             as first_touch_channel,
        hs_latest_source_data_1                             as first_touch_campaign,
        lower(hs_analytics_source)                          as original_source,

        -- timestamps: HubSpot stores epoch milliseconds — must cast before converting
        timestamp_millis(cast(createdate as int64))         as created_at,
        timestamp_millis(
            cast(hs_lifecyclestage_lead_date as int64)
        )                                                   as became_lead_at,
        timestamp_millis(
            cast(hs_lifecyclestage_marketingqualifiedlead_date as int64)
        )                                                   as became_mql_at,
        timestamp_millis(
            cast(hs_lifecyclestage_salesqualifiedlead_date as int64)
        )                                                   as became_sql_at,
        timestamp_millis(
            cast(hs_lifecyclestage_customer_date as int64)
        )                                                   as became_customer_at,

        -- booleans
        cast(hs_email_optout as bool)                       as is_email_opted_out,
        cast(hs_is_unworked as bool)                        as is_unworked,

        -- metadata
        _fivetran_synced                                    as synced_at

    from source

    where _fivetran_deleted is false

),

with_derived as (

    select
        *,
        became_customer_at is not null                      as is_customer,
        date_diff(
            cast(became_customer_at as date),
            cast(became_lead_at as date),
            day
        )                                                   as days_lead_to_close,
        date_diff(
            cast(became_mql_at as date),
            cast(became_lead_at as date),
            day
        )                                                   as days_lead_to_mql

    from renamed

)

select * from with_derived
