-- Carbon Intensity API regions (from the seed file).
select region_id, region_name, region_type, nation
from {{ ref('regions') }}
