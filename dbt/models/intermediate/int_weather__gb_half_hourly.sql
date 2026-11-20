-- A single GB weather series: population-weighted average of the city
-- readings for each hour, then repeated for both half hours in that hour.
with weights as (
    select city, population_weight_m from {{ ref('cities') }}
),

hourly as (
    select
        w.observed_at_utc,
        sum(w.temperature_c * c.population_weight_m) / sum(c.population_weight_m) as temperature_c,
        sum(w.wind_speed_kmh * c.population_weight_m) / sum(c.population_weight_m) as wind_speed_kmh,
        sum(w.solar_radiation_wm2 * c.population_weight_m) / sum(c.population_weight_m) as solar_radiation_wm2,
        sum(w.cloud_cover_pct * c.population_weight_m) / sum(c.population_weight_m) as cloud_cover_pct,
        count(*) as cities_reporting
    from {{ ref('stg_weather__hourly') }} as w
    join weights as c on c.city = w.city
    where w.temperature_c is not null
    group by w.observed_at_utc
)

select observed_at_utc as period_start_utc, temperature_c, wind_speed_kmh,
       solar_radiation_wm2, cloud_cover_pct, cities_reporting
from hourly
union all
select observed_at_utc + interval 30 minute, temperature_c, wind_speed_kmh,
       solar_radiation_wm2, cloud_cover_pct, cities_reporting
from hourly
