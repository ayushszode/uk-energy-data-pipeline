-- Regional carbon intensity. Grain: one row per region per half hour.
select
    r.period_start_utc,
    {{ utc_to_local('r.period_start_utc') }} as period_start_local,
    cast({{ utc_to_local('r.period_start_utc') }} as date) as local_date,
    r.region_id,
    r.intensity_forecast,
    r.intensity_index,
    r.wind_pct,
    r.solar_pct,
    r.nuclear_pct,
    r.hydro_pct,
    r.biomass_pct,
    r.gas_pct,
    r.coal_pct,
    r.imports_pct,
    r.other_pct,
    r.wind_pct + r.solar_pct + r.nuclear_pct + r.hydro_pct as zero_carbon_pct
from {{ ref('stg_carbon__regional') }} as r
