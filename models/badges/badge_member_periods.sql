-- Kudos and sessions per week for each member, before badges existed and after launch
{% set n_before = 8 %}
{% set n_after = 8 %}
with periods as (
    select 'before' as period, date '{{ var("badge_before_start") }}' as period_start, date '{{ var("badge_before_end") }}' as period_end, {{ n_before }} as n_weeks
    union all
    select 'after',  date '{{ var("badge_after_start") }}', date '{{ var("badge_after_end") }}', {{ n_after }}
)
select
    g.member_id,
    g.badge_group,
    p.period,
    coalesce(sum(a.kudos_given), 0) / p.n_weeks as kudos_per_week,
    coalesce(sum(a.sessions), 0)    / p.n_weeks as sessions_per_week
from {{ ref('badge_groups') }} g
cross join periods p
left join {{ ref('stg_weekly_activity') }} a
    on  a.member_id = g.member_id
    and a.week_start between p.period_start and p.period_end
group by g.member_id, g.badge_group, p.period, p.n_weeks
