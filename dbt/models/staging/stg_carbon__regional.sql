-- Regional carbon intensity per half hour and region. The API only publishes
-- forecasts (no "actual") at regional level.
with source as (
    select * from {{ source('raw', 'carbon_regional') }}
),

typed as (
    select
        {{ parse_api_timestamp('"from"') }} as period_start_utc,
        try_cast(regionid as integer) as region_id,
        trim(shortname) as region_short_name,
        trim(dnoregion) as dno_region,
        cast(round(try_cast(forecast as double)) as integer) as intensity_forecast,
        lower(trim("index")) as intensity_index,
        try_cast(biomass_perc as double) as biomass_pct,
        try_cast(coal_perc as double) as coal_pct,
        try_cast(imports_perc as double) as imports_pct,
        try_cast(gas_perc as double) as gas_pct,
        try_cast(nuclear_perc as double) as nuclear_pct,
        try_cast(other_perc as double) as other_pct,
        try_cast(hydro_perc as double) as hydro_pct,
        try_cast(solar_perc as double) as solar_pct,
        try_cast(wind_perc as double) as wind_pct,
        _source_file,
        _loaded_at
    from source
)

select *
from typed
where period_start_utc is not null
qualify row_number() over (partition by period_start_utc, region_id order by _loaded_at desc, _source_file desc) = 1
