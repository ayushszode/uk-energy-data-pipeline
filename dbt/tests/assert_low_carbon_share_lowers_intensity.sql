{{ config(severity = 'warn') }}
-- Sanity check that the two Carbon Intensity API feeds agree with each other:
-- a higher zero-carbon share should go with lower intensity (strong negative correlation).
select corr(zero_carbon_pct, intensity_actual) as correlation
from {{ ref('fct_electricity_half_hourly') }}
having corr(zero_carbon_pct, intensity_actual) > -0.5
