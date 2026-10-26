-- Before/after change this year, the same change one year earlier, and the change net of the calendar:
--   adjusted = (after / before this year) / (after / before prior year) - 1
with by_period as (
    select
        scenario, year_label, period,
        avg(sessions_per_week)              as sessions_per_member_week,
        avg(workouts_per_week)              as workouts_per_member_week,
        sum(partner_views) / sum(sessions)  as partner_views_per_session
    from {{ ref('feed_member_windows') }}
    group by all
),
long as (
    unpivot by_period
    on sessions_per_member_week, workouts_per_member_week, partner_views_per_session
    into name metric value value
),
changes as (
    select
        scenario, metric, year_label,
        max(value) filter (where period = 'before') as before_value,
        max(value) filter (where period = 'after')  as after_value
    from long
    group by all
)
select
    t.scenario,
    t.metric,
    t.before_value,
    t.after_value,
    t.after_value / t.before_value - 1                                            as change_this_year,
    p.after_value / p.before_value - 1                                            as change_prior_year,
    (t.after_value / t.before_value) / (p.after_value / p.before_value) - 1       as change_adjusted
from changes t
join changes p
    on p.scenario = t.scenario and p.metric = t.metric and p.year_label = 'prior_year'
where t.year_label = 'this_year'
order by t.scenario, t.metric
