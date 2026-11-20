-- One row per calendar day covered by the demand data, with calendar
-- attributes, bank holidays and clock-change flags.
with bounds as (
    select min(settlement_date) as first_day, max(settlement_date) as last_day
    from {{ ref('int_demand__half_hourly') }}
),

days as (
    select cast(unnest(generate_series(cast(first_day as timestamp), cast(last_day as timestamp), interval 1 day)) as date) as date_day
    from bounds
),

holidays as (
    select
        holiday_date,
        bool_or(division = 'england-and-wales') as is_bank_holiday_ew,
        bool_or(division = 'scotland') as is_bank_holiday_scotland,
        string_agg(distinct case when division = 'england-and-wales' then holiday_name end, ', ') as holiday_name
    from {{ ref('stg_gov__bank_holidays') }}
    group by holiday_date
)

select
    cast(strftime(d.date_day, '%Y%m%d') as integer) as date_key,
    d.date_day,
    year(d.date_day) as year,
    quarter(d.date_day) as quarter,
    month(d.date_day) as month,
    monthname(d.date_day) as month_name,
    weekofyear(d.date_day) as iso_week,
    isodow(d.date_day) as day_of_week,
    dayname(d.date_day) as day_name,
    isodow(d.date_day) in (6, 7) as is_weekend,
    case
        when month(d.date_day) in (12, 1, 2) then 'Winter'
        when month(d.date_day) in (3, 4, 5) then 'Spring'
        when month(d.date_day) in (6, 7, 8) then 'Summer'
        else 'Autumn'
    end as season,
    coalesce(h.is_bank_holiday_ew, false) as is_bank_holiday_ew,
    coalesce(h.is_bank_holiday_scotland, false) as is_bank_holiday_scotland,
    h.holiday_name,
    {{ expected_settlement_periods('d.date_day') }} as expected_settlement_periods,
    {{ expected_settlement_periods('d.date_day') }} <> 48 as is_clock_change_day,
    case {{ expected_settlement_periods('d.date_day') }}
        when 46 then 'Clocks go forward'
        when 50 then 'Clocks go back'
    end as clock_change
from days as d
left join holidays as h on h.holiday_date = d.date_day
