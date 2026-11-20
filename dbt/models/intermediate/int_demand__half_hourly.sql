-- Outturn (actual) demand per settlement period, with the correct UTC and UK
-- local start time for each period, including the 46- and 50-period days.
with demand as (
    select *
    from {{ ref('stg_neso__demand') }}
    where not is_forecast
      and settlement_date is not null
      and settlement_period between 1 and 50
      and national_demand_mw is not null
)

select
    settlement_date,
    settlement_period,
    {{ settlement_period_start_utc('settlement_date', 'settlement_period') }} as period_start_utc,
    {{ utc_to_local(settlement_period_start_utc('settlement_date', 'settlement_period')) }} as period_start_local,
    national_demand_mw,
    transmission_system_demand_mw,
    england_wales_demand_mw,
    embedded_wind_mw,
    embedded_wind_capacity_mw,
    embedded_solar_mw,
    embedded_solar_capacity_mw,
    pump_storage_pumping_mw,
    -- National Demand excludes generation on local networks, so add the NESO
    -- embedded wind and solar estimates back to approximate underlying demand.
    national_demand_mw + coalesce(embedded_wind_mw, 0) + coalesce(embedded_solar_mw, 0) as underlying_demand_mw,
    coalesce(ifa_flow_mw, 0) + coalesce(ifa2_flow_mw, 0) + coalesce(britned_flow_mw, 0)
        + coalesce(moyle_flow_mw, 0) + coalesce(east_west_flow_mw, 0) + coalesce(nemo_flow_mw, 0)
        + coalesce(nsl_flow_mw, 0) + coalesce(eleclink_flow_mw, 0) + coalesce(viking_flow_mw, 0)
        + coalesce(greenlink_flow_mw, 0) as net_interconnector_flow_mw
from demand
