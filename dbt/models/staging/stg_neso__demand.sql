-- One row per settlement period from the NESO demand files, with text cast to
-- proper types. Rows that appear in more than one file keep the latest file.
with source as (
    select * from {{ source('raw', 'neso_demand') }}
),

typed as (
    select
        trim(settlement_date) as settlement_date_raw,
        case
            -- Newer files: 2025-01-31 (sometimes with a time part)
            when regexp_matches(trim(settlement_date), '^\d{4}-\d{2}-\d{2}')
                then try_cast(substr(trim(settlement_date), 1, 10) as date)
            -- 2023 file: 31-Jan-23 (two-digit year)
            when regexp_matches(trim(settlement_date), '^\d{1,2}-[A-Za-z]{3}-\d{2}$')
                then make_date(
                    2000 + try_cast(split_part(trim(settlement_date), '-', 3) as bigint),
                    cast(list_position(['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC'],
                                       upper(split_part(trim(settlement_date), '-', 2))) as bigint),
                    try_cast(split_part(trim(settlement_date), '-', 1) as bigint))
            -- 2024 file: 31-JAN-2024
            when regexp_matches(trim(settlement_date), '^\d{1,2}-[A-Za-z]{3}-\d{4}$')
                then make_date(
                    try_cast(split_part(trim(settlement_date), '-', 3) as bigint),
                    cast(list_position(['JAN','FEB','MAR','APR','MAY','JUN','JUL','AUG','SEP','OCT','NOV','DEC'],
                                       upper(split_part(trim(settlement_date), '-', 2))) as bigint),
                    try_cast(split_part(trim(settlement_date), '-', 1) as bigint))
        end as settlement_date,
        try_cast(settlement_period as integer) as settlement_period,
        try_cast(nd as double) as national_demand_mw,
        try_cast(tsd as double) as transmission_system_demand_mw,
        try_cast(england_wales_demand as double) as england_wales_demand_mw,
        try_cast(embedded_wind_generation as double) as embedded_wind_mw,
        try_cast(embedded_wind_capacity as double) as embedded_wind_capacity_mw,
        try_cast(embedded_solar_generation as double) as embedded_solar_mw,
        try_cast(embedded_solar_capacity as double) as embedded_solar_capacity_mw,
        try_cast(non_bm_stor as double) as non_bm_stor_mw,
        try_cast(pump_storage_pumping as double) as pump_storage_pumping_mw,
        try_cast(scottish_transfer as double) as scottish_transfer_mw,
        try_cast(ifa_flow as double) as ifa_flow_mw,
        try_cast(ifa2_flow as double) as ifa2_flow_mw,
        try_cast(britned_flow as double) as britned_flow_mw,
        try_cast(moyle_flow as double) as moyle_flow_mw,
        try_cast(east_west_flow as double) as east_west_flow_mw,
        try_cast(nemo_flow as double) as nemo_flow_mw,
        try_cast(nsl_flow as double) as nsl_flow_mw,
        try_cast(eleclink_flow as double) as eleclink_flow_mw,
        try_cast(viking_flow as double) as viking_flow_mw,
        try_cast(greenlink_flow as double) as greenlink_flow_mw,
        coalesce(upper(trim(forecast_actual_indicator)) = 'F', false) as is_forecast,
        _source_file,
        _loaded_at
    from source
)

select *
from typed
qualify row_number() over (
    partition by settlement_date, settlement_period
    order by _source_file desc, _loaded_at desc
) = 1
