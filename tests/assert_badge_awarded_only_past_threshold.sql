-- Every award must belong to a member whose lifetime workouts reached the threshold by the award date
with lifetime as (
    select
        b.member_id,
        b.awarded_on,
        m.workouts_before_2024 + coalesce(sum(a.workouts_logged), 0) as workouts_at_award
    from {{ ref('stg_badge_awards') }} b
    join {{ ref('stg_members') }} m using (member_id)
    left join {{ ref('stg_weekly_activity') }} a
        on a.member_id = b.member_id and a.week_start <= b.awarded_on
    group by b.member_id, b.awarded_on, m.workouts_before_2024
)
select *
from lifetime
where workouts_at_award < {{ var("badge_threshold") }}
