-- Per member, scenario, year and period: weekly averages. Weeks with no activity count as zero.
with periods as (
    select scenario, year_label, 'before' as period, before_start as period_start, split_date - 1 as period_end
    from {{ ref('feed_scenarios') }}
    union all
    select scenario, year_label, 'after', split_date, after_end
    from {{ ref('feed_scenarios') }}
),
grid as (
    select c.member_id, p.*
    from {{ ref('feed_cohort') }} c
    cross join periods p
)
select
    g.member_id,
    g.scenario,
    g.year_label,
    g.period,
    coalesce(sum(a.sessions), 0)                / {{ var("window_weeks") }} as sessions_per_week,
    coalesce(sum(a.workouts_logged), 0)         / {{ var("window_weeks") }} as workouts_per_week,
    coalesce(sum(a.sessions), 0)                                             as sessions,
    coalesce(sum(a.partner_challenge_views), 0)                              as partner_views
from grid g
left join {{ ref('stg_weekly_activity') }} a
    on  a.member_id = g.member_id
    and a.week_start between g.period_start and g.period_end
group by all
