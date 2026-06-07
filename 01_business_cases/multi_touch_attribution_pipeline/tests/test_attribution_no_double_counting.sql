/*
  test_attribution_no_double_counting
  ------------------------------------
  Ensures that total first-touch attributed credits per contact sum to exactly 1.0.
  Guards against double-counting bugs in the attribution logic.
  Run with: dbt test --select fct_attribution
*/

with credits_per_contact as (

    select
        contact_id,
        round(sum(first_touch_credit), 4)   as total_first_touch,
        round(sum(last_touch_credit), 4)    as total_last_touch,
        round(sum(linear_credit), 4)        as total_linear

    from {{ ref('fct_attribution') }}
    where contact_id is not null
    group by 1

),

violations as (

    select *
    from credits_per_contact
    where total_first_touch != 1.0
       or total_last_touch  != 1.0
       or total_linear      != 1.0

)

select * from violations
