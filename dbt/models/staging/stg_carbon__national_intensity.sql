-- National carbon intensity per half hour. The API reports both a forecast and
-- (after the event) an actual estimate, in grams of CO2 per kWh.
with source as (
    select * from {{ source('raw', 'carbon_national') }}
),

typed as (
    select
        {{ parse_api_timestamp('"from"') }} as period_start_utc,
        {{ parse_api_timestamp('"to"') }} as period_end_utc,
        try_cast(forecast as integer) as intensity_forecast,
        try_cast(actual as integer) as intensity_actual,
        lower(trim("index")) as intensity_index,
        _source_file,
        _loaded_at
    from source
)

select *
from typed
where period_start_utc is not null
qualify row_number() over (partition by period_start_utc order by _loaded_at desc, _source_file desc) = 1
