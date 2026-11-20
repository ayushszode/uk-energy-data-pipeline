-- National carbon intensity joined to the generation mix for each half hour,
-- with simple grouped shares that are easier to explain than nine fuels.
select
    i.period_start_utc,
    i.intensity_actual,
    i.intensity_forecast,
    i.intensity_index,
    m.wind_pct,
    m.solar_pct,
    m.nuclear_pct,
    m.hydro_pct,
    m.biomass_pct,
    m.gas_pct,
    m.coal_pct,
    m.imports_pct,
    m.other_pct,
    m.wind_pct + m.solar_pct as wind_solar_pct,
    m.wind_pct + m.solar_pct + m.nuclear_pct + m.hydro_pct as zero_carbon_pct,
    m.gas_pct + m.coal_pct as fossil_pct
from {{ ref('stg_carbon__national_intensity') }} as i
left join {{ ref('stg_carbon__generation_mix') }} as m
    on m.period_start_utc = i.period_start_utc
