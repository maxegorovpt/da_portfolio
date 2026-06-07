{% macro attribution_first_touch(position_col) %}
    case when {{ position_col }} = 1 then 1.0 else 0.0 end
{% endmacro %}


{% macro attribution_last_touch(position_rev_col) %}
    case when {{ position_rev_col }} = 1 then 1.0 else 0.0 end
{% endmacro %}


{% macro attribution_linear(total_col) %}
    round(1.0 / nullif({{ total_col }}, 0), 6)
{% endmacro %}


{% macro attribution_time_decay(position_col, total_col, half_life_days=7) %}
    /*
      Time-decay attribution: touchpoints closer to conversion
      receive exponentially more credit. Half-life defaults to 7 days.
      Credit is normalised so all touchpoints in a journey sum to 1.0.
    */
    round(
        power(0.5, ({{ total_col }} - {{ position_col }}) / {{ half_life_days }}.0)
        / nullif(
            sum(power(0.5, ({{ total_col }} - {{ position_col }}) / {{ half_life_days }}.0))
                over (partition by contact_id),
            0
        ),
        6
    )
{% endmacro %}
