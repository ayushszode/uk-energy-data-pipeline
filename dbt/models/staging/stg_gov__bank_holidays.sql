-- UK bank holidays by division (england-and-wales, scotland, northern-ireland).
with source as (
    select * from {{ source('raw', 'bank_holidays') }}
)

select distinct
    trim(division) as division,
    try_cast("date" as date) as holiday_date,
    trim(title) as holiday_name
from source
where try_cast("date" as date) is not null
