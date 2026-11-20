-- Every complete day must have exactly the number of settlement periods the
-- UK clock implies: 48 normally, 46 when the clocks go forward, 50 when they
-- go back. The newest day is skipped because it may still be filling in.
with per_day as (
    select settlement_date, count(*) as periods, max(settlement_period) as max_period
    from {{ ref('int_demand__half_hourly') }}
    group by settlement_date
),

checked as (
    select
        settlement_date,
        periods,
        max_period,
        {{ expected_settlement_periods('settlement_date') }} as expected
    from per_day
    where settlement_date < (select max(settlement_date) from per_day)
)

select *
from checked
where periods <> expected or max_period <> expected
