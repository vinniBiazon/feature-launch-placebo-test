-- Four comparisons of N weeks before vs N weeks after a date:
--   launch  / this_year  : the real launch
--   launch  / prior_year : the same calendar weeks one year earlier, when nothing launched
--   placebo / this_year  : a fake launch date in 2025
--   placebo / prior_year : the same calendar weeks in 2024
with dates as (
    select 'launch'  as scenario, date '{{ var("feed_launch") }}'    as launch_date
    union all
    select 'placebo' as scenario, date '{{ var("placebo_launch") }}' as launch_date
),
years as (
    select 'this_year' as year_label, 0 as offset_days
    union all
    select 'prior_year', {{ var("prior_year_offset_days") }}
)
select
    d.scenario,
    y.year_label,
    d.launch_date - y.offset_days                                        as split_date,
    d.launch_date - y.offset_days - {{ var("window_weeks") * 7 }}         as before_start,
    d.launch_date - y.offset_days + {{ var("window_weeks") * 7 - 1 }}     as after_end
from dates d
cross join years y
