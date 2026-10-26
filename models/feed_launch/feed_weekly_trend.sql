-- Weekly series for the cohort, with week of year so 2024 and 2025 can be drawn on top of each other
with weekly as (
    select
        a.week_start,
        sum(a.sessions)                as sessions,
        sum(a.workouts_logged)         as workouts,
        sum(a.partner_challenge_views) as partner_views
    from {{ ref('stg_weekly_activity') }} a
    join {{ ref('feed_cohort') }} c using (member_id)
    group by 1
)
select
    week_start,
    isoyear(week_start)                                       as year,
    weekofyear(week_start)                                    as week_of_year,
    sessions / (select count(*) from {{ ref('feed_cohort') }}) as sessions_per_member,
    workouts / (select count(*) from {{ ref('feed_cohort') }}) as workouts_per_member,
    partner_views / sessions                                  as partner_views_per_session
from weekly
order by week_start
