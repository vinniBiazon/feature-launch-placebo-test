-- The gap that a dashboard would show after launch, the same gap before badges existed,
-- and the difference-in-differences (relative): how much more holders changed than non-holders
with means as (
    select badge_group, period, avg(kudos_per_week) as kudos, avg(sessions_per_week) as sessions
    from {{ ref('badge_member_periods') }}
    group by all
),
long as (
    unpivot means on kudos, sessions into name metric value value
),
wide as (
    select
        metric,
        max(value) filter (where badge_group = 'holder'     and period = 'before') as holder_before,
        max(value) filter (where badge_group = 'holder'     and period = 'after')  as holder_after,
        max(value) filter (where badge_group = 'non_holder' and period = 'before') as non_holder_before,
        max(value) filter (where badge_group = 'non_holder' and period = 'after')  as non_holder_after
    from long
    group by 1
)
select
    metric,
    holder_after / non_holder_after - 1                                       as gap_after_launch,
    holder_before / non_holder_before - 1                                     as gap_before_launch,
    (holder_after / holder_before) / (non_holder_after / non_holder_before) - 1 as did_relative
from wide
order by metric
