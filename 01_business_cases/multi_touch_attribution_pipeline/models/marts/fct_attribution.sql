/*
  fct_attribution
  ---------------
  Applies three attribution models to the unified touchpoints:
    - first_touch:  100% credit to the first touchpoint in the journey
    - last_touch:   100% credit to the last touchpoint before conversion
    - linear:       Equal credit split across all touchpoints in the journey

  Grain: one row per touchpoint_id with attributed revenue for each model.
  Join to stg_hubspot_contacts on first_touch_channel / first_touch_campaign
  to pull in contact-level conversion data.
*/

with touchpoints as (

    select * from {{ ref('int_touchpoints') }}

),

contacts as (

    select
        contact_id,
        email,
        first_touch_channel,
        first_touch_campaign,
        lifecycle_stage,
        is_customer,
        became_customer_at,
        days_lead_to_close
    from {{ ref('stg_hubspot_contacts') }}
    where is_customer = true

),

-- Join touchpoints to converted contacts via channel + campaign name
touchpoints_with_contact as (

    select
        t.*,
        c.contact_id,
        c.email,
        c.became_customer_at,
        c.days_lead_to_close
    from touchpoints t
    left join contacts c
        on lower(t.channel) = lower(c.first_touch_channel)
        and lower(t.campaign_name) = lower(c.first_touch_campaign)

),

-- Rank touchpoints per contact journey
journey as (

    select
        *,
        row_number() over (
            partition by contact_id
            order by date_day asc
        )                                       as touchpoint_position,
        count(*) over (
            partition by contact_id
        )                                       as total_touchpoints,
        row_number() over (
            partition by contact_id
            order by date_day desc
        )                                       as touchpoint_position_rev

    from touchpoints_with_contact
    where contact_id is not null

),

-- Apply attribution models using macros
attributed as (

    select
        touchpoint_id,
        contact_id,
        email,
        campaign_id,
        ad_group_id,
        campaign_name,
        ad_group_name,
        channel,
        source_system,
        date_day,
        spend_usd,
        impressions,
        clicks,
        conversions,
        ctr,
        cpc_usd,
        cpa_usd,
        touchpoint_position,
        total_touchpoints,
        became_customer_at,
        days_lead_to_close,

        -- First-touch: position 1 gets 100% credit
        {{ attribution_first_touch('touchpoint_position') }}    as first_touch_credit,

        -- Last-touch: reverse position 1 (most recent) gets 100% credit
        {{ attribution_last_touch('touchpoint_position_rev') }} as last_touch_credit,

        -- Linear: equal share across all touchpoints
        {{ attribution_linear('total_touchpoints') }}           as linear_credit

    from journey

)

select * from attributed
