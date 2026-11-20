{{ config(severity = 'warn') }}
-- Warn if more than 1% of half hours older than 8 days have no temperature.
-- (Recent days are excluded because the weather archive lags by a few days.)
with recent_cut as (
    select max(settlement_date) - 8 as cut_date from {{ ref('fct_electricity_half_hourly') }}
),

coverage as (
    select
        count(*) as periods,
        count(*) filter (where temperature_c is null) as missing
    from {{ ref('fct_electricity_half_hourly') }}, recent_cut
    where settlement_date <= cut_date
)

select *, round(100.0 * missing / periods, 2) as missing_pct
from coverage
where periods > 0 and 100.0 * missing / periods > 1
