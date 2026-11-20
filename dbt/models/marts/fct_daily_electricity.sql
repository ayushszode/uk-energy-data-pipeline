-- Daily summary. Grain: one row per settlement date. Used by the dashboard
-- and as the input to the next-day peak demand forecast.
with daily as (
    select
        settlement_date,
        count(*) as periods_reported,
        sum(national_demand_mw) * 0.5 / 1000 as demand_gwh,
        max(national_demand_mw) as peak_demand_mw,
        arg_max(period_start_local, national_demand_mw) as peak_time_local,
        min(national_demand_mw) as min_demand_mw,
        arg_min(period_start_local, national_demand_mw) as min_time_local,
        max(underlying_demand_mw) as peak_underlying_demand_mw,
        sum(embedded_solar_mw) * 0.5 / 1000 as embedded_solar_gwh,
        sum(embedded_wind_mw) * 0.5 / 1000 as embedded_wind_gwh,
        avg(intensity_actual) as avg_intensity,
        min(intensity_actual) as min_intensity,
        max(intensity_actual) as max_intensity,
        arg_min(period_start_local, intensity_actual) as cleanest_time_local,
        avg(wind_solar_pct) as avg_wind_solar_pct,
        avg(zero_carbon_pct) as avg_zero_carbon_pct,
        avg(gas_pct) as avg_gas_pct,
        avg(temperature_c) as avg_temperature_c,
        min(temperature_c) as min_temperature_c,
        avg(wind_speed_kmh) as avg_wind_speed_kmh
    from {{ ref('fct_electricity_half_hourly') }}
    group by settlement_date
)

select
    dd.date_key,
    d.settlement_date,
    dd.year,
    dd.month,
    dd.day_of_week,
    dd.day_name,
    dd.is_weekend,
    dd.season,
    dd.is_bank_holiday_ew,
    dd.is_clock_change_day,
    dd.expected_settlement_periods,
    d.periods_reported,
    d.periods_reported = dd.expected_settlement_periods as is_complete_day,
    d.demand_gwh,
    d.peak_demand_mw,
    d.peak_time_local,
    d.min_demand_mw,
    d.min_time_local,
    d.peak_underlying_demand_mw,
    d.embedded_solar_gwh,
    d.embedded_wind_gwh,
    d.avg_intensity,
    d.min_intensity,
    d.max_intensity,
    d.cleanest_time_local,
    d.avg_wind_solar_pct,
    d.avg_zero_carbon_pct,
    d.avg_gas_pct,
    d.avg_temperature_c,
    d.min_temperature_c,
    d.avg_wind_speed_kmh,
    greatest({{ var('hdd_base_c') }} - d.avg_temperature_c, 0) as heating_degree_days
from daily as d
join {{ ref('dim_date') }} as dd on dd.date_day = d.settlement_date
