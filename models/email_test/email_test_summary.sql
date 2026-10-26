-- Counts and rates per variant. Significance, intervals and the sample ratio check run in run_analysis.py
select
    variant,
    count(*)              as members,
    sum(first_workout_7d) as first_workout_7d,
    avg(first_workout_7d) as first_workout_7d_rate,
    sum(active_day_30)    as active_day_30,
    avg(active_day_30)    as active_day_30_rate
from {{ ref('stg_onboarding_email_test') }}
group by 1
order by 1
