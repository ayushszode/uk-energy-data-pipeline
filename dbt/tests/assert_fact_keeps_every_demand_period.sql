-- The joins in the fact table must not drop or duplicate any demand period.
select
    (select count(*) from {{ ref('int_demand__half_hourly') }}) as demand_periods,
    (select count(*) from {{ ref('fct_electricity_half_hourly') }}) as fact_rows
where (select count(*) from {{ ref('int_demand__half_hourly') }})
   <> (select count(*) from {{ ref('fct_electricity_half_hourly') }})
