{{ config(severity = 'warn') }}
-- Cross-source check: NESO's net interconnector flow should rise when the
-- Carbon Intensity API shows a higher imports share. If the correlation is not
-- positive, the sign convention of the flow columns needs checking.
select corr(net_interconnector_flow_mw, imports_pct) as correlation
from {{ ref('fct_electricity_half_hourly') }}
having corr(net_interconnector_flow_mw, imports_pct) <= 0
