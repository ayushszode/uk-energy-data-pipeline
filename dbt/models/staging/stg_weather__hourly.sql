-- Hourly observed weather per city (Open-Meteo reanalysis, times in UTC).
with source as (
    select * from {{ source('raw', 'weather_hourly') }}
),

typed as (
    select
        try_strptime("time", '%Y-%m-%dT%H:%M') as observed_at_utc,
        trim(city) as city,
        try_cast(temperature_2m as double) as temperature_c,
        try_cast(wind_speed_10m as double) as wind_speed_kmh,
        try_cast(shortwave_radiation as double) as solar_radiation_wm2,
        try_cast(cloud_cover as double) as cloud_cover_pct,
        _source_file,
        _loaded_at
    from source
)

select *
from typed
where observed_at_utc is not null
qualify row_number() over (partition by observed_at_utc, city order by _loaded_at desc, _source_file desc) = 1
