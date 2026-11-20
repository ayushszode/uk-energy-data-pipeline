{#- GB electricity is settled in half-hour "settlement periods" counted from
    local (UK) midnight. Most days have 48 periods, but the day the clocks go
    forward has 46 and the day they go back has 50. These macros turn a
    settlement date + period into a correct UTC timestamp, and work out how
    many periods each day should have. -#}

{% macro settlement_period_start_utc(date_col, period_col) -%}
    (timezone('UTC', timezone('Europe/London', cast({{ date_col }} as timestamp)))
        + to_minutes(cast(({{ period_col }} - 1) * 30 as bigint)))
{%- endmacro %}

{% macro utc_to_local(ts_col) -%}
    timezone('Europe/London', timezone('UTC', {{ ts_col }}))
{%- endmacro %}

{% macro expected_settlement_periods(date_col) -%}
    cast(date_diff('minute',
        timezone('Europe/London', cast({{ date_col }} as timestamp)),
        timezone('Europe/London', cast({{ date_col }} + 1 as timestamp))) / 30 as integer)
{%- endmacro %}

{% macro parse_api_timestamp(col) -%}
    {#- Carbon Intensity API times look like 2026-01-01T00:30Z (UTC). -#}
    coalesce(
        try_strptime({{ col }}, '%Y-%m-%dT%H:%MZ'),
        try_strptime({{ col }}, '%Y-%m-%dT%H:%M:%SZ'),
        try_strptime({{ col }}, '%Y-%m-%dT%H:%M'))
{%- endmacro %}
