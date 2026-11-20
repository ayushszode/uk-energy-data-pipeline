{{ config(severity = 'warn') }}
-- Warn when the national carbon series skips half hours (the public API
-- occasionally has short outages). Returns each gap with its length.
with ordered as (
    select
        period_start_utc,
        lead(period_start_utc) over (order by period_start_utc) as next_start
    from {{ ref('stg_carbon__national_intensity') }}
)

select
    period_start_utc as gap_after,
    next_start,
    date_diff('minute', period_start_utc, next_start) / 30 - 1 as missing_periods
from ordered
where next_start is not null
  and date_diff('minute', period_start_utc, next_start) <> 30
